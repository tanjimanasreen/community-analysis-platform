"""Unit tests for src/providers/factory.py.

All tests use mock provider only — no live API calls.
"""
import pytest

from src.providers.cached import CachedProvider
from src.providers.factory import build_theme_provider
from src.providers.mock import MockProvider
from src.providers.routing import RoutingBenchmarkProvider


def _mock_config(primary="mock", fallback=False, fallback_chain=None):
    return {
        "theme_provider": {
            "primary": primary,
            "fallback": fallback,
            "fallback_chain": fallback_chain or [],
        },
        "providers": {
            "mock": {"rate_limit_rpm": 1000, "models": ["deterministic-mock-theme-v2"]},
            "llm7": {"rate_limit_rpm": 10, "models": ["fast"]},
        },
    }


def test_factory_returns_cached_provider():
    """Factory always wraps the resolved provider in CachedProvider."""
    provider = build_theme_provider(_mock_config())
    assert isinstance(provider, CachedProvider)


def test_factory_fallback_false_primary_only():
    """When fallback=False, the primary provider is used directly (inside CachedProvider)."""
    config = _mock_config(primary="mock", fallback=False)
    provider = build_theme_provider(config)
    assert isinstance(provider, CachedProvider)
    # Inner provider should be MockProvider, not RoutingBenchmarkProvider
    assert not isinstance(provider._provider, RoutingBenchmarkProvider)


def test_factory_fallback_true_wraps_in_routing():
    """When fallback=True with a non-empty chain, wraps in RoutingBenchmarkProvider."""
    config = _mock_config(primary="mock", fallback=True, fallback_chain=["mock"])
    provider = build_theme_provider(config)
    assert isinstance(provider, CachedProvider)
    assert isinstance(provider._provider, RoutingBenchmarkProvider)


def test_factory_fallback_true_empty_chain_no_routing():
    """When fallback=True but fallback_chain is empty, routing is not used."""
    config = _mock_config(primary="mock", fallback=True, fallback_chain=[])
    provider = build_theme_provider(config)
    assert isinstance(provider, CachedProvider)
    assert not isinstance(provider._provider, RoutingBenchmarkProvider)


def test_factory_mock_generate_theme():
    """Factory-built mock provider returns expected theme structure."""
    provider = build_theme_provider(_mock_config(primary="mock", fallback=False))
    result = provider.generate_theme("apple orange discussion")
    assert isinstance(result, dict)
    assert len(result) > 0


def test_factory_cache_avoids_duplicate_calls():
    """CachedProvider caches generate_theme responses by text key."""
    provider = build_theme_provider(_mock_config())
    text = "apple orange"
    _ = provider.generate_theme(text)
    _ = provider.generate_theme(text)
    assert provider.cache_size == 1


def test_factory_config_without_theme_provider_uses_defaults():
    """Empty config falls back to defaults (mock primary, no fallback)."""
    provider = build_theme_provider({})
    assert isinstance(provider, CachedProvider)
    result = provider.generate_theme("test keyword")
    assert isinstance(result, dict)
