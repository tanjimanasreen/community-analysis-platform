"""Unit tests for scripts/aws_run_evolution.py operational evolution runner."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock

import pytest

from scripts.aws_run_evolution import (
    APPROVED_CANONICAL_CONFIGS,
    discover_run_id_from_batch_job,
    extract_run_id_from_log_events,
    get_batch_job_log_stream_name,
    resolve_job_definition_identifier,
    resolve_latest_active_job_definition,
    submit_evolution_batch_job,
    validate_canonical_config,
    validate_environment,
    verify_completed_manifest,
    wait_for_batch_job,
)


def test_validate_environment() -> None:
    validate_environment("dev")
    with pytest.raises(ValueError, match="is forbidden"):
        validate_environment("prod")


def test_validate_canonical_config() -> None:
    for cfg in APPROVED_CANONICAL_CONFIGS:
        assert validate_canonical_config(cfg) == cfg

    with pytest.raises(ValueError, match="not an approved canonical evolution config"):
        validate_canonical_config("configs/arbitrary.yml")
    with pytest.raises(ValueError, match="not an approved canonical evolution config"):
        validate_canonical_config("/etc/passwd")


def test_resolve_latest_active_job_definition_single_active() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_job_definitions.return_value = {
        "jobDefinitions": [
            {
                "jobDefinitionName": "community-analysis-dev-analytics-tei-job",
                "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:1",
                "revision": 1,
                "status": "ACTIVE",
            }
        ]
    }
    arn = resolve_latest_active_job_definition(batch_mock, "community-analysis-dev-analytics-tei-job")
    assert arn == "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:1"
    batch_mock.describe_job_definitions.assert_called_once_with(
        jobDefinitionName="community-analysis-dev-analytics-tei-job",
        status="ACTIVE",
    )


def test_resolve_latest_active_job_definition_multiple_active_highest_selected() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_job_definitions.return_value = {
        "jobDefinitions": [
            {
                "jobDefinitionName": "community-analysis-dev-analytics-tei-job",
                "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:1",
                "revision": 1,
                "status": "ACTIVE",
            },
            {
                "jobDefinitionName": "community-analysis-dev-analytics-tei-job",
                "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:3",
                "revision": 3,
                "status": "ACTIVE",
            },
            {
                "jobDefinitionName": "community-analysis-dev-analytics-tei-job",
                "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:2",
                "revision": 2,
                "status": "ACTIVE",
            },
        ]
    }
    arn = resolve_latest_active_job_definition(batch_mock, "community-analysis-dev-analytics-tei-job")
    assert arn == "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:3"


def test_resolve_latest_active_job_definition_pagination() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_job_definitions.side_effect = [
        {
            "jobDefinitions": [
                {
                    "jobDefinitionName": "community-analysis-dev-analytics-tei-job",
                    "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:1",
                    "revision": 1,
                    "status": "ACTIVE",
                }
            ],
            "nextToken": "token-page-2",
        },
        {
            "jobDefinitions": [
                {
                    "jobDefinitionName": "community-analysis-dev-analytics-tei-job",
                    "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:4",
                    "revision": 4,
                    "status": "ACTIVE",
                }
            ],
        },
    ]
    arn = resolve_latest_active_job_definition(batch_mock, "community-analysis-dev-analytics-tei-job")
    assert arn == "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:4"
    assert batch_mock.describe_job_definitions.call_count == 2
    second_call_kwargs = batch_mock.describe_job_definitions.call_args_list[1][1]
    assert second_call_kwargs.get("nextToken") == "token-page-2"


def test_resolve_latest_active_job_definition_filters_by_name_and_active() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_job_definitions.return_value = {
        "jobDefinitions": [
            {
                "jobDefinitionName": "different-job",
                "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/different-job:99",
                "revision": 99,
                "status": "ACTIVE",
            },
            {
                "jobDefinitionName": "community-analysis-dev-analytics-tei-job",
                "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:5",
                "revision": 5,
                "status": "INACTIVE",
            },
            {
                "jobDefinitionName": "community-analysis-dev-analytics-tei-job",
                "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:2",
                "revision": 2,
                "status": "ACTIVE",
            },
        ]
    }
    arn = resolve_latest_active_job_definition(batch_mock, "community-analysis-dev-analytics-tei-job")
    assert arn == "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:2"


def test_resolve_latest_active_job_definition_fail_closed() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_job_definitions.return_value = {"jobDefinitions": []}
    with pytest.raises(RuntimeError, match="No ACTIVE AWS Batch job definition found for 'missing-job'"):
        resolve_latest_active_job_definition(batch_mock, "missing-job")


def test_submit_evolution_batch_job() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_job_definitions.return_value = {
        "jobDefinitions": [
            {
                "jobDefinitionName": "community-analysis-dev-analytics-tei-job",
                "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:3",
                "revision": 3,
                "status": "ACTIVE",
            }
        ]
    }
    batch_mock.submit_job.return_value = {"jobId": "job-12345"}

    job_name, job_id = submit_evolution_batch_job(
        batch_mock,
        environment="dev",
        config_path="configs/telegram/forwarded_message_evolution.yml",
    )
    assert job_id == "job-12345"
    assert job_name.startswith("community-analysis-dev-")
    batch_mock.submit_job.assert_called_once()
    kwargs = batch_mock.submit_job.call_args[1]
    assert kwargs["jobQueue"] == "community-analysis-dev-queue"
    assert (
        kwargs["jobDefinition"]
        == "arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:3"
    )
    env_vars = kwargs["containerOverrides"]["environment"]
    env_map = {e["name"]: e["value"] for e in env_vars}
    assert env_map["CONFIG_PATH"] == "configs/telegram/forwarded_message_evolution.yml"
    assert env_map["PIPELINE_COMMAND"] == "run-evolution-pipeline"


def test_submit_evolution_batch_job_override_revisioned_arn() -> None:
    batch_mock = MagicMock()
    batch_mock.submit_job.return_value = {"jobId": "job-rev-arn"}

    job_name, job_id = submit_evolution_batch_job(
        batch_mock,
        environment="dev",
        config_path="configs/telegram/forwarded_message_evolution.yml",
        job_definition="arn:aws:batch:us-east-1:123456789012:job-definition/custom-job:2",
    )
    assert job_id == "job-rev-arn"
    batch_mock.submit_job.assert_called_once()
    assert (
        batch_mock.submit_job.call_args[1]["jobDefinition"]
        == "arn:aws:batch:us-east-1:123456789012:job-definition/custom-job:2"
    )
    batch_mock.describe_job_definitions.assert_not_called()


def test_submit_evolution_batch_job_override_revisioned_short_name() -> None:
    batch_mock = MagicMock()
    batch_mock.submit_job.return_value = {"jobId": "job-rev-short"}

    job_name, job_id = submit_evolution_batch_job(
        batch_mock,
        environment="dev",
        config_path="configs/telegram/forwarded_message_evolution.yml",
        job_definition="custom-job:7",
    )
    assert job_id == "job-rev-short"
    batch_mock.submit_job.assert_called_once()
    assert batch_mock.submit_job.call_args[1]["jobDefinition"] == "custom-job:7"
    batch_mock.describe_job_definitions.assert_not_called()


def test_submit_evolution_batch_job_override_unrevisioned_short_name() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_job_definitions.return_value = {
        "jobDefinitions": [
            {
                "jobDefinitionName": "custom-job",
                "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/custom-job:5",
                "revision": 5,
                "status": "ACTIVE",
            }
        ]
    }
    batch_mock.submit_job.return_value = {"jobId": "job-unrev-short"}

    job_name, job_id = submit_evolution_batch_job(
        batch_mock,
        environment="dev",
        config_path="configs/telegram/forwarded_message_evolution.yml",
        job_definition="custom-job",
    )
    assert job_id == "job-unrev-short"
    batch_mock.describe_job_definitions.assert_called_once_with(
        jobDefinitionName="custom-job",
        status="ACTIVE",
    )
    batch_mock.submit_job.assert_called_once()
    assert (
        batch_mock.submit_job.call_args[1]["jobDefinition"]
        == "arn:aws:batch:us-east-1:123456789012:job-definition/custom-job:5"
    )


def test_submit_evolution_batch_job_override_unrevisioned_arn() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_job_definitions.return_value = {
        "jobDefinitions": [
            {
                "jobDefinitionName": "custom-job",
                "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/custom-job:8",
                "revision": 8,
                "status": "ACTIVE",
            }
        ]
    }
    batch_mock.submit_job.return_value = {"jobId": "job-unrev-arn"}

    job_name, job_id = submit_evolution_batch_job(
        batch_mock,
        environment="dev",
        config_path="configs/telegram/forwarded_message_evolution.yml",
        job_definition="arn:aws:batch:us-east-1:123456789012:job-definition/custom-job",
    )
    assert job_id == "job-unrev-arn"
    batch_mock.describe_job_definitions.assert_called_once_with(
        jobDefinitionName="custom-job",
        status="ACTIVE",
    )
    batch_mock.submit_job.assert_called_once()
    assert (
        batch_mock.submit_job.call_args[1]["jobDefinition"]
        == "arn:aws:batch:us-east-1:123456789012:job-definition/custom-job:8"
    )


def test_submit_evolution_batch_job_override_unrevisioned_arn_scope_mismatch_fails_closed() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_job_definitions.return_value = {
        "jobDefinitions": [
            {
                "jobDefinitionName": "custom-job",
                "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/custom-job:8",
                "revision": 8,
                "status": "ACTIVE",
            }
        ]
    }

    with pytest.raises(ValueError, match="does not match supplied ARN scope"):
        submit_evolution_batch_job(
            batch_mock,
            environment="dev",
            config_path="configs/telegram/forwarded_message_evolution.yml",
            job_definition="arn:aws:batch:us-west-2:999999999999:job-definition/custom-job",
        )

    batch_mock.describe_job_definitions.assert_called_once_with(
        jobDefinitionName="custom-job",
        status="ACTIVE",
    )
    batch_mock.submit_job.assert_not_called()


def test_submit_evolution_batch_job_override_malformed_fails_closed() -> None:
    batch_mock = MagicMock()

    with pytest.raises(ValueError, match="Malformed or invalid AWS Batch job definition ARN"):
        submit_evolution_batch_job(
            batch_mock,
            environment="dev",
            config_path="configs/telegram/forwarded_message_evolution.yml",
            job_definition="arn:aws:batch:us-east-1:123456789012:job-definition/",
        )

    with pytest.raises(ValueError, match="Malformed or invalid AWS Batch job definition ARN"):
        submit_evolution_batch_job(
            batch_mock,
            environment="dev",
            config_path="configs/telegram/forwarded_message_evolution.yml",
            job_definition="arn:invalid",
        )

    with pytest.raises(ValueError, match="Malformed or invalid AWS Batch job definition identifier"):
        submit_evolution_batch_job(
            batch_mock,
            environment="dev",
            config_path="configs/telegram/forwarded_message_evolution.yml",
            job_definition="custom-job:abc",
        )

    with pytest.raises(ValueError, match="Job definition override cannot be empty"):
        submit_evolution_batch_job(
            batch_mock,
            environment="dev",
            config_path="configs/telegram/forwarded_message_evolution.yml",
            job_definition="   ",
        )


def test_wait_for_batch_job_success() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_jobs.side_effect = [
        {"jobs": [{"status": "RUNNING"}]},
        {"jobs": [{"status": "SUCCEEDED"}]},
    ]
    status = wait_for_batch_job(batch_mock, "job-12345", poll_interval_seconds=0.01)
    assert status == "SUCCEEDED"


def test_wait_for_batch_job_failure() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_jobs.return_value = {
        "jobs": [{"status": "FAILED", "statusReason": "OutOfMemory"}]
    }
    with pytest.raises(RuntimeError, match="Batch job job-12345 failed: OutOfMemory"):
        wait_for_batch_job(batch_mock, "job-12345", poll_interval_seconds=0.01)


def test_get_batch_job_log_stream_name() -> None:
    # 1. Multi-container ecsProperties
    multi_job = {
        "ecsProperties": {
            "taskProperties": [
                {
                    "containers": [
                        {"name": "tei-similarity", "logStreamName": "tei-sim-stream"},
                        {"name": "analytics", "logStreamName": "analytics-stream-1"},
                    ]
                }
            ]
        }
    }
    assert get_batch_job_log_stream_name(multi_job, "analytics") == "analytics-stream-1"
    assert get_batch_job_log_stream_name(multi_job, "non-existent") is None

    # 2. Top-level containers list
    top_containers_job = {
        "containers": [
            {"name": "analytics", "logStreamName": "analytics-stream-2"}
        ]
    }
    assert get_batch_job_log_stream_name(top_containers_job, "analytics") == "analytics-stream-2"

    # 3. Single-container top-level
    single_job = {"container": {"logStreamName": "single-stream-3"}}
    assert get_batch_job_log_stream_name(single_job, "analytics") == "single-stream-3"


def test_extract_run_id_from_log_events() -> None:
    # 1. Text format standard completion event
    events1 = [
        {"message": "2026-09-01 12:00:00 INFO starting pipeline"},
        {"message": "batch_job_completed_successfully run_id=run-20260901-test total_duration_seconds=42.1"},
    ]
    assert extract_run_id_from_log_events(events1) == "run-20260901-test"

    # 2. JSON formatted event
    events2 = [
        {"message": '{"level": "INFO", "logger": "src.cloud.batch_runner", "run_id": "run-json-12345"}'}
    ]
    assert extract_run_id_from_log_events(events2) == "run-json-12345"

    # 3. Manifest verified event
    events3 = [
        {"message": "run_manifest_verified run_id=run-manifest-999 artifact_count=12"}
    ]
    assert extract_run_id_from_log_events(events3) == "run-manifest-999"

    # 4. Fail closed on empty / missing run_id
    with pytest.raises(RuntimeError, match="Could not extract analytical run_id"):
        extract_run_id_from_log_events([{"message": "Unrelated log line without run id"}])

    # 5. Fail closed on conflicting run_ids
    conflicting_events = [
        {"message": "batch_job_completed_successfully run_id=run-aaa total_duration_seconds=10"},
        {"message": "batch_job_completed_successfully run_id=run-bbb total_duration_seconds=20"},
    ]
    with pytest.raises(RuntimeError, match="Conflicting run_ids discovered"):
        extract_run_id_from_log_events(conflicting_events)


def test_discover_run_id_from_batch_job() -> None:
    batch_mock = MagicMock()
    batch_mock.describe_jobs.return_value = {
        "jobs": [
            {
                "jobId": "job-123",
                "container": {"logStreamName": "analytics/job-123/stream"},
            }
        ]
    }
    logs_mock = MagicMock()
    logs_mock.get_log_events.return_value = {
        "events": [
            {"message": "batch_job_completed_successfully run_id=run-exact-corr-001 total_duration_seconds=15"}
        ],
        "nextForwardToken": None,
    }

    run_id = discover_run_id_from_batch_job(
        batch_mock,
        logs_mock,
        job_id="job-123",
        log_group_name="/aws/batch/job/community-analysis-dev",
    )
    assert run_id == "run-exact-corr-001"
    batch_mock.describe_jobs.assert_called_once_with(jobs=["job-123"])
    logs_mock.get_log_events.assert_called_once_with(
        logGroupName="/aws/batch/job/community-analysis-dev",
        logStreamName="analytics/job-123/stream",
        startFromHead=True,
    )


def test_verify_completed_manifest_with_all_artifacts() -> None:
    s3_mock = MagicMock()
    manifest_data = {
        "run_id": "test-run-001",
        "status": "completed",
        "artifacts": [
            {"key": "network_graph", "path": "twitter/network/march.parquet", "byte_size": 1024},
            {"key": "topic_scores", "path": "twitter/LDA/scores.parquet", "byte_size": 2048},
        ],
    }
    s3_mock.get_object.return_value = {
        "Body": io.BytesIO(json.dumps(manifest_data).encode("utf-8"))
    }

    def fake_head(Bucket: str, Key: str):
        if Key == "runs/test-run-001/twitter/network/march.parquet":
            return {"ContentLength": 1024}
        elif Key == "runs/test-run-001/twitter/LDA/scores.parquet":
            return {"ContentLength": 2048}
        raise FileNotFoundError(Key)

    s3_mock.head_object.side_effect = fake_head

    manifest = verify_completed_manifest(s3_mock, "test-bucket", "test-run-001")
    assert manifest["status"] == "completed"
    assert len(manifest["artifacts"]) == 2
    assert s3_mock.head_object.call_count == 2


def test_verify_completed_manifest_missing_artifact_raises() -> None:
    s3_mock = MagicMock()
    manifest_data = {
        "run_id": "test-run-001",
        "status": "completed",
        "artifacts": [
            {"key": "network_graph", "path": "twitter/network/march.parquet"},
            {"key": "missing_artifact", "path": "twitter/missing.parquet"},
        ],
    }
    s3_mock.get_object.return_value = {
        "Body": io.BytesIO(json.dumps(manifest_data).encode("utf-8"))
    }
    s3_mock.head_object.side_effect = [
        {"ContentLength": 1024},
        RuntimeError("NoSuchKey 404"),
    ]

    with pytest.raises(FileNotFoundError, match="Canonical artifact from manifest not found in S3"):
        verify_completed_manifest(s3_mock, "test-bucket", "test-run-001")


def test_verify_completed_manifest_size_mismatch_raises() -> None:
    s3_mock = MagicMock()
    manifest_data = {
        "run_id": "test-run-001",
        "status": "completed",
        "artifacts": [
            {"key": "network_graph", "path": "twitter/network/march.parquet", "byte_size": 5000},
        ],
    }
    s3_mock.get_object.return_value = {
        "Body": io.BytesIO(json.dumps(manifest_data).encode("utf-8"))
    }
    s3_mock.head_object.return_value = {"ContentLength": 1200}  # mismatch

    with pytest.raises(ValueError, match="Size mismatch for canonical artifact"):
        verify_completed_manifest(s3_mock, "test-bucket", "test-run-001")
