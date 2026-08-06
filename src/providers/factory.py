"""Provider factory — single entry point for theme-generation provider construction.

Reads `theme_provider` settings from the merged run config (which inherits from
configs/providers.yml) and builds the appropriate BaseLLMProvider instance.

The benchmark pipeline MUST NOT use this factory — benchmark providers are
constructed directly via src.themes.benchmark.providers.get_provider() so each
model is evaluated independently without fallback interference.

Usage:
    config = load_config("configs/longitudinal/sample_twitter_reply_04.yml")
    provider = build_theme_provider(config)
    themes = provider.generate_theme(["apple", "orange", "discussion"])
"""

from __future__ import annotations

from typing import Any

from src.providers.base import BaseLLMProvider
from src.providers.cached import CachedProvider


def build_theme_provider(config: dict[str, Any]) -> BaseLLMProvider:
    """Construct the theme-generation provider from a merged YAML config dict.

    Reads config["theme_provider"]:
      primary:        provider spec string (e.g. "mock", "gemini:gemini-3.1-flash-lite")
      fallback:       bool — if True and fallback_chain is non-empty, wraps primary
                      in RoutingBenchmarkProvider with the fallback chain
      fallback_chain: ordered list of fallback provider specs (real APIs only)

    All providers are wrapped in CachedProvider so repeated exact ordered
    keyword requests can be reused within a run and, for SQLite, across runs.

    Raises:
      ValueError: if the primary or any fallback provider spec is unrecognised.
    """
    theme_cfg = config.get("theme_provider", {})
    primary_id: str = theme_cfg.get("primary", "mock")
    use_fallback: bool = bool(theme_cfg.get("fallback", False))
    fallback_chain: list[str] = theme_cfg.get("fallback_chain", [])

    # Read rate limits from the providers registry (inherited via providers.yml include)
    providers_registry = config.get("providers", {})

    def _get(provider_id: str) -> BaseLLMProvider:
        """Resolve a provider spec string to a BaseLLMProvider instance."""
        from src.themes.benchmark.providers import get_provider

        # get_provider reads the provider-specific rate limit from the same
        # merged config. Timeouts and retries are operational controls and do
        # not affect analytical cache identity.
        prefix = provider_id.split(":", 1)[0] if ":" in provider_id else provider_id
        provider_cfg = providers_registry.get(prefix, {})
        is_live = prefix not in {"mock", "keyword_baseline"}
        max_outbound_requests = int(theme_cfg.get("max_outbound_requests", 10000))
        max_retries = int(
            provider_cfg.get("max_retries", theme_cfg.get("max_retries", 2))
        )
        timeout = provider_cfg.get("timeout_seconds", theme_cfg.get("timeout_seconds"))
        return get_provider(
            provider_id,
            config=config,
            allow_live=is_live,
            max_retries=max_retries,
            timeout=float(timeout) if timeout is not None else None,
            max_outbound_requests=max_outbound_requests,
        )

    primary = _get(primary_id)

    if use_fallback and fallback_chain:
        from src.providers.routing import RoutingBenchmarkProvider

        fallbacks = [_get(fid) for fid in fallback_chain]
        provider: BaseLLMProvider = RoutingBenchmarkProvider([primary] + fallbacks)
    else:
        provider = primary

    primary_prefix = primary_id.split(":", 1)[0]
    default_cache_backend = (
        "memory" if primary_prefix in {"mock", "keyword_baseline"} else "sqlite"
    )
    cache_backend = str(theme_cfg.get("cache_backend", default_cache_backend)).lower()
    cache_path = theme_cfg.get("cache_path", ".cache/theme_cache.sqlite3")
    failure_policy = str(theme_cfg.get("cache_failure_policy", "bypass")).lower()

    if cache_backend == "sqlite":
        from src.providers.cache_backends import SQLiteThemeResponseCache

        cache = SQLiteThemeResponseCache(cache_path, failure_policy=failure_policy)
    elif cache_backend == "memory":
        from src.providers.cache_backends import InMemoryThemeResponseCache

        cache = InMemoryThemeResponseCache()
    elif cache_backend in {"none", "disabled"}:
        from src.providers.cache_backends import NullThemeResponseCache

        cache = NullThemeResponseCache()
    else:
        raise ValueError(
            f"Unknown cache backend: {cache_backend!r}; expected sqlite, memory, or none"
        )

    return CachedProvider(provider, cache=cache)
