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

    import pandas as pd

    telegram_network = pd.read_parquet(
        paths["default"] / "runs" / "telegram-2017-03" / "data" / "network" / "network.parquet"
    )
    assert "forwarded_date" in telegram_network.columns
    assert "created_at" not in telegram_network.columns

    twitter_network = pd.read_parquet(
        paths["default"] / "runs" / "twitter-2017-04" / "data" / "network" / "network.parquet"
    )
    assert "created_at" in twitter_network.columns
    assert "forwarded_date" not in twitter_network.columns

    client = _client(paths["default"])
    runs = client.get("/api/v1/runs").json()["runs"]
    assert runs[0]["run_id"] == "twitter-2017-04"

    graph = client.get(
        "/api/v1/runs/twitter-2017-04/network?metric=if&max_nodes=200&max_edges=500"
    )
    assert graph.status_code == 200
    assert graph.json()["sampled"] is True

    retweet_overview = client.get("/api/v1/runs/twitter-2017-04-retweet/overview")
    assert retweet_overview.status_code == 200
    assert retweet_overview.json()["available_periods"] == [
        "2017-01",
        "2017-02",
        "2017-03",
        "2017-04",
    ]

    retweet_month = client.get(
        "/api/v1/runs/twitter-2017-04-retweet/theme-trends/monthly" "?period=2017-01"
    )
    assert retweet_month.status_code == 200
    assert retweet_month.json()["total_themed_community_pairs"] == 3
    assert retweet_month.json()["themes"][0]["name"] == (
        "US Immigration Policy and Protests"
    )

    retweet_timeline = client.get(
        "/api/v1/runs/twitter-2017-04-retweet/theme-trends/timeline"
    )
    assert retweet_timeline.status_code == 200
    assert retweet_timeline.json()["available_periods"] == [
        "2017-01",
        "2017-02",
        "2017-03",
        "2017-04",
    ]
    assert len(retweet_timeline.json()["monthly_summaries"]) == 4

    retweet_transitions = client.get(
        "/api/v1/runs/twitter-2017-04-retweet/transitions?limit=1000"
    )
    assert retweet_transitions.status_code == 200
    assert retweet_transitions.json()["total"] == 6

    evolution_paths = client.get("/api/v1/runs/twitter-2017-04-retweet/evolution/paths")
    assert evolution_paths.status_code == 200
    assert evolution_paths.json()["total"] == 2
    assert evolution_paths.json()["methodology"]["transition_threshold"] == 0.5
    first_path = evolution_paths.json()["paths"][0]
    assert first_path["duration"] == 4

    mobility = client.get(
        f"/api/v1/runs/twitter-2017-04-retweet/evolution/paths/{first_path['path_id']}/mobility"
    )
    assert mobility.status_code == 200
    assert any(
        record["reappearing_count"] == 1 for record in mobility.json()["records"]
    )

    similarity = client.get(
        f"/api/v1/runs/twitter-2017-04-retweet/evolution/paths/{first_path['path_id']}/theme-similarity?theme_type=general"
    )
    assert similarity.status_code == 200
    assert (
        similarity.json()["embedding_model"]
        == "sentence-transformers/paraphrase-MiniLM-L6-v2"
    )
    assert len(similarity.json()["matrix"]) == 4

    missing = client.get("/api/v1/runs/twitter-2017-05-missing/topics?type=partial")
    assert missing.status_code == 404
    assert missing.json()["code"] == "ARTIFACT_NOT_AVAILABLE"

    empty = client.get("/api/v1/runs/twitter-2017-06-empty/topics")
    assert empty.status_code == 200
    assert empty.json()["total"] == 0

    verification = client.get("/api/v1/runs/twitter-2017-07-tampered/verification")
    assert verification.status_code == 200
    assert verification.json()["ok"] is False

    no_runs_client = _client(paths["no_runs"])
    assert no_runs_client.get("/api/v1/runs").json() == {"runs": [], "total": 0}


def test_cluster_fixture_includes_long_valid_theme_text_for_layout_guard():
    from scripts.build_dashboard_fixture import RUN_SPECS, _cluster_fixture_rows

    spec = next(item for item in RUN_SPECS if item.run_id == "twitter-2017-04-retweet")
    rows, _ = _cluster_fixture_rows(spec, month=3)

    long_label = (
        "Cross-platform civic discussion of public accountability and "
        "institutional response"
    )
    assert any(row["canonical_theme_label"] == long_label for row in rows)
    assert any(
        "community_led_cross_platform_public_accountability_discussion"
        in row["prominent_keywords"]
        for row in rows
    )
    assert all(
        row["excluded_records_ambiguous_general_theme_serialization"] == 0
        for row in rows
    )
