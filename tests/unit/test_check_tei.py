from __future__ import annotations

import sys

from scripts import check_tei


def test_check_tei_validates_both_profiles(monkeypatch):
    calls: list[tuple[str, str | None]] = []

    def fake_embed(base_url: str, api_key: str | None, timeout: float) -> int:
        assert timeout == 5.0
        calls.append((base_url, api_key))
        return 384

    monkeypatch.setattr(check_tei, "_embed", fake_embed)
    monkeypatch.setenv("TEI_SIMILARITY_BASE_URL", "http://similarity.test:8080")
    monkeypatch.setenv("TEI_CLUSTERING_BASE_URL", "http://clustering.test:8081")
    monkeypatch.setenv("TEI_SIMILARITY_API_KEY", "similarity-secret")
    monkeypatch.setenv("TEI_CLUSTERING_API_KEY", "clustering-secret")
    monkeypatch.setattr(sys, "argv", ["check_tei.py"])

    assert check_tei.main() == 0
    assert calls == [
        ("http://similarity.test:8080", "similarity-secret"),
        ("http://clustering.test:8081", "clustering-secret"),
    ]


def test_check_tei_fails_when_either_profile_is_unhealthy(monkeypatch):
    def fake_embed(base_url: str, api_key: str | None, timeout: float) -> int:
        del api_key, timeout
        if "clustering" in base_url:
            raise OSError("service unavailable")
        return 384

    monkeypatch.setattr(check_tei, "_embed", fake_embed)
    monkeypatch.setenv("TEI_SIMILARITY_BASE_URL", "http://similarity.test:8080")
    monkeypatch.setenv("TEI_CLUSTERING_BASE_URL", "http://clustering.test:8081")
    monkeypatch.setattr(sys, "argv", ["check_tei.py"])

    assert check_tei.main() == 1
