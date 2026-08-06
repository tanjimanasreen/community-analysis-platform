"""Routing provider — fallback chain orchestrator for non-benchmark theme generation.

This module was previously located at src/themes/benchmark/routing_provider.py.
It has been moved to src/providers/routing.py because it is a provider-layer
concern, not a benchmark-specific concern.

The benchmark pipeline still accesses this class via
src.themes.benchmark.providers.get_provider("routing::<primary_id>").
The theme pipeline accesses it via src.providers.factory.build_theme_provider().
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Sequence

from src.themes.benchmark.contracts import (
    ProviderMetadata,
    ThemeBenchmarkError,
    ThemeBenchmarkRequest,
)

logger = logging.getLogger(__name__)


class RoutingBenchmarkProvider:
    """Fallback-chain provider for non-benchmark theme generation.

    Tries each provider in order. On rate limit or transient error, falls
    back to the next provider in the chain. Each provider respects its own
    rate_limit_rpm via internal sleep logic.

    NOT used in the benchmark pipeline — benchmark providers are evaluated
    independently without fallback.
    """

    def __init__(self, providers: Sequence[Any]) -> None:
        if not providers:
            raise ThemeBenchmarkError(
                "RoutingBenchmarkProvider requires at least one provider."
            )
        self.providers = list(providers)
        self._state = threading.local()
        self._metrics_lock = threading.Lock()
        self._fallback_attempts = 0

        # Metadata inherits from the primary provider
        primary_metadata = self.providers[0].metadata
        self.provider_id = f"routing::{primary_metadata.provider_id}"
        self.rate_limit_rpm = getattr(self.providers[0], "rate_limit_rpm", 0)

        aggregated_parameters = {
            "route": [
                {
                    "provider_id": p.metadata.provider_id,
                    "model_id": p.metadata.model_id,
                    "parameters": p.metadata.parameters,
                }
                for p in self.providers
            ],
        }
        self.metadata = ProviderMetadata(
            provider_id=self.provider_id,
            model_id=f"routing__{primary_metadata.model_id}",
            parameters=aggregated_parameters,
        )

    @property
    def last_generation_metadata(self) -> ProviderMetadata:
        """Metadata for the provider used by the current worker thread."""
        return getattr(self._state, "metadata", self.metadata)

    @property
    def run_metrics(self) -> dict[str, Any]:
        """Aggregate route metrics without exposing provider secrets."""
        totals: dict[str, Any] = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost": 0.0,
            "latency_ms_list": [],
            "ttft_ms_list": [],
            "tpot_ms_list": [],
            "prompts_and_responses": [],
            "calls": 0,
            "logical_theme_requests": 0,
            "outbound_requests": 0,
        }
        for provider in self.providers:
            metrics = getattr(provider, "run_metrics", {})
            for key in (
                "total_prompt_tokens",
                "total_completion_tokens",
                "total_cost",
                "calls",
                "logical_theme_requests",
                "outbound_requests",
            ):
                totals[key] += metrics.get(key, 0)
            for key in (
                "latency_ms_list",
                "ttft_ms_list",
                "tpot_ms_list",
                "prompts_and_responses",
            ):
                totals[key].extend(metrics.get(key, []))
        with self._metrics_lock:
            totals["fallback_attempts"] = self._fallback_attempts
        return totals

    def _record_fallback(self) -> None:
        with self._metrics_lock:
            self._fallback_attempts += 1

    def generate(self, request: ThemeBenchmarkRequest) -> dict[str, Any]:
        """Try each provider in order; fall back on any exception."""
        last_error: Exception | None = None
        fallback_attempts: list[dict[str, Any]] = []

        for i, provider in enumerate(self.providers):
            start_time = time.time()
            provider_id = provider.metadata.provider_id

            try:
                if i > 0:
                    logger.info(
                        "Attempting fallback provider %s for request %s",
                        provider_id,
                        request.example_id,
                    )
                result = provider.generate(request)
                self._state.metadata = provider.metadata
                if "_benchmark_metadata" in result:
                    result["_benchmark_metadata"][
                        "fallback_attempts"
                    ] = fallback_attempts
                return result

            except Exception as exc:
                if i < len(self.providers) - 1:
                    self._record_fallback()
                latency = time.time() - start_time
                error_msg = str(exc)
                last_error = exc
                fallback_attempts.append(
                    {
                        "provider_id": provider_id,
                        "error": error_msg,
                        "latency_seconds": round(latency, 2),
                    }
                )
                logger.warning(
                    "Provider %s failed on request %s after %.2fs. Error: %s",
                    provider_id,
                    request.example_id,
                    latency,
                    error_msg,
                )
                if i == len(self.providers) - 1:
                    logger.error(
                        "All %d providers in the fallback chain failed for request %s.",
                        len(self.providers),
                        request.example_id,
                    )
                    raise ThemeBenchmarkError(
                        f"Routing provider exhausted all fallbacks. Last error: {error_msg}"
                    ) from exc

    def generate_theme(self, keywords: list[str]) -> dict:
        """Fallback-aware theme generation for the theme pipeline."""
        last_error: Exception | None = None
        for i, provider in enumerate(self.providers):
            try:
                if i > 0:
                    logger.info(
                        "Fallback theme generation via %s",
                        provider.metadata.provider_id,
                    )
                result = provider.generate_theme(keywords)
                self._state.metadata = provider.metadata
                return result
            except Exception as exc:
                if i < len(self.providers) - 1:
                    self._record_fallback()
                last_error = exc
                logger.warning(
                    "Provider %s generate_theme() failed: %s",
                    provider.metadata.provider_id,
                    exc,
                )
                if i == len(self.providers) - 1:
                    raise ThemeBenchmarkError(
                        f"All providers exhausted during generate_theme(). Last: {exc}"
                    ) from exc

    def generate_text(self, prompt: str) -> str:
        """Fallback-aware text generation for the DeepEval judge pipeline."""
        last_error: Exception | None = None
        for i, provider in enumerate(self.providers):
            try:
                if i > 0:
                    logger.info(
                        "Fallback generate_text() via %s", provider.metadata.provider_id
                    )
                return provider.generate_text(prompt)
            except NotImplementedError:
                continue
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Provider %s generate_text() failed: %s",
                    provider.metadata.provider_id,
                    exc,
                )
                if i == len(self.providers) - 1:
                    raise ThemeBenchmarkError(
                        f"All providers exhausted during generate_text(). Last: {last_error}"
                    ) from last_error
