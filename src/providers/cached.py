"""In-memory caching wrapper for any BaseLLMProvider.

Wraps a provider and caches generate_theme() responses by keyword text.
Useful for avoiding redundant API calls in the theme pipeline when the same
community message text is processed multiple times in one run.

Note: the cache is not persisted across runs. For persistent caching,
see src/themes/benchmark/cache.py (JSONL-based benchmark response cache).
"""

from __future__ import annotations

from typing import Any

from src.providers.base import BaseLLMProvider
from src.themes.benchmark.contracts import ProviderMetadata, ThemeBenchmarkRequest


class CachedProvider(BaseLLMProvider):
    """In-memory response cache wrapper for the theme pipeline.

    Delegates all calls to the wrapped provider and caches generate_theme()
    responses by text key to avoid duplicate API calls within a single run.
    """

    def __init__(self, provider: BaseLLMProvider, cache: dict[str, dict] | None = None) -> None:
        self._provider = provider
        self._cache: dict[str, dict] = cache if cache is not None else {}
        self.rate_limit_rpm = getattr(provider, "rate_limit_rpm", 0)
        # Inherit metadata from the wrapped provider with a cache prefix
        inner_meta = getattr(provider, "metadata", None)
        if inner_meta is not None:
            self.metadata = ProviderMetadata(
                provider_id=f"cached::{inner_meta.provider_id}",
                model_id=inner_meta.model_id,
                parameters=inner_meta.parameters,
            )
        else:
            self.metadata = ProviderMetadata(
                provider_id="cached::unknown",
                model_id="unknown",
                parameters={},
            )

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    def generate(self, request: ThemeBenchmarkRequest) -> dict[str, Any]:
        """Delegate to the wrapped provider — benchmark calls are not cached."""
        return self._provider.generate(request)

    def generate_theme(self, text: str) -> dict:
        """Return cached response if available; otherwise call provider and cache."""
        if text not in self._cache:
            self._cache[text] = self._provider.generate_theme(text)
        return self._cache[text]

    def generate_text(self, prompt: str) -> str:
        """Delegate to the wrapped provider — text generation is not cached."""
        return self._provider.generate_text(prompt)
