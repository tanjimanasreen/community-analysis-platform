from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.build_dashboard_fixture import build_fixture
from src.api.app import create_app
from src.api.dependencies import ApiSettings
from src.artifacts.run_manifest import validate_run_manifest


def _client(root: Path) -> TestClient:
    return TestClient(
        create_app(
            settings=ApiSettings(
                artifact_root=root,
                max_graph_nodes=200,
                max_graph_edges=500,
                catalog_refresh_seconds=0,
            )
        )
    )


def test_dashboard_fixture_is_deterministic_valid_and_covers_variants(tmp_path):
    paths = {name: Path(value) for name, value in build_fixture(tmp_path).items()}

    default_runs = sorted((paths["default"] / "runs").iterdir())
    assert {item.name for item in default_runs} >= {
        "twitter-2017-03",
        "twitter-2017-04",
        "telegram-2017-03",
        "twitter-2017-05-missing",
        "twitter-2017-06-empty",
        "twitter-2017-07-tampered",
    }

    for run_root in default_runs:
        if run_root.name == "twitter-2017-07-tampered":
            with pytest.raises(ValueError):
                validate_run_manifest(run_root)
        else:
            validate_run_manifest(run_root)

    client = _client(paths["default"])
    runs = client.get("/api/v1/runs").json()["runs"]
    assert runs[0]["run_id"] == "twitter-2017-04"

    graph = client.get(
        "/api/v1/runs/twitter-2017-04/network?metric=if&max_nodes=200&max_edges=500"
    )
    assert graph.status_code == 200
    assert graph.json()["sampled"] is True

    missing = client.get(
        "/api/v1/runs/twitter-2017-05-missing/topics?type=partial"
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "ARTIFACT_NOT_AVAILABLE"

    empty = client.get("/api/v1/runs/twitter-2017-06-empty/topics")
    assert empty.status_code == 200
    assert empty.json()["total"] == 0

    verification = client.get(
        "/api/v1/runs/twitter-2017-07-tampered/verification"
    )
    assert verification.status_code == 200
    assert verification.json()["ok"] is False

    no_runs_client = _client(paths["no_runs"])
    assert no_runs_client.get("/api/v1/runs").json() == {"runs": [], "total": 0}
