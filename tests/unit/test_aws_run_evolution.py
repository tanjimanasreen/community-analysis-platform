"""Unit tests for scripts/aws_run_evolution.py operational evolution runner."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.aws_run_evolution import (
    APPROVED_CANONICAL_CONFIGS,
    APPROVED_THEME_MODES,
    DEFAULT_MAX_LOG_PAGES,
    build_analytics_ecs_properties_override,
    discover_run_id_from_batch_job,
    extract_run_id_from_log_events,
    get_batch_job_log_stream_name,
    resolve_job_definition_identifier,
    resolve_latest_active_job_definition,
    submit_evolution_batch_job,
    validate_canonical_config,
    validate_environment,
    validate_theme_mode,
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


def test_validate_theme_mode() -> None:
    assert APPROVED_THEME_MODES == {"canonical", "mock"}
    assert validate_theme_mode("canonical") == "canonical"
    assert validate_theme_mode("mock") == "mock"
    assert validate_theme_mode(" CANONICAL ") == "canonical"
    assert validate_theme_mode("Mock") == "mock"

    with pytest.raises(ValueError, match="is invalid"):
        validate_theme_mode("openai")
    with pytest.raises(ValueError, match="is invalid"):
        validate_theme_mode("gpt-5-nano")
    with pytest.raises(ValueError, match="is invalid"):
        validate_theme_mode("custom")
    with pytest.raises(ValueError, match="is invalid"):
        validate_theme_mode("")


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


def test_build_analytics_ecs_properties_override() -> None:
    env = [
        {"name": "CONFIG_PATH", "value": "test.yml"},
        {"name": "PIPELINE_COMMAND", "value": "run-evolution-pipeline"},
    ]
    override = build_analytics_ecs_properties_override(env)
    assert override == {
        "taskProperties": [
            {
                "containers": [
                    {
                        "name": "analytics",
                        "environment": env,
                    }
                ]
            }
        ]
    }
    assert override["taskProperties"][0]["containers"][0]["name"] == "analytics"


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
    assert "containerOverrides" not in kwargs, "TEI multi-container submission must not use containerOverrides"
    assert "ecsPropertiesOverride" in kwargs, "TEI multi-container submission must use ecsPropertiesOverride"
    ecs_override = kwargs["ecsPropertiesOverride"]
    assert "taskProperties" in ecs_override
    assert len(ecs_override["taskProperties"]) == 1
    containers = ecs_override["taskProperties"][0]["containers"]
    assert len(containers) == 1
    assert containers[0]["name"] == "analytics"
    env_vars = containers[0]["environment"]
    env_map = {e["name"]: e["value"] for e in env_vars}
    assert env_map["CONFIG_PATH"] == "configs/telegram/forwarded_message_evolution.yml"
    assert env_map["PIPELINE_COMMAND"] == "run-evolution-pipeline"
    assert "SKIP_S3_DOWNLOAD" not in env_map
    assert "THEME_PROVIDER" not in env_map
    assert "THEME_SIMILARITY_PROVIDER" not in env_map
    assert "THEME_CLUSTERING_PROVIDER" not in env_map


def test_submit_evolution_batch_job_canonical_mode_explicit() -> None:
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
    batch_mock.submit_job.return_value = {"jobId": "job-canonical"}

    job_name, job_id = submit_evolution_batch_job(
        batch_mock,
        environment="dev",
        config_path="configs/telegram/forwarded_message_evolution.yml",
        theme_mode="canonical",
    )
    assert job_id == "job-canonical"
    assert job_name.startswith("community-analysis-dev-")
    batch_mock.submit_job.assert_called_once()
    kwargs = batch_mock.submit_job.call_args[1]
    assert "containerOverrides" not in kwargs, "TEI multi-container submission must not use containerOverrides"
    assert "ecsPropertiesOverride" in kwargs, "TEI multi-container submission must use ecsPropertiesOverride"
    ecs_override = kwargs["ecsPropertiesOverride"]
    containers = ecs_override["taskProperties"][0]["containers"]
    assert len(containers) == 1
    assert containers[0]["name"] == "analytics"
    env_vars = containers[0]["environment"]
    env_map = {e["name"]: e["value"] for e in env_vars}
    assert env_map["CONFIG_PATH"] == "configs/telegram/forwarded_message_evolution.yml"
    assert env_map["PIPELINE_COMMAND"] == "run-evolution-pipeline"
    assert "THEME_PROVIDER" not in env_map
    assert "SKIP_S3_DOWNLOAD" not in env_map
    assert "THEME_SIMILARITY_PROVIDER" not in env_map
    assert "THEME_CLUSTERING_PROVIDER" not in env_map


def test_submit_evolution_batch_job_mock_mode() -> None:
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
    batch_mock.submit_job.return_value = {"jobId": "job-mock"}

    job_name, job_id = submit_evolution_batch_job(
        batch_mock,
        environment="dev",
        config_path="configs/twitter/reply_evolution.yml",
        theme_mode="mock",
    )
    assert job_id == "job-mock"
    assert job_name.startswith("community-analysis-dev-")
    batch_mock.submit_job.assert_called_once()
    kwargs = batch_mock.submit_job.call_args[1]
    assert "containerOverrides" not in kwargs, "TEI multi-container submission must not use containerOverrides"
    assert "ecsPropertiesOverride" in kwargs, "TEI multi-container submission must use ecsPropertiesOverride"
    ecs_override = kwargs["ecsPropertiesOverride"]
    containers = ecs_override["taskProperties"][0]["containers"]
    assert len(containers) == 1
    assert containers[0]["name"] == "analytics"
    env_vars = containers[0]["environment"]
    env_map = {e["name"]: e["value"] for e in env_vars}
    assert env_map["CONFIG_PATH"] == "configs/twitter/reply_evolution.yml"
    assert env_map["PIPELINE_COMMAND"] == "run-evolution-pipeline"
    assert env_map["THEME_PROVIDER"] == "mock"
    assert "SKIP_S3_DOWNLOAD" not in env_map
    assert "THEME_SIMILARITY_PROVIDER" not in env_map
    assert "THEME_CLUSTERING_PROVIDER" not in env_map


def test_submit_evolution_batch_job_invalid_theme_mode_fails_closed() -> None:
    batch_mock = MagicMock()
    with pytest.raises(ValueError, match="is invalid"):
        submit_evolution_batch_job(
            batch_mock,
            environment="dev",
            config_path="configs/telegram/forwarded_message_evolution.yml",
            theme_mode="openai",
        )
    batch_mock.submit_job.assert_not_called()

    with pytest.raises(ValueError, match="is invalid"):
        submit_evolution_batch_job(
            batch_mock,
            environment="dev",
            config_path="configs/telegram/forwarded_message_evolution.yml",
            theme_mode="arbitrary-model",
        )
    batch_mock.submit_job.assert_not_called()


def test_main_cli_theme_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.aws_run_evolution import main

    boto_mock = MagicMock()
    boto_mock.get_caller_identity.return_value = {"Account": "123456789012"}
    monkeypatch.setattr("boto3.client", MagicMock(return_value=boto_mock))

    submit_mock = MagicMock(return_value=("community-analysis-dev-test", "job-123"))
    wait_mock = MagicMock(return_value="SUCCEEDED")
    discover_mock = MagicMock(return_value="run-20260906-test")
    verify_mock = MagicMock(return_value={"status": "completed", "artifacts": [{"path": "a.parquet"}]})

    monkeypatch.setattr("scripts.aws_run_evolution.submit_evolution_batch_job", submit_mock)
    monkeypatch.setattr("scripts.aws_run_evolution.wait_for_batch_job", wait_mock)
    monkeypatch.setattr("scripts.aws_run_evolution.discover_run_id_from_batch_job", discover_mock)
    monkeypatch.setattr("scripts.aws_run_evolution.verify_completed_manifest", verify_mock)

    # 1. Default invocation uses theme_mode="canonical" and timeout=13200.0 (220 min)
    exit_code = main(["--config-path", "configs/telegram/forwarded_message_evolution.yml"])
    assert exit_code == 0
    assert submit_mock.call_args[1]["theme_mode"] == "canonical"
    assert wait_mock.call_args[1]["timeout_seconds"] == 13200.0

    # 2. Explicit mock invocation uses theme_mode="mock"
    exit_code = main([
        "--config-path",
        "configs/twitter/reply_evolution.yml",
        "--theme-mode",
        "mock",
    ])
    assert exit_code == 0
    assert submit_mock.call_args[1]["theme_mode"] == "mock"
    assert wait_mock.call_args[1]["timeout_seconds"] == 13200.0


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


def test_wait_for_batch_job_default_timeout() -> None:
    """Verify default timeout is 13200.0 seconds (220 minutes)."""
    import inspect
    sig = inspect.signature(wait_for_batch_job)
    assert sig.parameters["timeout_seconds"].default == 13200.0



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


def test_discover_run_id_from_batch_job_multi_page_pagination_real_data_shape() -> None:
    """Reproduction and regression test for CloudWatch pagination beyond 5,000 and 10,000 events.

    Reproduces the proven dev failure where a real run generated 13,668 events across 4 pages,
    with the first valid completion marker at event 13,216. Under the old cutoff (>= 5,000 events),
    discovery stopped prematurely on page 2.
    """
    batch_mock = MagicMock()
    batch_mock.describe_jobs.return_value = {
        "jobs": [
            {
                "jobId": "job-twitter-reply-real",
                "container": {"logStreamName": "analytics/job-twitter-reply/stream"},
            }
        ]
    }

    # Construct pages matching the measured diagnostic counts:
    # Page 1: 3,789 dummy events
    # Page 2: 3,970 dummy events (cumulative: 7,759)
    # Page 3: 3,921 dummy events (cumulative: 11,680)
    # Page 4: 1,988 events:
    #   - 1,535 dummy events (cumulative: 13,215)
    #   - Event 13,216: completion marker with run_id
    #   - 452 trailing dummy events (cumulative: 13,668)
    # Page 5: 0 events, stabilized forward token
    page1_events = [{"message": f"step info 1.{i}"} for i in range(3789)]
    page2_events = [{"message": f"step info 2.{i}"} for i in range(3970)]
    page3_events = [{"message": f"step info 3.{i}"} for i in range(3921)]

    expected_run_id = "a5d43c5b-46b4-4a75-8200-38ef0afa8646"
    completion_event = {
        "message": f"batch_job_completed_successfully run_id={expected_run_id} total_duration_seconds=1234.5"
    }
    page4_prefix = [{"message": f"step info 4.{i}"} for i in range(1535)]
    page4_suffix = [{"message": f"step info 4.{i}"} for i in range(452)]
    page4_events = page4_prefix + [completion_event] + page4_suffix
    assert len(page4_events) == 1988

    total_events = len(page1_events) + len(page2_events) + len(page3_events) + len(page4_events)
    assert total_events == 13668
    completion_idx = len(page1_events) + len(page2_events) + len(page3_events) + len(page4_prefix)
    assert completion_idx == 13215  # 0-indexed, meaning the 13,216th event

    logs_mock = MagicMock()
    logs_mock.get_log_events.side_effect = [
        {"events": page1_events, "nextForwardToken": "token-page-2"},
        {"events": page2_events, "nextForwardToken": "token-page-3"},
        {"events": page3_events, "nextForwardToken": "token-page-4"},
        {"events": page4_events, "nextForwardToken": "token-page-5"},
        {"events": [], "nextForwardToken": "token-page-5"},  # Token stabilization
    ]

    run_id = discover_run_id_from_batch_job(
        batch_mock,
        logs_mock,
        job_id="job-twitter-reply-real",
        log_group_name="/aws/batch/job/community-analysis-dev",
    )

    assert run_id == expected_run_id
    assert logs_mock.get_log_events.call_count == 5

    # Verify calls and pagination tokens
    call_args = logs_mock.get_log_events.call_args_list
    assert "nextToken" not in call_args[0][1]
    assert call_args[0][1]["startFromHead"] is True
    assert call_args[1][1]["nextToken"] == "token-page-2"
    assert call_args[2][1]["nextToken"] == "token-page-3"
    assert call_args[3][1]["nextToken"] == "token-page-4"
    assert call_args[4][1]["nextToken"] == "token-page-5"


def test_discover_run_id_from_batch_job_max_pages_guard_fails_closed() -> None:
    """Verify that exceeding max_pages raises RuntimeError and fails closed."""
    assert DEFAULT_MAX_LOG_PAGES == 100

    batch_mock = MagicMock()
    batch_mock.describe_jobs.return_value = {
        "jobs": [
            {
                "jobId": "job-runaway",
                "container": {"logStreamName": "analytics/job-runaway/stream"},
            }
        ]
    }

    logs_mock = MagicMock()

    def fake_get_log_events(**kwargs):
        current_token = kwargs.get("nextToken", "token-0")
        token_num = int(current_token.split("-")[1]) if "-" in current_token else 0
        return {
            "events": [{"message": f"line {token_num}"}],
            "nextForwardToken": f"token-{token_num + 1}",
        }

    logs_mock.get_log_events.side_effect = fake_get_log_events

    with pytest.raises(
        RuntimeError,
        match=r"Exceeded maximum log pages safety limit \(5\)",
    ) as exc_info:
        discover_run_id_from_batch_job(
            batch_mock,
            logs_mock,
            job_id="job-runaway",
            log_group_name="/aws/batch/job/community-analysis-dev",
            max_pages=5,
        )

    assert "accumulated 5 events across 5 pages" in str(exc_info.value)
    assert logs_mock.get_log_events.call_count == 5


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


def test_get_batch_job_log_stream_name_attempts_task_properties() -> None:
    """Documented AWS DescribeJobs attempt shape: attempts[] -> taskProperties[] -> containers[]."""
    job_info = {
        "attempts": [
            {
                "taskProperties": [
                    {
                        "containers": [
                            {
                                "name": "analytics",
                                "logStreamName": "analytics/job-123/stream-attempt-1",
                            },
                            {
                                "name": "tei-similarity",
                                "logStreamName": "tei-similarity/job-123/stream-attempt-1",
                            },
                            {
                                "name": "tei-clustering",
                                "logStreamName": "tei-clustering/job-123/stream-attempt-1",
                            },
                        ]
                    }
                ]
            }
        ]
    }
    assert (
        get_batch_job_log_stream_name(job_info, "analytics")
        == "analytics/job-123/stream-attempt-1"
    )
    assert (
        get_batch_job_log_stream_name(job_info, "tei-similarity")
        == "tei-similarity/job-123/stream-attempt-1"
    )
    assert (
        get_batch_job_log_stream_name(job_info, "tei-clustering")
        == "tei-clustering/job-123/stream-attempt-1"
    )
    assert get_batch_job_log_stream_name(job_info, "non-existent") is None


def test_cross_layer_tei_batch_architecture_and_submission_contract() -> None:
    """Cross-layer regression contract:

    1. BatchStack TEI job definition uses ecs_properties multi-container (analytics, tei-similarity, tei-clustering).
    2. Operational evolution SubmitJob uses ecsPropertiesOverride targeting 'analytics' (no containerOverrides).
    3. build_analytics_ecs_properties_override produces an ecsPropertiesOverride targeting exactly 'analytics'.
    """
    # 1. BatchStack architecture defines multi-container ecs_properties
    batch_stack_path = Path("infra/community_analysis_infra/batch_stack.py")
    assert batch_stack_path.is_file()
    stack_content = batch_stack_path.read_text(encoding="utf-8")
    assert "ecs_properties=batch.CfnJobDefinition.EcsPropertiesProperty" in stack_content
    assert 'name="analytics"' in stack_content
    assert 'name="tei-similarity"' in stack_content
    assert 'name="tei-clustering"' in stack_content

    # 2. Operational evolution submission uses ecsPropertiesOverride and no containerOverrides
    batch_mock = MagicMock()
    batch_mock.submit_job.return_value = {"jobId": "job-contract-1"}
    submit_evolution_batch_job(
        batch_mock,
        environment="dev",
        config_path="configs/telegram/forwarded_message_evolution.yml",
        job_definition="arn:aws:batch:us-east-1:123456789012:job-definition/community-analysis-dev-analytics-tei-job:3",
    )
    op_kwargs = batch_mock.submit_job.call_args[1]
    assert "containerOverrides" not in op_kwargs, "Operational TEI submit must not use containerOverrides"
    assert "ecsPropertiesOverride" in op_kwargs, "Operational TEI submit must use ecsPropertiesOverride"
    op_containers = op_kwargs["ecsPropertiesOverride"]["taskProperties"][0]["containers"]
    assert len(op_containers) == 1
    assert op_containers[0]["name"] == "analytics"

    # 3. Helper always targets exactly 'analytics'
    helper_override = build_analytics_ecs_properties_override([{"name": "CONFIG_PATH", "value": "test.yml"}])
    assert "taskProperties" in helper_override
    helper_containers = helper_override["taskProperties"][0]["containers"]
    assert len(helper_containers) == 1
    assert helper_containers[0]["name"] == "analytics"
