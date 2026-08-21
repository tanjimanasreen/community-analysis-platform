from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Mapping

from src.themes.benchmark.cache import JsonlResponseCache
from src.themes.benchmark.contracts import (
    BenchmarkProviderStats,
    BenchmarkRunReport,
    ThemeBenchmarkResult,
    read_json,
    read_jsonl,
    stable_hash,
    write_json,
    write_jsonl,
)
from src.themes.benchmark.dataset import benchmark_root, load_requests
from src.themes.benchmark.integrity import (
    filter_examples_by_split,
    validate_frozen_dataset,
)
from src.themes.benchmark.metrics import write_summary
from src.themes.benchmark.providers import get_provider


def run_benchmark(
    config: Mapping[str, Any],
    *,
    run_id: str,
    provider_ids: list[str],
    max_examples: int | None = None,
    keyword_modes: list[str] | None = None,
    allow_live: bool = False,
    max_retries: int = 2,
    timeout: float | None = None,
    max_outbound_requests: int = 50,
    split: str | None = None,
    resume_unresolved: bool = False,
    max_unresolved_examples: int | None = None,
    example_ids: list[str] | None = None,
    repetition_index: int | None = None,
) -> BenchmarkRunReport:
    output_base_path = str(config.get("output_base_path", "results/"))
    root = benchmark_root(output_base_path, run_id)
    dataset_rows = read_jsonl(root / "dataset.jsonl")
    split_example_ids = None
    if split is not None:
        validate_frozen_dataset(output_base_path, run_id, write_report=True)
        split_example_ids = filter_examples_by_split(
            [
                str(request.example_id)
                for request in load_requests(output_base_path, run_id)
            ],
            dataset_rows,
            split,
        )
    if keyword_modes is None and any(
        provider_spec.startswith(("gemini:", "llm7:")) for provider_spec in provider_ids
    ):
        keyword_modes = ["general"]
    requests = _filter_requests(
        load_requests(output_base_path, run_id),
        max_examples=max_examples,
        keyword_modes=keyword_modes,
        split_example_ids=split_example_ids,
        example_ids=set(example_ids) if example_ids else None,
    )
    results_by_provider: dict[str, list[dict[str, Any]]] = {}
    stats_by_provider: dict[str, BenchmarkProviderStats] = {}
    metadata_by_provider: dict[str, dict[str, Any]] = {}
    request_budgets = {}
    if any(provider_spec.startswith("gemini:") for provider_spec in provider_ids):
        from src.providers.gemini import GeminiRequestBudget

        request_budgets["gemini"] = GeminiRequestBudget(max_outbound_requests)
    if any(provider_spec.startswith("nvidia:") for provider_spec in provider_ids):
        from src.providers.nvidia import NvidiaRequestBudget

        request_budgets["nvidia"] = NvidiaRequestBudget(max_outbound_requests)
    if any(provider_spec.startswith("llm7:") for provider_spec in provider_ids):
        from src.providers.llm7 import LLM7RequestBudget

        request_budgets["llm7"] = LLM7RequestBudget(max_outbound_requests)

    for provider_spec in provider_ids:
        budget_key = provider_spec.split(":", 1)[0] if ":" in provider_spec else None
        request_budget = request_budgets.get(budget_key)
        outbound_before = request_budget.used if request_budget is not None else 0
        provider = get_provider(
            provider_spec,
            config=config,
            allow_live=allow_live,
            max_retries=max_retries,
            timeout=timeout,
            max_outbound_requests=max_outbound_requests,
            request_budget=request_budget,
            benchmark_run_dir=root,
        )
        metadata = provider.metadata
        if repetition_index is not None:
            metadata = type(metadata)(
                provider_id=metadata.provider_id,
                model_id=metadata.model_id,
                parameters={
                    **metadata.parameters,
                    "repetition_index": repetition_index,
                },
            )
        metadata_by_provider[metadata.provider_id] = {
            "provider_id": metadata.provider_id,
            "model_id": metadata.model_id,
            "parameters": metadata.parameters,
        }
        cache = JsonlResponseCache(root / "cache" / f"{metadata.provider_id}.jsonl")
        generation_path = (
            root / "generations" / split / f"{metadata.provider_id}.jsonl"
            if split
            else root / "generations" / f"{metadata.provider_id}.jsonl"
        )
        provider_requests = requests
        if resume_unresolved:
            provider_requests = _filter_unresolved_requests(
                provider_requests,
                cache=cache,
                metadata=metadata,
                max_unresolved_examples=max_unresolved_examples,
            )
        raw_dir = (
            root / "raw" / metadata.provider_id / split
            if split
            else root / "raw" / metadata.provider_id
        )
        raw_dir.mkdir(parents=True, exist_ok=True)
        generation_path.parent.mkdir(parents=True, exist_ok=True)
        provider_results: list[dict[str, Any]] = []
        cache_hits = 0
        cache_misses = 0
        provider_executions = 0
        failures = 0

        for request in provider_requests:
            request_id = stable_hash(request.to_dict())
            cache_key = cache.cache_key(
                provider_id=metadata.provider_id,
                model_id=metadata.model_id,
                request=request,
                parameters=metadata.parameters,
            )
            cached = cache.get(cache_key)
            if cached is not None:
                cache_hits += 1
                normalized = cached["normalized_theme_json"]
                benchmark_metadata = cached.get("benchmark_metadata", {})
                result = _result(
                    provider_id=metadata.provider_id,
                    model_id=metadata.model_id,
                    request=request,
                    request_id=request_id,
                    cache_key=cache_key,
                    normalized=normalized,
                    latency_ms=cached.get("latency_ms"),
                    cache_hit=True,
                    benchmark_metadata=benchmark_metadata,
                )
                provider_results.append(result)
                continue

            cache_misses += 1
            provider_executions += 1
            started = time.monotonic()
            try:
                normalized = provider.generate(request)
                error = None
            except Exception as exc:  # pragma: no cover - defensive normalization
                normalized = {"themes": []}
                error = str(exc)
                failures += 1
            latency_ms = round((time.monotonic() - started) * 1000, 3)
            raw_path = raw_dir / f"{request_id}.json"
            write_json(
                raw_path,
                {
                    "provider_id": metadata.provider_id,
                    "model_id": metadata.model_id,
                    "request_id": request_id,
                    "response": normalized,
                    "error": error,
                },
            )
            if error is None:
                normalized_for_cache, benchmark_metadata = _split_benchmark_metadata(
                    normalized
                )
                cache.put(
                    cache_key,
                    {
                        "provider_id": metadata.provider_id,
                        "model_id": metadata.model_id,
                        "request_id": request_id,
                        "normalized_theme_json": normalized_for_cache,
                        "benchmark_metadata": benchmark_metadata,
                        "latency_ms": latency_ms,
                        "parameters": metadata.parameters,
                    },
                )
            result = _result(
                provider_id=metadata.provider_id,
                model_id=metadata.model_id,
                request=request,
                request_id=request_id,
                cache_key=cache_key,
                normalized=normalized,
                latency_ms=latency_ms,
                cache_hit=False,
                error=error,
                raw_response_path=str(raw_path.relative_to(root)),
            )
            provider_results.append(result)

        write_jsonl(generation_path, provider_results)
        results_by_provider[metadata.provider_id] = provider_results
        outbound_after = request_budget.used if request_budget is not None else 0
        stats_by_provider[metadata.provider_id] = BenchmarkProviderStats(
            provider_id=metadata.provider_id,
            request_count=len(provider_requests),
            result_count=len(provider_results),
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            provider_executions=provider_executions,
            outbound_requests=outbound_after - outbound_before,
            failures=failures,
        )

    summary_path = (
        root / "scores" / f"{split}_summary.parquet"
        if split
        else root / "scores" / "summary.parquet"
    )
    write_summary(
        summary_path, _collect_generation_results(root, split, results_by_provider)
    )
    _update_manifest(
        root,
        list(stats_by_provider),
        stats_by_provider,
        metadata_by_provider,
        split=split,
    )
    return BenchmarkRunReport(
        request_count=sum(stats.request_count for stats in stats_by_provider.values()),
        result_count=sum(stats.result_count for stats in stats_by_provider.values()),
        cache_hits=sum(stats.cache_hits for stats in stats_by_provider.values()),
        cache_misses=sum(stats.cache_misses for stats in stats_by_provider.values()),
        provider_executions=sum(
            stats.provider_executions for stats in stats_by_provider.values()
        ),
        outbound_requests=sum(
            stats.outbound_requests for stats in stats_by_provider.values()
        ),
        failures=sum(stats.failures for stats in stats_by_provider.values()),
        providers=stats_by_provider,
        results_by_provider=results_by_provider,
    )


def _result(
    *,
    provider_id: str,
    model_id: str,
    request,
    request_id: str,
    cache_key: str,
    normalized: dict[str, Any],
    latency_ms: float | None,
    cache_hit: bool,
    error: str | None = None,
    raw_response_path: str | None = None,
    benchmark_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized, metadata = _split_benchmark_metadata(normalized)
    metadata = {**metadata, **(benchmark_metadata or {})}
    result = ThemeBenchmarkResult(
        provider_id=provider_id,
        model_id=model_id,
        request_id=request_id,
        example_id=request.example_id,
        keyword_mode=request.keyword_mode,
        input_hash=request.input_hash,
        prompt_hash=request.prompt_hash,
        cache_key=cache_key,
        normalized_theme_json=_normalize_theme_json(normalized, request.keywords),
        latency_ms=latency_ms,
        cache_hit=cache_hit,
        error=error,
        raw_response_path=raw_response_path,
        usage=metadata.get("usage"),
        retries=int(metadata.get("retries", 0) or 0),
        parsed_successfully=metadata.get("parsed_successfully"),
        schema_valid=metadata.get("schema_valid"),
        finish_reason=metadata.get("finish_reason"),
        safety_metadata=metadata.get("safety_metadata"),
        raw_metadata=metadata.get("raw_metadata"),
        estimated_cost=metadata.get("estimated_cost"),
    ).to_dict()
    result["request_keywords"] = request.keywords
    return result


def _split_benchmark_metadata(
    value: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, dict):
        return {"themes": []}, {}
    metadata = value.get("_benchmark_metadata", {})
    normalized = {
        key: val for key, val in value.items() if key != "_benchmark_metadata"
    }
    return normalized, metadata if isinstance(metadata, dict) else {}


def _normalize_theme_json(
    value: Mapping[str, Any], allowed_keywords: list[str]
) -> dict[str, Any]:
    themes = value.get("themes", []) if isinstance(value, Mapping) else []
    allowed = set(allowed_keywords)
    normalized = []
    for theme in themes if isinstance(themes, list) else []:
        if not isinstance(theme, Mapping):
            continue
        keywords = [
            str(keyword)
            for keyword in theme.get("keywords", [])
            if str(keyword) in allowed
        ]
        normalized.append(
            {"name": str(theme.get("name", "")).strip(), "keywords": keywords}
        )
    return {"themes": normalized}


def _update_manifest(
    root: Path,
    provider_ids: list[str],
    stats_by_provider: dict[str, BenchmarkProviderStats],
    metadata_by_provider: dict[str, dict[str, Any]],
    *,
    split: str | None = None,
) -> None:
    manifest_path = root / "manifest.json"
    manifest = read_json(manifest_path)
    existing = list(manifest.get("providers", []))
    for provider_id in provider_ids:
        if provider_id not in existing:
            existing.append(provider_id)
    manifest["providers"] = existing
    if split:
        manifest["artifacts"].update(
            {
                f"{split}_generations": f"generations/{split}/",
                "cache": "cache/",
                f"{split}_scores": f"scores/{split}_summary.parquet",
                "split_distribution": "reports/split_distribution.json",
            }
        )
    else:
        manifest["artifacts"].update(
            {
                "generations": "generations/",
                "cache": "cache/",
                "scores": "scores/summary.parquet",
            }
        )
    stats_key = "benchmark_run_stats_by_split" if split else "benchmark_run_stats"
    if split:
        by_split = dict(manifest.get(stats_key, {}))
        split_stats = dict(by_split.get(split, {}))
        split_stats.update(
            {
                provider_id: stats.to_dict()
                for provider_id, stats in stats_by_provider.items()
            }
        )
        by_split[split] = split_stats
        manifest[stats_key] = by_split
    else:
        manifest[stats_key] = {
            provider_id: stats.to_dict()
            for provider_id, stats in stats_by_provider.items()
        }
    manifest["benchmark_provider_metadata"] = metadata_by_provider
    write_json(manifest_path, manifest)


def _collect_generation_results(
    root: Path,
    split: str | None,
    fallback: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    generation_dir = root / "generations" / split if split else root / "generations"
    if not generation_dir.exists():
        return fallback
    collected: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(generation_dir.glob("*.jsonl")):
        collected[path.stem] = read_jsonl(path)
    return collected or fallback


def _filter_unresolved_requests(
    requests,
    *,
    cache: JsonlResponseCache,
    metadata,
    max_unresolved_examples: int | None,
):
    unresolved = []
    for request in requests:
        cache_key = cache.cache_key(
            provider_id=metadata.provider_id,
            model_id=metadata.model_id,
            request=request,
            parameters=metadata.parameters,
        )
        if cache.get(cache_key) is None:
            unresolved.append(request)
    if max_unresolved_examples is None:
        return unresolved
    example_order: list[str] = []
    for request in unresolved:
        if request.example_id not in example_order:
            example_order.append(request.example_id)
    allowed = set(example_order[:max_unresolved_examples])
    return [request for request in unresolved if request.example_id in allowed]


def _filter_requests(
    requests,
    *,
    max_examples: int | None,
    keyword_modes: list[str] | None,
    split_example_ids: set[str] | None = None,
    example_ids: set[str] | None = None,
):
    filtered = [
        request
        for request in requests
        if not keyword_modes or request.keyword_mode in set(keyword_modes)
    ]
    if split_example_ids is not None:
        filtered = [
            request for request in filtered if request.example_id in split_example_ids
        ]
    if example_ids is not None:
        filtered = [
            request for request in filtered if request.example_id in example_ids
        ]
    if max_examples is None:
        return filtered
    example_order: list[str] = []
    for request in filtered:
        if request.example_id not in example_order:
            example_order.append(request.example_id)
    allowed = set(example_order[:max_examples])
    return [request for request in filtered if request.example_id in allowed]
