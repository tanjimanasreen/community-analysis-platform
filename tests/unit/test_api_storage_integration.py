from __future__ import annotations

import json
import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import pandas as pd
import pyarrow.fs as pafs

from src.api.app import create_app
from src.api.dependencies import ApiSettings
from src.api.storage.s3 import S3ArtifactStorage


def _setup_full_s3_run(root_dir: Path, run_id: str = "2017-03_twitter_reply") -> None:
    run_dir = root_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Network data
    net_dir = run_dir / "data" / "network"
    net_dir.mkdir(parents=True, exist_ok=True)
    net_df = pd.DataFrame(
        {
            "unique_id": ["m1", "m2"],
            "from_id": ["user_1", "user_2"],
            "forwarder_id": ["user_2", "user_3"],
            "text": ["hello", "world"],
            "created_at": ["2017-03-01", "2017-03-02"],
        }
    )
    net_path = net_dir / "network_data.parquet"
    net_df.to_parquet(net_path, index=False)

    # 2. Communities
    comm_dir = run_dir / "data" / "communities" / "absolute"
    comm_dir.mkdir(parents=True, exist_ok=True)
    comm_df = pd.DataFrame(
        {
            "source": ["u1", "u2"],
            "target": ["u2", "u3"],
            "community_number": [1, 2],
            "direction": ["out", "out"],
            "weight": [9.0, 8.0],
        }
    )
    comm_path = comm_dir / "communities_absolute.parquet"
    comm_df.to_parquet(comm_path, index=False)

    # 3. Community summary
    comm_sum_dir = run_dir / "data" / "communities" / "summary" / "absolute"
    comm_sum_dir.mkdir(parents=True, exist_ok=True)
    comm_sum_df = pd.DataFrame(
        {
            "community_id": [1, 2],
            "node_count": [10, 20],
            "edge_count": [15, 30],
            "total_weight": [25.0, 50.0],
        }
    )
    comm_sum_path = comm_sum_dir / "community_summary_absolute.parquet"
    comm_sum_df.to_parquet(comm_sum_path, index=False)

    # 4. Topics
    topic_dir = run_dir / "data" / "topics" / "matched"
    topic_dir.mkdir(parents=True, exist_ok=True)
    topic_df = pd.DataFrame(
        {
            "absolute_community": [1, 2],
            "weighted_community": [1, 2],
            "absolute_unigram_topic": ["topic-1", "topic-2"],
            "absolute_unigram_keywords": ["['tax', 'economy']", "['vote', 'election']"],
            "weighted_unigram_topic": ["topic-1", "topic-2"],
            "weighted_unigram_keywords": ["['tax']", "['vote']"],
            "absolute_bigram_topic": ["topic-b1", "topic-b2"],
            "absolute_bigram_keywords": ["['tax cut']", "['vote now']"],
            "weighted_bigram_topic": ["topic-b1", "topic-b2"],
            "weighted_bigram_keywords": ["['tax cut']", "['vote now']"],
            "members": ["['u1', 'u2']", "['u3', 'u4']"],
        }
    )
    topic_path = topic_dir / "topics.parquet"
    topic_df.to_parquet(topic_path, index=False)

    # 5. Report HTML
    report_dir = run_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.html"
    report_html = "<html><body><h1>Community Analysis Report</h1></body></html>"
    report_path.write_text(report_html, encoding="utf-8")

    def _file_info(p: Path) -> tuple[str, int]:
        data = p.read_bytes()
        return hashlib.sha256(data).hexdigest(), len(data)

    net_sha, net_bytes = _file_info(net_path)
    comm_sha, comm_bytes = _file_info(comm_path)
    comm_sum_sha, comm_sum_bytes = _file_info(comm_sum_path)
    topic_sha, topic_bytes = _file_info(topic_path)
    report_sha, report_bytes = _file_info(report_path)

    manifest_data = {
        "run_id": run_id,
        "schema_version": "1.0",
        "status": "completed",
        "created_at": "2026-08-28T00:00:00Z",
        "dataset": {
            "platform": "twitter",
            "content_type": "reply",
            "date_start": "2017-03-01",
            "date_end": "2017-03-31",
        },
        "pipeline": {
            "started_at": "2026-08-28T00:00:00Z",
            "completed_at": "2026-08-28T00:10:00Z",
        },
        "code": {},
        "artifacts": [
            {
                "key": "network_data",
                "path": "data/network/network_data.parquet",
                "category": "data",
                "media_type": "application/vnd.apache.parquet",
                "schema_version": "1.0",
                "sha256": net_sha,
                "byte_size": net_bytes,
                "rows": 2,
                "stage": "network_construction",
            },
            {
                "key": "communities_absolute",
                "path": "data/communities/absolute/communities_absolute.parquet",
                "category": "data",
                "media_type": "application/vnd.apache.parquet",
                "schema_version": "1.0",
                "sha256": comm_sha,
                "byte_size": comm_bytes,
                "rows": 2,
                "stage": "community_detection",
            },
            {
                "key": "community_summary_absolute",
                "path": "data/communities/summary/absolute/community_summary_absolute.parquet",
                "category": "data",
                "media_type": "application/vnd.apache.parquet",
                "schema_version": "1.0",
                "sha256": comm_sum_sha,
                "byte_size": comm_sum_bytes,
                "rows": 2,
                "stage": "community_detection",
            },
            {
                "key": "matched_communities_topics",
                "path": "data/topics/matched/topics.parquet",
                "category": "data",
                "media_type": "application/vnd.apache.parquet",
                "schema_version": "1.0",
                "sha256": topic_sha,
                "byte_size": topic_bytes,
                "rows": 2,
                "stage": "topic_modeling",
            },
            {
                "key": "report_html",
                "path": "reports/report.html",
                "category": "report",
                "media_type": "text/html",
                "schema_version": "1.0",
                "sha256": report_sha,
                "byte_size": report_bytes,
                "rows": None,
                "stage": "reporting",
            },
        ],
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
    (run_dir / "resolved_config.yaml").write_text(
        "platform: twitter\n", encoding="utf-8"
    )
    inputs_dir = run_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    (inputs_dir / "datasets.json").write_text(
        json.dumps({"datasets": [{"source_name": "twitter_201703.csv"}]}),
        encoding="utf-8",
    )


def _s3_client(tmp_path: Path, prefix: str = "") -> TestClient:
    fs = pafs.LocalFileSystem()
    sub_fs = pafs.SubTreeFileSystem(str(tmp_path), fs)
    storage = S3ArtifactStorage(
        bucket="community-analysis-dev-data",
        prefix=prefix,
        filesystem=sub_fs,
    )
    settings = ApiSettings(
        artifact_root=f"s3://community-analysis-dev-data/{prefix}".rstrip("/"),
        storage_backend="s3",
        s3_bucket="community-analysis-dev-data",
        s3_prefix=prefix,
        storage=storage,
    )
    app = create_app(settings=settings)
    return TestClient(app)


def test_api_health_and_readiness_on_s3(tmp_path: Path) -> None:
    client = _s3_client(tmp_path)

    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"
    assert health_res.json()["read_only"] is True

    ready_res = client.get("/api/v1/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"


def test_api_endpoints_backed_by_s3(tmp_path: Path) -> None:
    _setup_full_s3_run(tmp_path, "2017-03_twitter_reply")
    client = _s3_client(tmp_path)

    # 1. List runs
    runs_res = client.get("/api/v1/runs")
    assert runs_res.status_code == 200
    runs_payload = runs_res.json()
    assert runs_payload["total"] == 1
    assert runs_payload["runs"][0]["run_id"] == "2017-03_twitter_reply"

    # 2. Get run detail
    run_res = client.get("/api/v1/runs/2017-03_twitter_reply")
    assert run_res.status_code == 200
    assert run_res.json()["run_id"] == "2017-03_twitter_reply"

    # 3. Overview
    overview_res = client.get("/api/v1/runs/2017-03_twitter_reply/overview")
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert overview["run_id"] == "2017-03_twitter_reply"
    assert overview["platform"] == "twitter"

    # 4. Communities
    comm_res = client.get("/api/v1/runs/2017-03_twitter_reply/communities?metric=if")
    assert comm_res.status_code == 200

    # 5. Topics
    topics_res = client.get("/api/v1/runs/2017-03_twitter_reply/topics")
    assert topics_res.status_code == 200
    topics = topics_res.json()
    assert topics["total"] == 2
    assert len(topics["records"]) == 2

    # 6. Stream HTML Report with StreamingResponse headers
    report_res = client.get("/api/v1/runs/2017-03_twitter_reply/report")
    assert report_res.status_code == 200
    assert "text/html" in report_res.headers["content-type"]
    assert "inline" in report_res.headers["content-disposition"]
    assert "Community Analysis Report" in report_res.text

    # 7. Download Artifact with StreamingResponse headers
    dl_res = client.get("/api/v1/runs/2017-03_twitter_reply/downloads/network_data")
    assert dl_res.status_code == 200
    assert "attachment" in dl_res.headers["content-disposition"]
    assert len(dl_res.content) > 0

    # 8. Verification endpoint on S3 (quick and deep)
    verify_quick = client.get("/api/v1/runs/2017-03_twitter_reply/verification")
    assert verify_quick.status_code == 200
    assert verify_quick.json()["ok"] is True
    assert verify_quick.json()["status"] == "completed"

    verify_deep = client.get(
        "/api/v1/runs/2017-03_twitter_reply/verification?deep=true"
    )
    assert verify_deep.status_code == 200
    assert verify_deep.json()["ok"] is True
    assert verify_deep.json()["checked_artifacts"] == 5

    # 9. Missing run returns 404
    missing_res = client.get("/api/v1/runs/nonexistent")
    assert missing_res.status_code == 404


def test_api_verification_corruption_on_s3(tmp_path: Path) -> None:
    _setup_full_s3_run(tmp_path, "corrupted_run")
    client = _s3_client(tmp_path)

    # 1. Corrupt checksum in manifest
    manifest_file = tmp_path / "runs" / "corrupted_run" / "manifest.json"
    payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    payload["artifacts"][0]["sha256"] = "f" * 64
    manifest_file.write_text(json.dumps(payload), encoding="utf-8")

    # Fast verify ok
    res_quick = client.get("/api/v1/runs/corrupted_run/verification")
    assert res_quick.status_code == 200
    assert res_quick.json()["ok"] is True

    # Deep verify fails with ARTIFACT_CHECKSUM_MISMATCH
    res_deep = client.get("/api/v1/runs/corrupted_run/verification?deep=true")
    assert res_deep.status_code == 200
    assert res_deep.json()["ok"] is False
    assert res_deep.json()["error_code"] == "ARTIFACT_CHECKSUM_MISMATCH"
