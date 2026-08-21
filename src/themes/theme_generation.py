from __future__ import annotations

import concurrent.futures
import logging
import time
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.config.defaults import DEFAULT_CONFIG
from src.providers.base import (
    BaseLLMProvider as LLMProvider,
    ProviderSafetyError,
    build_theme_request,
)
from src.themes.benchmark.contracts import (
    OUTPUT_SCHEMA_VERSION,
    THEME_PROMPT_CONTRACT_VERSION,
)
from src.themes.theme_inputs import _parse_list

logger = logging.getLogger(__name__)

THEME_GENERATION_PROVENANCE_COLUMNS = (
    "year",
    "month",
    "source_row_index",
    "keyword_kind",
    "absolute_community",
    "weighted_community",
    "provider_keywords",
    "keyword_count",
    "input_hash",
    "prompt_hash",
    "prompt_contract_version",
    "output_schema_version",
    "status",
    "failure_category",
    "failure_stage",
    "configured_provider",
    "configured_model",
    "content_filter_summary",
)


@dataclass(frozen=True)
class ThemeFetchOutcome:
    status: str
    themes: dict[str, Any] | None = None
    failure: ProviderSafetyError | None = None


def parse_keyword_values(value: object) -> list[object]:
    result = _parse_list(value)
    if not isinstance(result, list):
        raise ValueError(
            f"Malformed keyword representation: expected list, got {type(result)}"
        )
    return result


def normalize_ranked_keywords(values: Sequence[object]) -> list[str]:
    """Normalize and de-duplicate while preserving first-observed LDA rank."""
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        display_value = unicodedata.normalize("NFKC", str(value)).strip()
        identity = display_value.casefold()
        if display_value and identity not in seen:
            seen.add(identity)
            normalized.append(display_value)
    return normalized


def extract_unique_keywords(month_df: pd.DataFrame) -> pd.DataFrame:
    """Create ordered keyword tuples used by exact-request caching."""
    df = month_df.copy()
    required = (
        "absolute_unigram_keywords",
        "absolute_bigram_keywords",
        "weighted_unigram_keywords",
        "weighted_bigram_keywords",
    )
    for column in required:
        if column not in df.columns:
            df[column] = [[] for _ in range(len(df))]
        else:
            # Parse each source cell once and preserve list-valued columns in the
            # published themed dataframe.
            df[column] = [parse_keyword_values(value) for value in df[column].tolist()]

    def process_values(values: Sequence[list[object]]) -> tuple[str, ...]:
        combined: list[object] = []
        for value in values:
            combined.extend(value)
        return tuple(normalize_ranked_keywords(combined))

    rows = list(df.loc[:, required].itertuples(index=False, name=None))
    df["all_keywords"] = [process_values(row) for row in rows]
    df["absolute_keywords"] = [process_values(row[:2]) for row in rows]
    df["weighted_keywords"] = [process_values(row[2:]) for row in rows]
    return df


def call_gpt_theme_api(keywords: list[str]):
    from src.providers.factory import build_theme_provider

    provider = build_theme_provider(DEFAULT_CONFIG.model_dump())
    return provider.generate_theme(keywords)


def generate_gpt_theme(month_df: pd.DataFrame):
    from src.providers.factory import build_theme_provider

    provider = build_theme_provider(DEFAULT_CONFIG.model_dump())
    return generate_llm_themes(provider, month_df)


def _fetch_themes_concurrently(
    provider: LLMProvider,
    unique_keywords: Sequence[tuple[str, ...]],
    *,
    max_workers: int = 6,
) -> dict[tuple[str, ...], ThemeFetchOutcome]:
    """Fetch exact payloads; recover only typed provider-safety outcomes."""
    if not unique_keywords:
        return {}
    workers = max(1, min(int(max_workers), len(unique_keywords)))
    results: dict[tuple[str, ...], ThemeFetchOutcome] = {}
    total = len(unique_keywords)
    progress_step = max(1, total // 10)
    started = time.perf_counter()
    logger.info(
        "theme_requests_started total=%d max_workers=%d provider=%s",
        total,
        workers,
        getattr(getattr(provider, "metadata", None), "provider_id", "unknown"),
    )

    def fetch_single(keywords: tuple[str, ...]):
        return keywords, provider.generate_theme(list(keywords))

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_single, keywords): keywords
            for keywords in unique_keywords
        }
        try:
            for completed, future in enumerate(
                concurrent.futures.as_completed(futures), start=1
            ):
                source_keywords = futures[future]
                try:
                    keywords, response = future.result()
                    results[keywords] = ThemeFetchOutcome(
                        status="generated", themes=response
                    )
                except ProviderSafetyError as exc:
                    if exc.category == "content_filter":
                        status = "content_filter_unavailable"
                    elif exc.category == "policy_refusal":
                        status = "policy_refusal_unavailable"
                    else:
                        raise
                    results[source_keywords] = ThemeFetchOutcome(
                        status=status, failure=exc
                    )
                    logger.warning(
                        "theme_request_safety_unavailable input_hash=%s "
                        "category=%s stage=%s provider=%s model=%s",
                        exc.input_hash[:12],
                        exc.category,
                        exc.stage,
                        exc.provider_id,
                        exc.model_id,
                    )
                if completed == total or completed % progress_step == 0:
                    metrics = getattr(provider, "run_metrics", {})
                    logger.info(
                        "theme_requests_progress completed=%d total=%d "
                        "cache_hits=%d outbound_requests=%d elapsed_seconds=%.2f",
                        completed,
                        total,
                        int(metrics.get("cache_hits", 0)),
                        int(metrics.get("outbound_requests", 0)),
                        time.perf_counter() - started,
                    )
        except Exception:
            for future in futures:
                future.cancel()
            raise
    return results


def _provenance_record(
    *,
    keywords: tuple[str, ...],
    outcome: ThemeFetchOutcome,
    year: str | int | None,
    month: str | None,
    source_row_index: int,
    keyword_kind: str,
    absolute_community: Any,
    weighted_community: Any,
    provider: LLMProvider,
) -> dict[str, Any]:
    request = build_theme_request(list(keywords))
    metadata = getattr(provider, "metadata", None)
    failure = outcome.failure
    diagnostics: Mapping[str, Any] = failure.diagnostics if failure is not None else {}
    return {
        "year": None if year is None else str(year),
        "month": None if month is None else str(month),
        "source_row_index": int(source_row_index),
        "keyword_kind": keyword_kind,
        "absolute_community": absolute_community,
        "weighted_community": weighted_community,
        "provider_keywords": list(keywords),
        "keyword_count": len(keywords),
        "input_hash": request.input_hash,
        "prompt_hash": request.prompt_hash,
        "prompt_contract_version": THEME_PROMPT_CONTRACT_VERSION,
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "status": outcome.status,
        "failure_category": None if failure is None else failure.category,
        "failure_stage": None if failure is None else failure.stage,
        "configured_provider": getattr(metadata, "provider_id", "unknown"),
        "configured_model": getattr(metadata, "model_id", "unknown"),
        "content_filter_summary": diagnostics.get("content_filter_summary"),
    }


def build_theme_generation_coverage(
    provenance_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build safe aggregate coverage without copying keyword evidence."""
    rows = list(provenance_records)
    unique_statuses: dict[str, set[str]] = {}
    for row in rows:
        input_hash = str(row.get("input_hash", ""))
        if input_hash:
            unique_statuses.setdefault(input_hash, set()).add(
                str(row.get("status", ""))
            )

    source_generated = sum(row.get("status") == "generated" for row in rows)
    source_unavailable = len(rows) - source_generated
    unique_generated = sum(
        "generated" in statuses for statuses in unique_statuses.values()
    )
    unique_unavailable = len(unique_statuses) - unique_generated
    return {
        "unique_payloads_requested": len(unique_statuses),
        "unique_payloads_generated": unique_generated,
        "unique_payloads_unavailable": unique_unavailable,
        "source_assignments_requested": len(rows),
        "source_assignments_generated": source_generated,
        "source_assignments_unavailable": source_unavailable,
        "content_filter_count": sum(
            row.get("status") == "content_filter_unavailable" for row in rows
        ),
        "policy_refusal_count": sum(
            row.get("status") == "policy_refusal_unavailable" for row in rows
        ),
        "partial": source_unavailable > 0,
    }


def generate_llm_themes(
    provider: LLMProvider,
    month_df: pd.DataFrame,
    *,
    max_workers: int = 6,
    provenance_records: list[dict[str, Any]] | None = None,
    year: str | int | None = None,
    month: str | None = None,
) -> pd.DataFrame:
    df = extract_unique_keywords(month_df).reset_index(drop=True)
    all_unique = {
        keywords
        for column in ("absolute_keywords", "weighted_keywords", "all_keywords")
        for keywords in df[column].tolist()
        if keywords
    }
    ordered_payloads = sorted(all_unique)
    bag_signatures = {
        tuple(sorted(keyword.casefold() for keyword in payload))
        for payload in ordered_payloads
    }
    logger.info(
        "theme_keyword_diagnostics ordered_unique_count=%d "
        "bag_signature_count=%d order_variant_count=%d max_workers=%d",
        len(ordered_payloads),
        len(bag_signatures),
        len(ordered_payloads) - len(bag_signatures),
        max_workers,
    )

    theme_results = _fetch_themes_concurrently(
        provider, ordered_payloads, max_workers=max_workers
    )

    def map_theme(keywords: tuple[str, ...]) -> str:
        outcome = theme_results.get(keywords)
        response = outcome.themes if outcome and outcome.themes else {}
        return str(response)

    def map_names(keywords: tuple[str, ...]) -> str | None:
        outcome = theme_results.get(keywords)
        response = outcome.themes if outcome and outcome.themes else {}
        return ".".join(response) if response else None

    for prefix, keyword_column in (
        ("absolute", "absolute_keywords"),
        ("weighted", "weighted_keywords"),
        ("general", "all_keywords"),
    ):
        df[f"{prefix}_theme_gpt"] = df[keyword_column].map(map_theme)
        df[f"{prefix}_theme_names"] = df[keyword_column].map(map_names)

    if provenance_records is not None:
        absolute_values = df.get("absolute_community", pd.Series([None] * len(df)))
        weighted_values = df.get("weighted_community", pd.Series([None] * len(df)))
        for row_index in range(len(df)):
            for keyword_kind, keyword_column in (
                ("absolute", "absolute_keywords"),
                ("weighted", "weighted_keywords"),
                ("general", "all_keywords"),
            ):
                keywords = df.at[row_index, keyword_column]
                if not keywords:
                    continue
                outcome = theme_results[keywords]
                provenance_records.append(
                    _provenance_record(
                        keywords=keywords,
                        outcome=outcome,
                        year=year,
                        month=month,
                        source_row_index=row_index,
                        keyword_kind=keyword_kind,
                        absolute_community=absolute_values.iloc[row_index],
                        weighted_community=weighted_values.iloc[row_index],
                        provider=provider,
                    )
                )
    return df
