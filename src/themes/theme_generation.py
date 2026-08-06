from __future__ import annotations

import concurrent.futures
import logging
import time
import unicodedata
from collections.abc import Sequence
from typing import Any

import pandas as pd

from src.config.defaults import DEFAULT_CONFIG
from src.providers.base import BaseLLMProvider as LLMProvider
from src.themes.theme_inputs import _parse_list

logger = logging.getLogger(__name__)


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
) -> dict[tuple[str, ...], dict[str, Any]]:
    """Fetch exact ordered payloads with bounded concurrency and fail-fast errors."""
    if not unique_keywords:
        return {}
    workers = max(1, min(int(max_workers), len(unique_keywords)))
    results: dict[tuple[str, ...], dict[str, Any]] = {}
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
                keywords, response = future.result()
                results[keywords] = response
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


def generate_llm_themes(
    provider: LLMProvider,
    month_df: pd.DataFrame,
    *,
    max_workers: int = 6,
) -> pd.DataFrame:
    df = extract_unique_keywords(month_df)
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
        return str(theme_results.get(keywords, {}))

    def map_names(keywords: tuple[str, ...]) -> str | None:
        response = theme_results.get(keywords, {})
        return ".".join(response) if response else None

    for prefix, keyword_column in (
        ("absolute", "absolute_keywords"),
        ("weighted", "weighted_keywords"),
        ("general", "all_keywords"),
    ):
        df[f"{prefix}_theme_gpt"] = df[keyword_column].map(map_theme)
        df[f"{prefix}_theme_names"] = df[keyword_column].map(map_names)
    return df
