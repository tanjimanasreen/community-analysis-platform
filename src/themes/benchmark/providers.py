from __future__ import annotations

from typing import Any, Mapping, Protocol

from src.themes.benchmark.contracts import ProviderMetadata, ThemeBenchmarkRequest


class ThemeBenchmarkProvider(Protocol):
    metadata: ProviderMetadata

    def generate(self, request: ThemeBenchmarkRequest) -> dict:
        ...


from src.providers.mock import BenchmarkMockProvider, KeywordBaselineProvider


def get_provider(
    provider_id: str,
    *,
    config: Mapping[str, Any] | None = None,
    allow_live: bool = False,
    max_retries: int = 2,
    timeout: float | None = None,
    max_outbound_requests: int = 50,
    request_budget=None,
    benchmark_run_dir=None,
) -> ThemeBenchmarkProvider:
    provider_prefix = provider_id.split(":", 1)[0] if ":" in provider_id else provider_id
    rate_limit_rpm = None
    if config and "providers" in config and provider_prefix in config["providers"]:
        rate_limit_rpm = config["providers"][provider_prefix].get("rate_limit_rpm")

    if provider_id.startswith("gemini:"):
        from src.providers.gemini import GeminiBenchmarkProvider

        model_id = provider_id.split(":", 1)[1].strip()
        kwargs = {
            "model_id": model_id,
            "allow_live": allow_live,
            "max_retries": max_retries,
            "timeout": timeout,
            "max_outbound_requests": max_outbound_requests,
            "request_budget": request_budget,
        }
        if rate_limit_rpm is not None:
            kwargs["rate_limit_rpm"] = rate_limit_rpm
        return GeminiBenchmarkProvider(**kwargs)

    if provider_id.startswith("llm7:"):
        from src.providers.llm7 import (
            LLM7BenchmarkProvider,
            load_approved_llm7_selection,
        )

        model_id = provider_id.split(":", 1)[1].strip()
        model_catalog_record = (
            load_approved_llm7_selection(benchmark_run_dir, model_id)
            if benchmark_run_dir is not None
            else None
        )
        kwargs = {
            "model_id": model_id,
            "allow_live": allow_live,
            "max_retries": max_retries,
            "timeout": timeout,
            "max_outbound_requests": max_outbound_requests,
            "request_budget": request_budget,
            "model_catalog_record": model_catalog_record,
        }
        if rate_limit_rpm is not None:
            kwargs["rate_limit_rpm"] = rate_limit_rpm
        return LLM7BenchmarkProvider(**kwargs)

    if provider_id.startswith("nvidia:"):
        from src.providers.nvidia import NvidiaBenchmarkProvider
        
        model_id = provider_id.split(":", 1)[1].strip()
        kwargs = {
            "model_id": model_id,
            "allow_live": allow_live,
            "max_retries": max_retries,
            "timeout": timeout,
            "max_outbound_requests": max_outbound_requests,
            "request_budget": request_budget,
        }
        if rate_limit_rpm is not None:
            kwargs["rate_limit_rpm"] = rate_limit_rpm
        return NvidiaBenchmarkProvider(**kwargs)

    if provider_id.startswith("routing:"):
        from src.providers.routing import RoutingBenchmarkProvider
        
        chain_str = provider_id.split(":", 1)[1].strip()
        provider_strings = [p.strip() for p in chain_str.split(",") if p.strip()]
        
        providers = []
        for p_str in provider_strings:
            providers.append(
                get_provider(
                    p_str,
                    config=config,
                    allow_live=allow_live,
                    max_retries=max_retries,
                    timeout=timeout,
                    max_outbound_requests=max_outbound_requests,
                    request_budget=request_budget,
                    benchmark_run_dir=benchmark_run_dir,
                )
            )
            
        return RoutingBenchmarkProvider(providers)

    providers = {
        "keyword_baseline": KeywordBaselineProvider,
        "mock": BenchmarkMockProvider,
    }
    try:
        return providers[provider_id]()
    except KeyError as exc:
        raise ValueError(
            f"Unsupported offline benchmark provider {provider_id!r}; "
            "available providers are keyword_baseline,mock."
        ) from exc
