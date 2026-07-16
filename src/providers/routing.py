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

        # Metadata inherits from the primary provider
        primary_metadata = self.providers[0].metadata
        self.provider_id = f"routing::{primary_metadata.provider_id}"
        self.rate_limit_rpm = getattr(self.providers[0], "rate_limit_rpm", 0)

        aggregated_parameters = {
            "primary": primary_metadata.parameters,
            "fallback_chain": [p.metadata.provider_id for p in self.providers],
        }
        self.metadata = ProviderMetadata(
            provider_id=self.provider_id,
            model_id=f"routing__{primary_metadata.model_id}",
            parameters=aggregated_parameters,
        )

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
                if "_benchmark_metadata" in result:
                    result["_benchmark_metadata"][
                        "fallback_attempts"
                    ] = fallback_attempts
                return result

            except Exception as exc:
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

    def generate_theme(self, text: str) -> dict:
        """Fallback-aware theme generation for the theme pipeline."""
        last_error: Exception | None = None
        for i, provider in enumerate(self.providers):
            try:
                if i > 0:
                    logger.info(
                        "Fallback theme generation via %s",
                        provider.metadata.provider_id,
                    )
                return provider.generate_theme(text)
            except Exception as exc:
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
