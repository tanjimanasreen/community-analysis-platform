"""Unit tests for TEI health readiness polling (wait_for_tei_services)."""

from __future__ import annotations

import pytest

from src.themes.tei_health import wait_for_tei_services


def test_wait_for_tei_services_skips_when_mock():
    config = {
        "theme": {
            "similarity_provider": "mock",
            "clustering_provider": "mock",
        }
    }
    result = wait_for_tei_services(config)
    assert result == {}


def test_wait_for_tei_services_similarity_only_success(monkeypatch):
    calls = []

    def fake_dims(
        base_url: str,
        api_key: str | None,
        *,
        timeout: float = 5.0,
        normalize: bool = True,
    ) -> int:
        calls.append((base_url, api_key, timeout, normalize))
        return 384

    monkeypatch.setattr("src.themes.tei_health.embedding_dimensions", fake_dims)

    config = {
        "theme": {
            "similarity_provider": "tei",
            "clustering_provider": "mock",
        },
    }
    monkeypatch.setenv("THEME_SIMILARITY_PROVIDER", "tei")
    monkeypatch.setenv("TEI_SIMILARITY_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("TEI_SIMILARITY_API_KEY", "sim-key")

    result = wait_for_tei_services(config, attempts=3, interval=0.01)
    assert result == {"similarity": 384}
    assert len(calls) == 1
    assert calls[0][0] == "http://127.0.0.1:8080"
    assert calls[0][1] == "sim-key"
    assert calls[0][3] is True


def test_wait_for_tei_services_clustering_only_success(monkeypatch):
    calls = []

    def fake_dims(
        base_url: str,
        api_key: str | None,
        *,
        timeout: float = 5.0,
        normalize: bool = True,
    ) -> int:
        calls.append((base_url, api_key, timeout, normalize))
        return 384

    monkeypatch.setattr("src.themes.tei_health.embedding_dimensions", fake_dims)

    config = {
        "theme": {
            "similarity_provider": "mock",
            "clustering_provider": "tei",
        },
    }
    monkeypatch.setenv("THEME_CLUSTERING_PROVIDER", "tei")
    monkeypatch.setenv("TEI_CLUSTERING_BASE_URL", "http://127.0.0.1:8081")
    monkeypatch.setenv("TEI_CLUSTERING_API_KEY", "clust-key")

    result = wait_for_tei_services(config, attempts=3, interval=0.01)
    assert result == {"clustering": 384}
    assert len(calls) == 1
    assert calls[0][0] == "http://127.0.0.1:8081"
    assert calls[0][1] == "clust-key"
    assert calls[0][3] is False


def test_wait_for_tei_services_both_success(monkeypatch):
    calls = []

    def fake_dims(
        base_url: str,
        api_key: str | None,
        *,
        timeout: float = 5.0,
        normalize: bool = True,
    ) -> int:
        calls.append(base_url)
        return 384

    monkeypatch.setattr("src.themes.tei_health.embedding_dimensions", fake_dims)

    config = {
        "theme": {
            "similarity_provider": "tei",
            "clustering_provider": "tei",
        },
    }
    monkeypatch.setenv("THEME_SIMILARITY_PROVIDER", "tei")
    monkeypatch.setenv("THEME_CLUSTERING_PROVIDER", "tei")
    monkeypatch.setenv("TEI_SIMILARITY_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("TEI_CLUSTERING_BASE_URL", "http://127.0.0.1:8081")

    result = wait_for_tei_services(config, attempts=3, interval=0.01)
    assert result == {"similarity": 384, "clustering": 384}
    assert set(calls) == {"http://127.0.0.1:8080", "http://127.0.0.1:8081"}


def test_wait_for_tei_services_retries_until_success(monkeypatch):
    attempts = 0

    def fake_dims(
        base_url: str,
        api_key: str | None,
        *,
        timeout: float = 5.0,
        normalize: bool = True,
    ) -> int:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Service not ready yet")
        return 384

    monkeypatch.setattr("src.themes.tei_health.embedding_dimensions", fake_dims)

    config = {
        "theme": {
            "similarity_provider": "tei",
            "clustering_provider": "mock",
        },
    }
    monkeypatch.setenv("THEME_SIMILARITY_PROVIDER", "tei")
    monkeypatch.setenv("TEI_SIMILARITY_BASE_URL", "http://127.0.0.1:8080")

    result = wait_for_tei_services(config, attempts=5, interval=0.01)
    assert result == {"similarity": 384}
    assert attempts == 3


def test_wait_for_tei_services_timeout_raises_runtime_error(monkeypatch):
    def fake_dims(
        base_url: str,
        api_key: str | None,
        *,
        timeout: float = 5.0,
        normalize: bool = True,
    ) -> int:
        raise ConnectionError("Service unavailable")

    monkeypatch.setattr("src.themes.tei_health.embedding_dimensions", fake_dims)

    config = {
        "theme": {
            "similarity_provider": "tei",
            "clustering_provider": "mock",
        },
    }
    monkeypatch.setenv("THEME_SIMILARITY_PROVIDER", "tei")
    monkeypatch.setenv("TEI_SIMILARITY_BASE_URL", "http://127.0.0.1:8080")

    with pytest.raises(RuntimeError, match="similarity.*failed readiness check"):
        wait_for_tei_services(config, attempts=2, interval=0.01)


def test_wait_for_tei_services_dimension_mismatch_raises(monkeypatch):
    def fake_dims(
        base_url: str,
        api_key: str | None,
        *,
        timeout: float = 5.0,
        normalize: bool = True,
    ) -> int:
        return 768

    monkeypatch.setattr("src.themes.tei_health.embedding_dimensions", fake_dims)

    config = {
        "theme": {
            "similarity_provider": "tei",
            "clustering_provider": "mock",
        },
    }
    monkeypatch.setenv("THEME_SIMILARITY_PROVIDER", "tei")
    monkeypatch.setenv("TEI_SIMILARITY_BASE_URL", "http://127.0.0.1:8080")

    with pytest.raises(RuntimeError, match="dimension 768.*expected 384"):
        wait_for_tei_services(config, attempts=1, interval=0.01)
