from pathlib import Path

from src.providers.base import BaseLLMProvider
from src.providers.cache_backends import (
    InMemoryThemeResponseCache,
    SQLiteThemeResponseCache,
)
from src.providers.cached import CachedProvider
from src.themes.benchmark.contracts import ProviderMetadata, ThemeBenchmarkRequest


class CountingProvider(BaseLLMProvider):
    rate_limit_rpm = 1000

    def __init__(self, *, model_id: str = "model-a", valid: bool = True) -> None:
        super().__init__()
        self.metadata = ProviderMetadata(
            provider_id="counting",
            model_id=model_id,
            parameters={"temperature": 0},
        )
        self.calls = 0
        self.valid = valid

    def generate(self, request: ThemeBenchmarkRequest):
        self.calls += 1
        if not self.valid:
            return {"themes": []}
        return {
            "themes": [{"name": "Theme", "keywords": list(request.keywords)}],
            "_benchmark_metadata": {"usage": {}},
        }


def test_ranked_exact_cache_distinguishes_keyword_order():
    inner = CountingProvider()
    cached = CachedProvider(inner, InMemoryThemeResponseCache())

    cached.generate_theme(["travel ban", "court"])
    cached.generate_theme(["court", "travel ban"])

    assert inner.calls == 2
    assert cached.run_metrics["cache_misses"] == 2


def test_sqlite_cache_is_shared_across_provider_instances(tmp_path: Path):
    path = tmp_path / "theme-cache.sqlite3"
    first_inner = CountingProvider()
    first = CachedProvider(first_inner, SQLiteThemeResponseCache(path))
    assert first.generate_theme(["travel ban", "court"]) == {
        "Theme": ["travel ban", "court"]
    }
    assert first_inner.calls == 1

    second_inner = CountingProvider()
    second = CachedProvider(second_inner, SQLiteThemeResponseCache(path))
    assert second.generate_theme(["travel ban", "court"]) == {
        "Theme": ["travel ban", "court"]
    }
    assert second_inner.calls == 0
    assert second.run_metrics["cache_hits"] == 1


def test_model_change_invalidates_sqlite_cache(tmp_path: Path):
    path = tmp_path / "theme-cache.sqlite3"
    CachedProvider(
        CountingProvider(model_id="model-a"), SQLiteThemeResponseCache(path)
    ).generate_theme(["keyword"])

    changed = CountingProvider(model_id="model-b")
    CachedProvider(changed, SQLiteThemeResponseCache(path)).generate_theme(["keyword"])
    assert changed.calls == 1


def test_invalid_empty_theme_response_is_not_cached():
    inner = CountingProvider(valid=False)
    cache = InMemoryThemeResponseCache()
    cached = CachedProvider(inner, cache)

    assert cached.generate_theme(["keyword"]) == {}
    assert cached.generate_theme(["keyword"]) == {}
    assert inner.calls == 2
    assert cache.write_count == 0
