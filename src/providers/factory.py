"""Provider factory — single entry point for theme-generation provider construction.

Reads `theme_provider` settings from the merged run config (which inherits from
configs/providers.yml) and builds the appropriate BaseLLMProvider instance.

The benchmark pipeline MUST NOT use this factory — benchmark providers are
constructed directly via src.themes.benchmark.providers.get_provider() so each
model is evaluated independently without fallback interference.

Usage:
    config = load_config("configs/longitudinal/sample_twitter_reply_04.yml")
    provider = build_theme_provider(config)
    themes = provider.generate_theme("apple, orange, discussion")
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

    All providers are wrapped in CachedProvider so repeated calls with the
    same text do not make redundant API requests within a single pipeline run.

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

        # Respect rate_limit_rpm from providers.yml
        prefix = provider_id.split(":", 1)[0] if ":" in provider_id else provider_id
        rate_limit_rpm = providers_registry.get(prefix, {}).get("rate_limit_rpm")

        kwargs: dict[str, Any] = {"config": config, "allow_live": False}
        if rate_limit_rpm is not None:
            kwargs["rate_limit_rpm"] = rate_limit_rpm  # type: ignore[arg-type]

        try:
            return get_provider(provider_id, **kwargs)
        except TypeError:
            # get_provider may not accept rate_limit_rpm as a kwarg for all providers
            return get_provider(provider_id, config=config, allow_live=False)

    primary = _get(primary_id)

    if use_fallback and fallback_chain:
        from src.providers.routing import RoutingBenchmarkProvider

        fallbacks = [_get(fid) for fid in fallback_chain]
        provider: BaseLLMProvider = RoutingBenchmarkProvider([primary] + fallbacks)
    else:
        provider = primary

    return CachedProvider(provider)
