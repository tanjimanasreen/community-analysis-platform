from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencies import ApiSettings
from src.artifacts.models import (
    ArtifactCategory,
    ArtifactRecord,
    RunManifest,
    RunStatus,
)
from src.reporting import output_contract as contract


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_parquet(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=columns).to_parquet(path, index=False)


def _record(
    root: Path,
    key: str,
    relative: str,
    category: ArtifactCategory,
    media_type: str,
    *,
    stage: str,
) -> ArtifactRecord:
    path = root / relative
    rows = None
    if path.suffix == ".parquet":
        rows = len(pd.read_parquet(path))
    elif path.suffix == ".csv":
        rows = len(pd.read_csv(path))
    return ArtifactRecord(
        key=key,
        path=relative,
        category=category,
        media_type=media_type,
        schema_version="1",
        sha256=_hash(path),
        rows=rows,
        byte_size=path.stat().st_size,
        stage=stage,
    )


def _build_run(
    artifact_root: Path,
    *,
    run_id: str = "run-03",
    month: str = "03",
    status: RunStatus = RunStatus.COMPLETED,
    include_similarity: bool = True,
) -> Path:
    root = artifact_root / "runs" / run_id
    root.mkdir(parents=True)
    (root / "inputs").mkdir()
    (root / "resolved_config.yaml").write_text(
        yaml.safe_dump(
            {
                "data_type": "twitter",
                "content_type": "reply",
                "month": month,
                "year": "2017",
                "graph_thresholds": {
                    "min_total_post": 10,
                    "min_shared_post": 5,
                },
                "louvain": {"resolution": 1, "seed": 123},
                "lda": {"num_topics": 15, "random_state": 100},
                "theme": {
                    "model": "gpt-4o",
                    "similarity_model": "paraphrase-MiniLM-L6-v2",
                },
                "database": {"password": "must-not-be-returned"},
            }
        ),
        encoding="utf-8",
    )
    (root / "inputs" / "datasets.json").write_text(
        json.dumps({"schema_version": "1.0", "datasets": []}),
        encoding="utf-8",
    )

    network_rows = [
        {
            "unique_id": f"m{index}",
            "from_id": f"u{index}",
            "forwarder_id": f"u{index + 1}",
            "text": "message",
            "created_at": "2017-03-01",
        }
        for index in range(1, 5)
    ]
    _write_parquet(
        root / "data/network/network.parquet",
        network_rows,
        contract.NETWORK_DATA_COLUMNS,
    )

    graph_rows = [
        {
            "source": "u1",
            "target": "u2",
            "community_number": 1,
            "direction": "out",
            "weight": 9.0,
        },
        {
            "source": "u2",
            "target": "u3",
            "community_number": 1,
            "direction": "out",
            "weight": 8.0,
        },
        {
            "source": "u4",
            "target": "u5",
            "community_number": 2,
            "direction": "out",
            "weight": 7.0,
        },
    ]
    _write_parquet(
        root / "data/communities/absolute/communities.parquet",
        graph_rows,
        contract.COMMUNITY_GRAPH_COLUMNS,
    )
    _write_parquet(
        root / "data/communities/weighted/communities.parquet",
        graph_rows,
        contract.COMMUNITY_GRAPH_COLUMNS,
    )
    _write_parquet(
        root / "data/communities/matched/matched.parquet",
        [
            {
                "month": month,
                "total_matched": 2,
                "total_absolute": 3,
                "total_weighted": 4,
            }
        ],
        contract.MATCHED_COMMUNITY_SUMMARY_COLUMNS,
    )
    _write_parquet(
        root / "data/metrics/count_user_messages/counts.parquet",
        [
            {
                "month": month,
                "user": "{'absolute': 5, 'weighted': 4}",
                "messages": "{'absolute': 20, 'weighted': 18}",
            }
        ],
        contract.COUNT_USER_MESSAGES_COLUMNS,
    )
    _write_parquet(
        root / "data/metrics/user_centrality/centrality.parquet",
        [{"month": month, "absolute": "{'u1': 0.5}", "weighted": "{'u1': 0.4}"}],
        contract.USER_CENTRALITY_COLUMNS,
    )

    topic_row = {
        "absolute_community": 1,
        "absolute_unigram_topic": "topic-a",
        "absolute_unigram_keywords": "['alpha', 'beta']",
        "weighted_community": 1,
        "weighted_unigram_topic": "topic-a",
        "weighted_unigram_keywords": "['alpha']",
        "absolute_bigram_topic": "topic-b",
        "absolute_bigram_keywords": "['alpha beta']",
        "weighted_bigram_topic": "topic-b",
        "weighted_bigram_keywords": "['alpha beta']",
        "members": "['u1', 'u2']",
    }
    _write_parquet(
        root / "data/topics/matched/topics.parquet",
        [topic_row, {**topic_row, "absolute_community": 2, "weighted_community": 2}],
        contract.MATCHED_LDA_COLUMNS,
    )

    themed_row = {
        **topic_row,
        "all_keywords": "['alpha', 'beta']",
        "absolute_keywords": "['alpha']",
        "weighted_keywords": "['beta']",
        "general_theme_gpt": "{'Policy': ['alpha']}",
        "general_theme_names": "['Policy']",
        "absolute_theme_gpt": "{'Policy': ['alpha']}",
        "absolute_theme_names": "['Policy']",
        "weighted_theme_gpt": "{'Policy': ['beta']}",
        "weighted_theme_names": "['Policy']",
    }
    _write_parquet(
        root / f"data/themes/monthly/{month}.parquet",
        [themed_row, themed_row],
        contract.THEMED_OUTPUT_COLUMNS,
    )

    transition_row = {
        "start_month": "03",
        "end_month": "04",
        "start_month_community": 1,
        "end_month_community": 2,
        "jaccard_score": 0.6,
        "common_members": "['u1']",
        "uncommon_members": "['u2', 'u3']",
        "start_month_members": "['u1', 'u2']",
        "total_start_month_members": 2,
        "end_month_members": "['u1', 'u3']",
        "total_end_month_members": 2,
        "start_month_absolute_theme": "Policy",
        "end_month_absolute_theme": "Policy",
        "start_month_weighted_theme": "Policy",
        "end_month_weighted_theme": "Policy",
        "start_month_general_theme": "Policy",
        "end_month_general_theme": "Policy",
    }
    _write_parquet(
        root / "data/themes/community_transition.parquet",
        [transition_row],
        contract.COMMUNITY_TRANSITION_COLUMNS,
    )
    (root / "data/themes/provider_run_summary.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "configured_primary_provider": "mock",
                "configured_primary_model": "mock-v1",
            }
        ),
        encoding="utf-8",
    )
    (root / "reports").mkdir(exist_ok=True)
    (root / "reports/report.html").write_text("<html>report</html>", encoding="utf-8")
    if include_similarity:
        (root / "reports/figures/theme_similarity").mkdir(parents=True)
        (root / "reports/figures/theme_similarity/general.png").write_bytes(b"png")

    records = [
        _record(
            root,
            "network_data",
            "data/network/network.parquet",
            ArtifactCategory.DATA,
            "application/vnd.apache.parquet",
            stage="network_community",
        ),
        _record(
            root,
            "communities_absolute",
            "data/communities/absolute/communities.parquet",
            ArtifactCategory.DATA,
            "application/vnd.apache.parquet",
            stage="network_community",
        ),
        _record(
            root,
            "communities_weighted",
            "data/communities/weighted/communities.parquet",
            ArtifactCategory.DATA,
            "application/vnd.apache.parquet",
            stage="network_community",
        ),
        _record(
            root,
            "communities_matched",
            "data/communities/matched/matched.parquet",
            ArtifactCategory.DATA,
            "application/vnd.apache.parquet",
            stage="network_community",
        ),
        _record(
            root,
            "count_user_messages",
            "data/metrics/count_user_messages/counts.parquet",
            ArtifactCategory.DATA,
            "application/vnd.apache.parquet",
            stage="network_community",
        ),
        _record(
            root,
            "user_centrality",
            "data/metrics/user_centrality/centrality.parquet",
            ArtifactCategory.DATA,
            "application/vnd.apache.parquet",
            stage="network_community",
        ),
        _record(
            root,
            "matched_communities_topics",
            "data/topics/matched/topics.parquet",
            ArtifactCategory.DATA,
            "application/vnd.apache.parquet",
            stage="topic",
        ),
        _record(
            root,
            f"themes_{month}",
            f"data/themes/monthly/{month}.parquet",
            ArtifactCategory.DATA,
            "application/vnd.apache.parquet",
            stage="theme",
        ),
        _record(
            root,
            "community_transitions",
            "data/themes/community_transition.parquet",
            ArtifactCategory.DATA,
            "application/vnd.apache.parquet",
            stage="theme",
        ),
        _record(
            root,
            "provider_run_summary",
            "data/themes/provider_run_summary.json",
            ArtifactCategory.DATA,
            "application/json",
            stage="theme",
        ),
        _record(
            root,
            "report_html",
            "reports/report.html",
            ArtifactCategory.REPORT,
            "text/html",
            stage="report",
        ),
    ]
    if include_similarity:
        records.append(
            _record(
                root,
                "visualization_theme_similarity_general.png",
                "reports/figures/theme_similarity/general.png",
                ArtifactCategory.REPORT,
                "image/png",
                stage="theme",
            )
        )

    manifest = RunManifest(
        run_id=run_id,
        status=status,
        dataset={
            "platform": "twitter",
            "content_type": "reply",
            "date_start": f"2017-{month}-01",
            "date_end": f"2017-{month}-28",
            "source_hash": "a" * 64,
        },
        code={"git_commit": "abc", "config_digest": "def"},
        pipeline={
            "started_at": "2026-07-17T00:00:00+00:00",
            "completed_at": "2026-07-17T00:01:00+00:00",
            "prefect_flow_run_id": "prefect-1",
            "mlflow_run_id": "mlflow-1",
        },
        artifacts=tuple(records),
    )
    (root / "manifest.json").write_text(
        json.dumps(manifest.to_dict()), encoding="utf-8"
    )
    return root


def _client(artifact_root: Path, *, max_nodes: int = 1000, max_edges: int = 5000):
    settings = ApiSettings(
        artifact_root=artifact_root,
        max_graph_nodes=max_nodes,
        max_graph_edges=max_edges,
        catalog_refresh_seconds=0,
    )
    return TestClient(create_app(settings=settings))


def test_run_catalog_filters_and_metadata_hide_absolute_paths(tmp_path):
    _build_run(tmp_path, run_id="march", month="03")
    _build_run(tmp_path, run_id="april", month="04")
    client = _client(tmp_path)

    response = client.get("/api/v1/runs?platform=twitter&year=2017&month=3")

    assert response.status_code == 200
    assert [item["run_id"] for item in response.json()["runs"]] == ["march"]
    assert str(tmp_path) not in response.text
    detail = client.get("/api/v1/runs/march").json()
    assert detail["pipeline"]["mlflow_run_id"] == "mlflow-1"


def test_verification_and_checksum_failure_are_explicit(tmp_path):
    root = _build_run(tmp_path)
    client = _client(tmp_path)

    assert client.get("/api/v1/runs/run-03/verification").json()["ok"] is True
    (root / "data/communities/absolute/communities.parquet").write_bytes(b"tampered")

    verification = client.get("/api/v1/runs/run-03/verification")
    assert verification.status_code == 200
    assert verification.json()["error_code"] in {
        "ARTIFACT_CHECKSUM_MISMATCH",
        "ARTIFACT_SCHEMA_MISMATCH",
    }
    network = client.get("/api/v1/runs/run-03/network")
    assert network.status_code == 409
    assert network.json()["code"] == "ARTIFACT_CHECKSUM_MISMATCH"


def test_overview_returns_precomputed_results_without_secrets(tmp_path):
    _build_run(tmp_path)
    client = _client(tmp_path)

    response = client.get("/api/v1/runs/run-03/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["total_users"] == 5
    assert body["total_messages"] == 20
    assert body["total_interactions"] == 4
    assert body["if_community_count"] == 3
    assert body["wif_community_count"] == 4
    assert body["matched_percentage"] == 50.0
    assert body["persistent_community_count"] == 1
    assert body["top_themes"] == [{"name": "Policy", "count": 2}]
    assert "password" not in response.text


def test_network_is_bounded_and_community_endpoints_are_chart_ready(tmp_path):
    _build_run(tmp_path)
    client = _client(tmp_path, max_nodes=3, max_edges=2)

    too_large = client.get("/api/v1/runs/run-03/network?max_nodes=4&max_edges=3")
    assert too_large.status_code == 413
    assert too_large.json()["code"] == "GRAPH_REQUEST_TOO_LARGE"

    graph = client.get("/api/v1/runs/run-03/network?metric=if&max_nodes=3&max_edges=2")
    assert graph.status_code == 200
    assert graph.json()["returned_nodes"] <= 3
    assert graph.json()["returned_edges"] <= 2
    assert graph.json()["sampled"] is True

    communities = client.get("/api/v1/runs/run-03/communities?metric=if")
    assert communities.status_code == 200
    assert communities.json()["total"] == 2
    detail = client.get(
        "/api/v1/runs/run-03/communities/1?metric=if&max_nodes=3&max_edges=2"
    )
    assert detail.status_code == 200
    assert detail.json()["community"]["node_count"] == 3


def test_topic_theme_pagination_and_lda_provenance(tmp_path):
    _build_run(tmp_path)
    client = _client(tmp_path)

    topics = client.get("/api/v1/runs/run-03/topics?limit=1&offset=1")
    assert topics.status_code == 200
    assert topics.json()["total"] == 2
    assert topics.json()["records"][0]["absolute_community"] == 2
    assert topics.json()["records"][0]["absolute_unigram_keywords"] == [
        "alpha",
        "beta",
    ]

    themes = client.get(
        "/api/v1/runs/run-03/themes?month=03&exact_theme=Policy&limit=1"
    )
    assert themes.status_code == 200
    body = themes.json()
    assert body["total"] == 2
    assert body["records"][0]["general_theme_names"] == ["Policy"]
    assert body["records"][0]["absolute_unigram_keywords"] == ["alpha", "beta"]
    assert body["provider_metadata"]["configured_primary_provider"] == "mock"

    no_theme = client.get("/api/v1/runs/run-03/themes?month=03&exact_theme=policy")
    assert no_theme.status_code == 200
    assert no_theme.json()["total"] == 0


def test_evolution_and_report_endpoints(tmp_path):
    _build_run(tmp_path)
    client = _client(tmp_path)

    transitions = client.get("/api/v1/runs/run-03/transitions")
    assert transitions.status_code == 200
    assert transitions.json()["records"][0]["jaccard_score"] == 0.6

    persistent = client.get("/api/v1/runs/run-03/persistent-communities")
    assert persistent.json()["total"] == 1
    membership = client.get("/api/v1/runs/run-03/membership-changes")
    assert membership.json()["records"][0] == {
        "start_month": "03",
        "end_month": "04",
        "start_community": "1",
        "end_community": "2",
        "retained_count": 1,
        "joined_count": 1,
        "exited_count": 1,
        "start_count": 2,
        "end_count": 2,
    }
    similarity = client.get("/api/v1/runs/run-03/theme-similarity")
    assert similarity.status_code == 200
    assert similarity.json()["artifacts"][0]["media_type"] == "image/png"

    report = client.get("/api/v1/runs/run-03/report")
    assert report.status_code == 200
    assert b"report" in report.content
    download = client.get("/api/v1/runs/run-03/downloads/network_data")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/vnd.apache.parquet")


def test_missing_optional_artifact_has_stable_error(tmp_path):
    _build_run(tmp_path, include_similarity=False)
    client = _client(tmp_path)

    partial = client.get("/api/v1/runs/run-03/topics?type=partial")
    assert partial.status_code == 404
    assert partial.json()["code"] == "ARTIFACT_NOT_AVAILABLE"
    similarity = client.get("/api/v1/runs/run-03/theme-similarity")
    assert similarity.status_code == 404
    assert similarity.json()["code"] == "ARTIFACT_NOT_AVAILABLE"


def test_invalid_manifest_and_symlink_escape_are_rejected(tmp_path):
    invalid_root = tmp_path / "runs" / "invalid"
    invalid_root.mkdir(parents=True)
    (invalid_root / "manifest.json").write_text("{broken", encoding="utf-8")
    client = _client(tmp_path)
    invalid = client.get("/api/v1/runs/invalid")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "INVALID_MANIFEST"

    root = _build_run(tmp_path, run_id="symlink")
    outside = tmp_path / "outside.html"
    outside.write_text("outside", encoding="utf-8")
    report = root / "reports/report.html"
    report.unlink()
    report.symlink_to(outside)
    payload = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    report_record = next(
        item for item in payload["artifacts"] if item["key"] == "report_html"
    )
    report_record["sha256"] = _hash(outside)
    report_record["byte_size"] = outside.stat().st_size
    (root / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    escaped = client.get("/api/v1/runs/symlink/report")
    assert escaped.status_code == 409
    assert escaped.json()["code"] == "ARTIFACT_PATH_VIOLATION"


def test_openapi_contract_and_invalid_filters(tmp_path):
    _build_run(tmp_path)
    client = _client(tmp_path)

    schema = client.get("/openapi.json").json()
    expected = {
        "/api/v1/runs",
        "/api/v1/runs/{run_id}",
        "/api/v1/runs/{run_id}/overview",
        "/api/v1/runs/{run_id}/network",
        "/api/v1/runs/{run_id}/communities",
        "/api/v1/runs/{run_id}/topics",
        "/api/v1/runs/{run_id}/themes",
        "/api/v1/runs/{run_id}/theme-trends/monthly",
        "/api/v1/runs/{run_id}/theme-trends/timeline",
        "/api/v1/runs/{run_id}/theme-clusters/monthly",
        "/api/v1/runs/{run_id}/theme-clusters/timeline",
        "/api/v1/runs/{run_id}/theme-clusters/evidence",
        "/api/v1/runs/{run_id}/transitions",
        "/api/v1/runs/{run_id}/evolution/paths",
        "/api/v1/runs/{run_id}/evolution/paths/{path_id}/mobility",
        "/api/v1/runs/{run_id}/evolution/paths/{path_id}/theme-similarity",
        "/api/v1/runs/{run_id}/report",
    }
    assert expected.issubset(schema["paths"])
    invalid = client.get("/api/v1/runs?month=13")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "INVALID_FILTER"


def test_api_requests_do_not_import_analytical_modules(tmp_path):
    for module_name in [
        "src.pipelines.social_network_pipeline",
        "src.pipelines.theme_pipeline",
        "src.topics.lda",
        "src.themes.theme_similarity",
        "src.themes.theme_clustering",
        "networkx",
    ]:
        sys.modules.pop(module_name, None)

    _build_run(tmp_path)
    client = _client(tmp_path)
    assert client.get("/api/v1/runs/run-03/overview").status_code == 200
    assert client.get("/api/v1/runs/run-03/network").status_code == 200

    assert "src.pipelines.social_network_pipeline" not in sys.modules
    assert "src.pipelines.theme_pipeline" not in sys.modules
    assert "src.topics.lda" not in sys.modules
    assert "src.themes.theme_similarity" not in sys.modules
    assert "src.themes.theme_clustering" not in sys.modules
    assert "networkx" not in sys.modules


def test_api_startup_does_not_import_heavy_data_libraries(tmp_path):
    """Verify that importing src.api.app, initializing app, and calling /health do not import pandas, pyarrow, or numpy."""
    _build_run(tmp_path)
    worker_code = (
        "import sys\n"
        "assert 'pandas' not in sys.modules\n"
        "assert 'pyarrow' not in sys.modules\n"
        "assert 'numpy' not in sys.modules\n"
        "from fastapi.testclient import TestClient\n"
        "from src.api.app import create_app\n"
        f"app = create_app(artifact_root='{tmp_path}')\n"
        "assert 'pandas' not in sys.modules\n"
        "assert 'pyarrow' not in sys.modules\n"
        "assert 'numpy' not in sys.modules\n"
        "client = TestClient(app)\n"
        "assert 'pandas' not in sys.modules\n"
        "assert 'pyarrow' not in sys.modules\n"
        "assert 'numpy' not in sys.modules\n"
        "resp_health = client.get('/api/v1/health')\n"
        "assert resp_health.status_code == 200\n"
        "assert resp_health.json()['status'] == 'ok'\n"
        "assert 'pandas' not in sys.modules\n"
        "assert 'pyarrow' not in sys.modules\n"
        "assert 'numpy' not in sys.modules\n"
        "resp_ready = client.get('/api/v1/ready')\n"
        "assert resp_ready.status_code == 200\n"
        "assert resp_ready.json()['status'] == 'ready'\n"
        "assert 'pandas' not in sys.modules\n"
        "assert 'pyarrow' not in sys.modules\n"
        "assert 'numpy' not in sys.modules\n"
        "resp_overview = client.get('/api/v1/runs/run-03/overview')\n"
        "assert resp_overview.status_code == 200\n"
        "assert 'pandas' in sys.modules\n"
        "assert 'pyarrow' in sys.modules\n"
        "assert 'numpy' in sys.modules\n"
        "print('STARTUP_AND_HEALTH_CLEAN')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", worker_code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Subprocess failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert "STARTUP_AND_HEALTH_CLEAN" in result.stdout


def test_api_startup_s3_backend_does_not_import_heavy_data_libraries():
    """Verify that importing src.api.app, initializing S3 app, and calling /health do not import pandas, pyarrow, or numpy."""
    worker_code = (
        "import sys\n"
        "assert 'pandas' not in sys.modules\n"
        "assert 'pyarrow' not in sys.modules\n"
        "assert 'numpy' not in sys.modules\n"
        "from fastapi.testclient import TestClient\n"
        "from src.api.app import create_app\n"
        "from src.api.storage import S3ArtifactStorage\n"
        "from src.api.storage.factory import create_artifact_storage\n"
        "direct_storage = create_artifact_storage(backend_type='s3', s3_bucket='test-direct-bucket', s3_region='us-east-1')\n"
        "assert isinstance(direct_storage, S3ArtifactStorage)\n"
        "assert 'pandas' not in sys.modules\n"
        "assert 'pyarrow' not in sys.modules\n"
        "assert 'numpy' not in sys.modules\n"
        "app = create_app()\n"
        "assert 'pandas' not in sys.modules\n"
        "assert 'pyarrow' not in sys.modules\n"
        "assert 'numpy' not in sys.modules\n"
        "client = TestClient(app)\n"
        "assert 'pandas' not in sys.modules\n"
        "assert 'pyarrow' not in sys.modules\n"
        "assert 'numpy' not in sys.modules\n"
        "resp_health = client.get('/api/v1/health')\n"
        "assert resp_health.status_code == 200\n"
        "assert resp_health.json()['status'] == 'ok'\n"
        "assert 'pandas' not in sys.modules\n"
        "assert 'pyarrow' not in sys.modules\n"
        "assert 'numpy' not in sys.modules\n"
        "print('S3_STARTUP_AND_HEALTH_CLEAN')\n"
    )
    env = dict(os.environ)
    env["AWS_EC2_METADATA_DISABLED"] = "true"
    env["COMMUNITY_ANALYSIS_STORAGE_BACKEND"] = "s3"
    env["COMMUNITY_ANALYSIS_S3_BUCKET"] = "test-startup-bucket"
    env["COMMUNITY_ANALYSIS_S3_REGION"] = "us-east-1"
    result = subprocess.run(
        [sys.executable, "-c", worker_code],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, f"Subprocess failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert "S3_STARTUP_AND_HEALTH_CLEAN" in result.stdout


def test_api_parquet_endpoints_work_with_lazy_imports(tmp_path):
    """Verify that endpoints requiring Parquet data load and return valid payloads with lazy imports."""
    _build_run(tmp_path)
    client = _client(tmp_path)

    # Health and readiness endpoints succeed without requiring analytical or heavy processing
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    ready_resp = client.get("/api/v1/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"

    # Parquet-backed data endpoints resolve correctly with lazy loading
    overview_resp = client.get("/api/v1/runs/run-03/overview")
    assert overview_resp.status_code == 200
    overview_data = overview_resp.json()
    assert overview_data["run_id"] == "run-03"
    assert overview_data["total_users"] == 5

    network_resp = client.get("/api/v1/runs/run-03/network")
    assert network_resp.status_code == 200
    network_data = network_resp.json()
    assert network_data["view"] == "users"
    assert len(network_data["nodes"]) > 0

    topics_resp = client.get("/api/v1/runs/run-03/topics?topic_type=matched")
    assert topics_resp.status_code == 200
    topics_data = topics_resp.json()
    assert topics_data["topic_type"] == "matched"
    assert len(topics_data["records"]) > 0

    themes_resp = client.get("/api/v1/runs/run-03/themes")
    assert themes_resp.status_code == 200
    themes_data = themes_resp.json()
    assert len(themes_data["records"]) > 0
