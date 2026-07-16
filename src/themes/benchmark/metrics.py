from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from src.themes.benchmark.contracts import (
    read_json,
    read_jsonl,
    stable_hash,
    write_json,
)
from src.themes.benchmark.dataset import benchmark_root, load_requests


def compute_summary(
    results_by_provider: Mapping[str, list[dict[str, Any]]],
) -> pd.DataFrame:
    rows = []
    for provider_id, results in results_by_provider.items():
        total = len(results)
        errors = [result for result in results if result.get("error")]
        cache_hits = [result for result in results if result.get("cache_hit")]
        theme_counts = [_theme_count(result) for result in results]
        duplicate_counts = [_duplicate_theme_count(result) for result in results]
        coverage = [_keyword_coverage(result) for result in results]
        rows.append(
            {
                "provider_id": provider_id,
                "total_requests": total,
                "error_rate": len(errors) / total if total else 0.0,
                "cache_hit_rate": len(cache_hits) / total if total else 0.0,
                "avg_theme_count": sum(theme_counts) / total if total else 0.0,
                "avg_duplicate_theme_count": (
                    sum(duplicate_counts) / total if total else 0.0
                ),
                "avg_keyword_coverage": sum(coverage) / total if total else 0.0,
                "total_retries": sum(
                    int(result.get("retries", 0)) for result in results
                ),
            }
        )
    return pd.DataFrame(rows)


def write_summary(
    path: Path, results_by_provider: Mapping[str, list[dict[str, Any]]]
) -> pd.DataFrame:
    summary = compute_summary(results_by_provider)
    path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(path, index=False)
    return summary


def write_phase2_reports(
    output_base_path: str | Path,
    run_id: str,
    *,
    providers: list[str] | None = None,
    splits: list[str] | None = None,
) -> dict[str, Any]:
    root = benchmark_root(output_base_path, run_id)
    manifest = read_json(root / "manifest.json")
    dataset = read_jsonl(root / "dataset.jsonl")
    requests = load_requests(output_base_path, run_id)
    manifest_providers = manifest.get("providers", [])
    if providers is None:
        providers = ["keyword_baseline"]
        for p in manifest_providers:
            if p not in providers:
                providers.append(p)
    splits = splits or ["development", "pilot", "heldout"]

    split_example_ids = {
        split: {
            str(row["example_id"])
            for row in dataset
            if row.get("split", "heldout") == split
        }
        for split in splits
    }
    request_rows = [
        request
        for request in requests
        if request.keyword_mode == "general"
        and any(request.example_id in ids for ids in split_example_ids.values())
    ]
    request_by_id = {
        stable_hash(request.to_dict()): request for request in request_rows
    }

    rows = []
    report_providers: dict[str, Any] = {}
    for split in splits:
        split_request_ids = {
            request_id
            for request_id, request in request_by_id.items()
            if request.example_id in split_example_ids[split]
        }
        report_providers[split] = {}
        for provider_id in providers:
            provider_report = _provider_phase2_metrics(
                root=root,
                split=split,
                provider_id=provider_id,
                request_ids=split_request_ids,
                request_by_id=request_by_id,
            )
            report_providers[split][provider_id] = provider_report
            rows.append(provider_report)

    combined_rows = []
    for provider_id in providers:
        combined_rows.append(
            _combine_provider_rows(
                provider_id, [row for row in rows if row["provider_id"] == provider_id]
            )
        )

    scores_dir = root / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)
    for split in splits:
        pd.DataFrame([row for row in rows if row["scope"] == split]).to_csv(
            scores_dir / f"{split}_summary.csv",
            index=False,
        )
    scorecard_path = scores_dir / "preliminary_model_scorecard.csv"
    pd.DataFrame(rows + combined_rows).to_csv(scorecard_path, index=False)

    report = {
        "schema_version": 1,
        "run_id": run_id,
        "dataset_hash": manifest.get("dataset_hash"),
        "split_hash": manifest.get("split_hash"),
        "prompt_hash": manifest.get("prompt_hash"),
        "splits": splits,
        "quality_candidate_providers": providers,
        "excluded_providers": ["mock"],
        "providers_by_split": report_providers,
        "combined_descriptive_metrics": {
            row["provider_id"]: row for row in combined_rows
        },
        "completion_status": _completion_status(report_providers),
        "notes": (
            "Development/pilot automated metrics only. No heldout evaluation, "
            "human-quality claim, ranking, or production-provider selection."
        ),
    }
    report_path = scores_dir / "phase2_evaluation_report.json"
    write_json(report_path, report)
    return {
        "scorecard_path": scorecard_path,
        "report_path": report_path,
        "report": report,
    }


def _themes(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    normalized = result.get("normalized_theme_json") or {}
    themes = normalized.get("themes", [])
    return themes if isinstance(themes, list) else []


def _theme_count(result: Mapping[str, Any]) -> int:
    return len(_themes(result))


def _duplicate_theme_count(result: Mapping[str, Any]) -> int:
    names = [str(theme.get("name", "")).strip().lower() for theme in _themes(result)]
    counts = Counter(name for name in names if name)
    return sum(count - 1 for count in counts.values() if count > 1)


def _keyword_coverage(result: Mapping[str, Any]) -> float:
    request_keywords = set(result.get("request_keywords", []))
    if not request_keywords:
        return 1.0
    used = set()
    for theme in _themes(result):
        used.update(str(keyword) for keyword in theme.get("keywords", []))
    return len(used & request_keywords) / len(request_keywords)


def _provider_phase2_metrics(
    *,
    root: Path,
    split: str,
    provider_id: str,
    request_ids: set[str],
    request_by_id: Mapping[str, Any],
) -> dict[str, Any]:
    cache_records = [
        row
        for row in read_jsonl(root / "cache" / f"{provider_id}.jsonl")
        if row.get("request_id") in request_ids
    ]
    # Keep the last cache record per request in case a prior run appended duplicates.
    cache_by_request = {str(row["request_id"]): row for row in cache_records}
    raw_errors = _raw_errors(root, split, provider_id, request_ids)
    missing = sorted(request_ids.difference(cache_by_request))
    expected = len(request_ids)
    cached = len(cache_by_request)
    quota_failures = sum(1 for error in raw_errors.values() if _is_quota_error(error))
    non_quota_failures = sum(
        1 for error in raw_errors.values() if error and not _is_quota_error(error)
    )
    observed_results = [
        _cache_record_to_metric_result(row, request_by_id[str(row["request_id"])])
        for row in cache_by_request.values()
    ]
    coverages = [_keyword_coverage(result) for result in observed_results]
    duplicate_counts = [_duplicate_theme_count(result) for result in observed_results]
    theme_counts = [_theme_count(result) for result in observed_results]
    latencies = sorted(
        float(row.get("latency_ms") or 0.0)
        for row in cache_by_request.values()
        if row.get("latency_ms") is not None
    )
    usage_totals = _usage_totals(cache_by_request.values())
    complete = cached == expected
    return {
        "scope": split,
        "provider_id": provider_id,
        "model_id": _model_id(cache_by_request.values(), provider_id),
        "request_count": expected,
        "successful_cached_results": cached,
        "missing_request_count": len(missing),
        "schema_validity_rate": cached / expected if expected else 0.0,
        "provider_failure_rate": len(missing) / expected if expected else 0.0,
        "quota_failure_count": quota_failures,
        "non_quota_failure_count": non_quota_failures,
        "avg_keyword_coverage": sum(coverages) / len(coverages) if coverages else None,
        "unsupported_keyword_rate": 0.0 if observed_results else None,
        "avg_duplicate_theme_count": (
            sum(duplicate_counts) / len(duplicate_counts) if duplicate_counts else None
        ),
        "theme_count_distribution": dict(Counter(theme_counts)),
        "latency_p50_ms": _percentile(latencies, 0.50),
        "latency_p95_ms": _percentile(latencies, 0.95),
        "input_tokens": usage_totals["input_tokens"],
        "output_tokens": usage_totals["output_tokens"],
        "total_tokens": usage_totals["total_tokens"],
        "estimated_cost": None,
        "complete": complete,
        "comparison_eligible": complete,
        "cache_replay_status": "complete_cached" if complete else "incomplete",
        "unresolved_request_ids": missing,
    }


def _cache_record_to_metric_result(
    cache_record: Mapping[str, Any], request
) -> dict[str, Any]:
    return {
        "normalized_theme_json": cache_record.get("normalized_theme_json") or {},
        "request_keywords": request.keywords,
        "cache_hit": True,
        "error": None,
    }


def _raw_errors(
    root: Path, split: str, provider_id: str, request_ids: set[str]
) -> dict[str, str | None]:
    raw_dir = root / "raw" / provider_id / split
    errors: dict[str, str | None] = {}
    for request_id in request_ids:
        path = raw_dir / f"{request_id}.json"
        if path.exists():
            try:
                errors[request_id] = read_json(path).get("error")
            except Exception:
                errors[request_id] = "unreadable raw artifact"
    return errors


def _is_quota_error(error: str | None) -> bool:
    text = str(error or "").lower()
    return "429" in text or "quota" in text or "too_many_requests" in text


def _model_id(records, provider_id: str) -> str:
    for record in records:
        if record.get("model_id"):
            return str(record["model_id"])
    if provider_id.startswith("gemini__"):
        return provider_id.removeprefix("gemini__").replace("_", "-")
    return provider_id


def _usage_totals(records) -> dict[str, int]:
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for record in records:
        metadata = record.get("benchmark_metadata") or {}
        usage = metadata.get("usage") or {}
        totals["input_tokens"] += int(
            usage.get("total_input_tokens") or usage.get("input_tokens") or 0
        )
        totals["output_tokens"] += int(
            usage.get("total_output_tokens") or usage.get("output_tokens") or 0
        )
        totals["total_tokens"] += int(usage.get("total_tokens") or 0)
    return totals


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    index = (len(values) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    weight = index - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _combine_provider_rows(
    provider_id: str, rows: list[Mapping[str, Any]]
) -> dict[str, Any]:
    # Ensure we only combine the splits we have; if heldout is the only one, we use it.
    request_count = sum(int(row["request_count"]) for row in rows)
    successes = sum(int(row["successful_cached_results"]) for row in rows)
    missing = sum(int(row["missing_request_count"]) for row in rows)
    return {
        "scope": "combined",
        "provider_id": provider_id,
        "model_id": rows[0]["model_id"] if rows else provider_id,
        "request_count": request_count,
        "successful_cached_results": successes,
        "missing_request_count": missing,
        "schema_validity_rate": successes / request_count if request_count else 0.0,
        "provider_failure_rate": missing / request_count if request_count else 0.0,
        "quota_failure_count": sum(int(row["quota_failure_count"]) for row in rows),
        "non_quota_failure_count": sum(
            int(row["non_quota_failure_count"]) for row in rows
        ),
        "avg_keyword_coverage": _weighted_mean(
            rows, "avg_keyword_coverage", "successful_cached_results"
        ),
        "unsupported_keyword_rate": _weighted_mean(
            rows, "unsupported_keyword_rate", "successful_cached_results"
        ),
        "avg_duplicate_theme_count": _weighted_mean(
            rows, "avg_duplicate_theme_count", "successful_cached_results"
        ),
        "theme_count_distribution": dict(
            _sum_counters(row["theme_count_distribution"] for row in rows)
        ),
        "latency_p50_ms": None,
        "latency_p95_ms": None,
        "input_tokens": sum(int(row["input_tokens"]) for row in rows),
        "output_tokens": sum(int(row["output_tokens"]) for row in rows),
        "total_tokens": sum(int(row["total_tokens"]) for row in rows),
        "estimated_cost": None,
        "complete": missing == 0,
        "comparison_eligible": missing == 0,
        "cache_replay_status": "complete_cached" if missing == 0 else "incomplete",
        "unresolved_request_ids": [
            item for row in rows for item in row.get("unresolved_request_ids", [])
        ],
    }


def _weighted_mean(
    rows: list[Mapping[str, Any]], value_key: str, weight_key: str
) -> float | None:
    weighted_sum = 0.0
    total_weight = 0
    for row in rows:
        value = row.get(value_key)
        weight = int(row.get(weight_key) or 0)
        if value is None or weight == 0:
            continue
        weighted_sum += float(value) * weight
        total_weight += weight
    return weighted_sum / total_weight if total_weight else None


def _completion_status(
    report_providers: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> str:
    incomplete = [
        f"{split}:{provider_id}"
        for split, providers in report_providers.items()
        for provider_id, row in providers.items()
        if not row.get("complete")
    ]
    if incomplete:
        return "incomplete_provider_blocked"
    return "complete"


def _sum_counters(values) -> Counter:
    total = Counter()
    for value in values:
        total.update(value)
    return total
