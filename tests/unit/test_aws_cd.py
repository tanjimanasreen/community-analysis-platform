"""Unit tests for scripts/aws_cd.py deployment helper."""

from __future__ import annotations

import io
import urllib.request
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.aws_cd import (
    APPROVED_DEV_APPLICATION_STACKS,
    build_and_deploy_frontend,
    check_ecr_image_exists,
    cleanup_github_runner_docker_state,
    compute_tei_fingerprint,
    deploy_cdk_application_stacks,
    smoke_test_frontend,
    validate_environment,
    validate_source_sha,
)


def test_validate_environment() -> None:
    validate_environment("dev")
    with pytest.raises(ValueError, match="is forbidden"):
        validate_environment("prod")
    with pytest.raises(ValueError, match="is forbidden"):
        validate_environment("staging")


def test_validate_source_sha() -> None:
    assert validate_source_sha("6d4dcbbcd5f67ff89850d4b52c333b0804965b77") == "6d4dcbbcd5f67ff89850d4b52c333b0804965b77"
    assert validate_source_sha("6d4dcbb") == "6d4dcbb"
    assert validate_source_sha("ABCDEF1234567") == "abcdef1234567"

    with pytest.raises(ValueError, match="Invalid source SHA"):
        validate_source_sha("short")
    with pytest.raises(ValueError, match="Invalid source SHA"):
        validate_source_sha("not-a-valid-hex-sha12345")
    with pytest.raises(ValueError, match="Invalid source SHA"):
        validate_source_sha("a" * 41)


def test_compute_tei_fingerprint(tmp_path: Path) -> None:
    test_file = tmp_path / "Dockerfile.tei"
    test_file.write_text("FROM test-image\nRUN echo 1\n", encoding="utf-8")
    fp1 = compute_tei_fingerprint(test_file)
    assert fp1.startswith("tei-")
    assert len(fp1) == 20  # "tei-" + 16 chars

    # Determinism
    fp2 = compute_tei_fingerprint(test_file)
    assert fp1 == fp2

    # Different content produces different fingerprint
    test_file.write_text("FROM test-image\nRUN echo 2\n", encoding="utf-8")
    fp3 = compute_tei_fingerprint(test_file)
    assert fp3 != fp1


def test_check_ecr_image_exists() -> None:
    ecr_mock = MagicMock()
    ecr_mock.describe_images.return_value = {"imageDetails": [{"imageTag": "test-tag"}]}
    assert check_ecr_image_exists(ecr_mock, "test-repo", "test-tag") is True

    ecr_mock.describe_images.return_value = {"imageDetails": []}
    assert check_ecr_image_exists(ecr_mock, "test-repo", "missing-tag") is False


def test_approved_dev_application_stacks() -> None:
    # Ensure exact stack set is present and cicd is excluded
    assert "community-analysis-dev-storage" in APPROVED_DEV_APPLICATION_STACKS
    assert "community-analysis-dev-registry" in APPROVED_DEV_APPLICATION_STACKS
    assert "community-analysis-dev-api" in APPROVED_DEV_APPLICATION_STACKS
    assert "community-analysis-dev-frontend" in APPROVED_DEV_APPLICATION_STACKS
    assert "community-analysis-dev-batch" in APPROVED_DEV_APPLICATION_STACKS
    assert "community-analysis-dev-cicd" not in APPROVED_DEV_APPLICATION_STACKS
    assert len(APPROVED_DEV_APPLICATION_STACKS) == 5


@patch("scripts.aws_cd.run_command")
def test_deploy_cdk_application_stacks(mock_run: MagicMock) -> None:
    deploy_cdk_application_stacks(
        stage="dev",
        image_tag="testsha123",
        tei_image_tag="tei-12345678abcdef01",
        infra_dir="infra",
    )
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "npx"
    assert cmd[1] == "cdk"
    assert cmd[2] == "deploy"
    # Ensure all 5 stacks are listed
    for stack in APPROVED_DEV_APPLICATION_STACKS:
        assert stack in cmd
    assert "community-analysis-dev-cicd" not in cmd
    assert "--all" not in cmd
    assert "-c" in cmd
    assert "stage=dev" in cmd
    assert "image_tag=testsha123" in cmd
    assert "tei_image_tag=tei-12345678abcdef01" in cmd


@patch("scripts.aws_cd.run_command")
def test_build_and_deploy_frontend(mock_run: MagicMock, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<div id='root'></div>")

    build_and_deploy_frontend(
        frontend_dir=tmp_path,
        bucket_name="test-frontend-bucket",
        distribution_id="E123456789",
    )
    assert mock_run.call_count == 3


@patch("urllib.request.urlopen")
def test_smoke_test_frontend(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b"<!DOCTYPE html><html><body><div id=\"root\"></div></body></html>"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    smoke_test_frontend("test.cloudfront.net")
    mock_urlopen.assert_called_once()


@patch("scripts.aws_cd.smoke_test_frontend")
@patch("scripts.aws_cd.deploy_cdk_application_stacks")
@patch("scripts.aws_cd.build_and_deploy_frontend")
@patch("scripts.aws_cd.run_command")
def test_cd_main_exact_run_id_correlation_and_no_docker_login(
    mock_run_cmd: MagicMock,
    mock_build_fe: MagicMock,
    mock_deploy_cdk: MagicMock,
    mock_smoke_fe: MagicMock,
) -> None:
    """Verify that CD main workflow uses exact Batch job run-id discovery and performs no internal ECR login."""
    from scripts.aws_cd import main

    batch_mock = MagicMock()
    batch_mock.submit_job.return_value = {"jobId": "batch-accept-job-999"}

    with (
        patch("boto3.client") as mock_boto,
        patch("scripts.aws_run_evolution.wait_for_batch_job") as mock_wait,
        patch("scripts.aws_run_evolution.discover_run_id_from_batch_job") as mock_discover,
        patch("scripts.aws_run_evolution.verify_completed_manifest") as mock_verify_manifest,
        patch("scripts.smoke_live_api.main", return_value=0) as mock_smoke_api,
    ):
        cfn_mock = MagicMock()
        cfn_mock.describe_stacks.return_value = {
            "Stacks": [
                {
                    "Outputs": [
                        {"OutputKey": "ApiEndpoint", "OutputValue": "https://api.test/api/v1"},
                        {"OutputKey": "CognitoUserPoolId", "OutputValue": "pool-123"},
                        {"OutputKey": "CognitoAppClientId", "OutputValue": "client-123"},
                        {"OutputKey": "FrontendBucketName", "OutputValue": "fe-bucket"},
                        {"OutputKey": "CloudFrontDistributionId", "OutputValue": "dist-123"},
                        {"OutputKey": "CloudFrontDomainName", "OutputValue": "d123.cloudfront.net"},
                    ]
                }
            ]
        }
        sts_mock = MagicMock()
        sts_mock.get_caller_identity.return_value = {"Account": "123456789012"}
        ecr_mock = MagicMock()
        ecr_mock.describe_images.return_value = {"imageDetails": [{"imageTag": "tei-test"}]}

        def client_factory(service_name, **kwargs):
            if service_name == "cloudformation":
                return cfn_mock
            elif service_name == "sts":
                return sts_mock
            elif service_name == "batch":
                return batch_mock
            elif service_name == "ecr":
                return ecr_mock
            return MagicMock()

        mock_boto.side_effect = client_factory
        mock_discover.return_value = "run-exact-accept-777"

        exit_code = main(
            [
                "--environment",
                "dev",
                "--source-sha",
                "6d4dcbbcd5f67ff89850d4b52c333b0804965b77",
            ]
        )

        assert exit_code == 0
        # Verify Batch job submitted
        batch_mock.submit_job.assert_called_once()
        # Verify wait called on exact job ID
        mock_wait.assert_called_once_with(batch_mock, "batch-accept-job-999", timeout_seconds=7200.0)
        # Verify exact run_id discovery from Batch job logs
        mock_discover.assert_called_once()
        call_args = mock_discover.call_args[0]
        assert call_args[2] == "batch-accept-job-999"  # exact job_id
        # Verify manifest verified with that exact run ID
        mock_verify_manifest.assert_called_once()
        assert mock_verify_manifest.call_args[0][2] == "run-exact-accept-777"
        # Verify API smoke called with that exact run ID
        mock_smoke_api.assert_called_once()
        smoke_cmd_args = mock_smoke_api.call_args[0][0]
        assert "--run-id" in smoke_cmd_args
        run_id_idx = smoke_cmd_args.index("--run-id") + 1
        assert smoke_cmd_args[run_id_idx] == "run-exact-accept-777"

        # Verify NO internal docker login command was run
        for call in mock_run_cmd.call_args_list:
            cmd = call[0][0]
            assert "docker login" not in str(cmd)
            assert "get-login-password" not in str(cmd)


@patch("scripts.aws_cd.run_command")
def test_cleanup_github_runner_docker_state_noop_locally(
    mock_run_cmd: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test A: When GITHUB_ACTIONS is absent or not 'true', no cleanup commands are run."""
    image_ref = "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo:test-tag"

    # Absent
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    cleanup_github_runner_docker_state(image_ref)
    mock_run_cmd.assert_not_called()

    # Explicitly false
    monkeypatch.setenv("GITHUB_ACTIONS", "false")
    cleanup_github_runner_docker_state(image_ref)
    mock_run_cmd.assert_not_called()

    # Empty string
    monkeypatch.setenv("GITHUB_ACTIONS", "")
    cleanup_github_runner_docker_state(image_ref)
    mock_run_cmd.assert_not_called()

    # Arbitrary non-true values
    monkeypatch.setenv("GITHUB_ACTIONS", "1")
    cleanup_github_runner_docker_state(image_ref)
    mock_run_cmd.assert_not_called()

    monkeypatch.setenv("GITHUB_ACTIONS", "TRUE")
    cleanup_github_runner_docker_state(image_ref)
    mock_run_cmd.assert_not_called()


@patch("scripts.aws_cd.run_command")
def test_cleanup_github_runner_docker_state_github_actions(
    mock_run_cmd: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test B: When GITHUB_ACTIONS=true, issues exact docker image rm followed by builder prune --force."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    image_ref = "123456789012.dkr.ecr.us-east-1.amazonaws.com/community-analysis-dev-api:abc1234"

    cleanup_github_runner_docker_state(image_ref)

    assert mock_run_cmd.call_count == 2
    calls = [call[0][0] for call in mock_run_cmd.call_args_list]
    assert calls[0] == ["docker", "image", "rm", image_ref]
    assert calls[1] == ["docker", "builder", "prune", "--force"]

    # Verify no broad pruning or force-removal flags
    for call_cmd in calls:
        cmd_str = " ".join(call_cmd)
        assert "system prune" not in cmd_str
        assert "container prune" not in cmd_str
        assert "volume prune" not in cmd_str
        assert "image prune" not in cmd_str
    assert "--force" not in calls[0]  # exact image rm must not use --force


def _setup_mock_cd_environment(
    mock_boto: MagicMock,
    *,
    tei_exists: bool = False,
    batch_job_id: str = "batch-accept-job-999",
) -> None:
    """Helper to mock common AWS services for aws_cd.main() tests."""
    cfn_mock = MagicMock()
    cfn_mock.describe_stacks.return_value = {
        "Stacks": [
            {
                "Outputs": [
                    {"OutputKey": "ApiEndpoint", "OutputValue": "https://api.test/api/v1"},
                    {"OutputKey": "CognitoUserPoolId", "OutputValue": "pool-123"},
                    {"OutputKey": "CognitoAppClientId", "OutputValue": "client-123"},
                    {"OutputKey": "FrontendBucketName", "OutputValue": "fe-bucket"},
                    {"OutputKey": "CloudFrontDistributionId", "OutputValue": "dist-123"},
                    {"OutputKey": "CloudFrontDomainName", "OutputValue": "d123.cloudfront.net"},
                ]
            }
        ]
    }
    sts_mock = MagicMock()
    sts_mock.get_caller_identity.return_value = {"Account": "123456789012"}
    ecr_mock = MagicMock()
    ecr_mock.describe_images.return_value = (
        {"imageDetails": [{"imageTag": "tei-test"}]} if tei_exists else {"imageDetails": []}
    )
    batch_mock = MagicMock()
    batch_mock.submit_job.return_value = {"jobId": batch_job_id}

    def client_factory(service_name: str, **kwargs: Any) -> MagicMock:
        if service_name == "cloudformation":
            return cfn_mock
        elif service_name == "sts":
            return sts_mock
        elif service_name == "batch":
            return batch_mock
        elif service_name == "ecr":
            return ecr_mock
        return MagicMock()

    mock_boto.side_effect = client_factory


@patch("scripts.aws_cd.smoke_test_frontend")
@patch("scripts.aws_cd.deploy_cdk_application_stacks")
@patch("scripts.aws_cd.build_and_deploy_frontend")
@patch("scripts.aws_cd.run_command")
def test_cd_main_github_actions_cleanup_order(
    mock_run_cmd: MagicMock,
    mock_build_fe: MagicMock,
    mock_deploy_cdk: MagicMock,
    mock_smoke_fe: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test C: Under GITHUB_ACTIONS=true, verify build -> push -> cleanup order for all built images."""
    from scripts.aws_cd import main

    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    with (
        patch("boto3.client") as mock_boto,
        patch("scripts.aws_run_evolution.wait_for_batch_job"),
        patch("scripts.aws_run_evolution.discover_run_id_from_batch_job", return_value="run-accept-1"),
        patch("scripts.aws_run_evolution.verify_completed_manifest"),
        patch("scripts.smoke_live_api.main", return_value=0),
    ):
        _setup_mock_cd_environment(mock_boto, tei_exists=False)

        exit_code = main(
            [
                "--environment",
                "dev",
                "--source-sha",
                "6d4dcbbcd5f67ff89850d4b52c333b0804965b77",
            ]
        )
        assert exit_code == 0

        docker_cmds = [
            call[0][0] for call in mock_run_cmd.call_args_list if call[0][0][0] == "docker"
        ]

        # Should have 3 images x 4 commands each = 12 docker commands:
        # [build, push, image rm, builder prune] for TEI, API, Analytics
        assert len(docker_cmds) == 12

        # Verify TEI cycle
        assert docker_cmds[0][:3] == ["docker", "build", "--platform"]
        assert "community-analysis-dev-tei" in docker_cmds[0][5]
        tei_ref = docker_cmds[0][5]
        assert docker_cmds[1] == ["docker", "push", tei_ref]
        assert docker_cmds[2] == ["docker", "image", "rm", tei_ref]
        assert docker_cmds[3] == ["docker", "builder", "prune", "--force"]

        # Verify API cycle
        assert docker_cmds[4][:3] == ["docker", "build", "--platform"]
        assert "community-analysis-dev-api" in docker_cmds[4][5]
        api_ref = docker_cmds[4][5]
        assert docker_cmds[5] == ["docker", "push", api_ref]
        assert docker_cmds[6] == ["docker", "image", "rm", api_ref]
        assert docker_cmds[7] == ["docker", "builder", "prune", "--force"]

        # Verify Analytics cycle
        assert docker_cmds[8][:3] == ["docker", "build", "--platform"]
        assert "community-analysis-dev-analytics" in docker_cmds[8][5]
        analytics_ref = docker_cmds[8][5]
        assert docker_cmds[9] == ["docker", "push", analytics_ref]
        assert docker_cmds[10] == ["docker", "image", "rm", analytics_ref]
        assert docker_cmds[11] == ["docker", "builder", "prune", "--force"]


@patch("scripts.aws_cd.smoke_test_frontend")
@patch("scripts.aws_cd.deploy_cdk_application_stacks")
@patch("scripts.aws_cd.build_and_deploy_frontend")
@patch("scripts.aws_cd.run_command")
def test_cd_main_push_failure_does_not_cleanup(
    mock_run_cmd: MagicMock,
    mock_build_fe: MagicMock,
    mock_deploy_cdk: MagicMock,
    mock_smoke_fe: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test D: When a docker push fails, no docker image rm or builder prune is executed."""
    from scripts.aws_cd import main

    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    def side_effect(cmd: list[str], **kwargs: Any) -> MagicMock:
        if cmd[:2] == ["docker", "push"]:
            raise RuntimeError("Simulated push failure to ECR")
        res = MagicMock()
        res.returncode = 0
        return res

    mock_run_cmd.side_effect = side_effect

    with (
        patch("boto3.client") as mock_boto,
        patch("scripts.aws_run_evolution.wait_for_batch_job"),
        patch("scripts.aws_run_evolution.discover_run_id_from_batch_job"),
        patch("scripts.aws_run_evolution.verify_completed_manifest"),
        patch("scripts.smoke_live_api.main", return_value=0),
    ):
        _setup_mock_cd_environment(mock_boto, tei_exists=True)  # TEI skipped, fails on API push

        with pytest.raises(RuntimeError, match="Simulated push failure to ECR"):
            main(
                [
                    "--environment",
                    "dev",
                    "--source-sha",
                    "6d4dcbbcd5f67ff89850d4b52c333b0804965b77",
                ]
            )

        executed_cmds = [call[0][0] for call in mock_run_cmd.call_args_list]
        # Verify no cleanup was attempted
        for cmd in executed_cmds:
            assert cmd[:3] != ["docker", "image", "rm"]
            assert cmd[:3] != ["docker", "builder", "prune"]


@patch("scripts.aws_cd.smoke_test_frontend")
@patch("scripts.aws_cd.deploy_cdk_application_stacks")
@patch("scripts.aws_cd.build_and_deploy_frontend")
@patch("scripts.aws_cd.run_command")
def test_cd_main_tei_ecr_cache_hit_does_not_cleanup_tei(
    mock_run_cmd: MagicMock,
    mock_build_fe: MagicMock,
    mock_deploy_cdk: MagicMock,
    mock_smoke_fe: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test E: When TEI fingerprint exists in ECR, TEI build/push/cleanup are all skipped."""
    from scripts.aws_cd import main

    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    with (
        patch("boto3.client") as mock_boto,
        patch("scripts.aws_run_evolution.wait_for_batch_job"),
        patch("scripts.aws_run_evolution.discover_run_id_from_batch_job", return_value="run-accept-2"),
        patch("scripts.aws_run_evolution.verify_completed_manifest"),
        patch("scripts.smoke_live_api.main", return_value=0),
    ):
        _setup_mock_cd_environment(mock_boto, tei_exists=True)

        exit_code = main(
            [
                "--environment",
                "dev",
                "--source-sha",
                "6d4dcbbcd5f67ff89850d4b52c333b0804965b77",
            ]
        )
        assert exit_code == 0

        docker_cmds = [
            call[0][0] for call in mock_run_cmd.call_args_list if call[0][0][0] == "docker"
        ]

        # Only API and Analytics: 2 images x 4 commands = 8 commands
        assert len(docker_cmds) == 8

        # No command references the TEI repository
        for cmd in docker_cmds:
            assert "community-analysis-dev-tei" not in " ".join(cmd)

        # API cycle
        api_ref = docker_cmds[0][5]
        assert "community-analysis-dev-api" in api_ref
        assert docker_cmds[1] == ["docker", "push", api_ref]
        assert docker_cmds[2] == ["docker", "image", "rm", api_ref]
        assert docker_cmds[3] == ["docker", "builder", "prune", "--force"]

        # Analytics cycle
        analytics_ref = docker_cmds[4][5]
        assert "community-analysis-dev-analytics" in analytics_ref
        assert docker_cmds[5] == ["docker", "push", analytics_ref]
        assert docker_cmds[6] == ["docker", "image", "rm", analytics_ref]
        assert docker_cmds[7] == ["docker", "builder", "prune", "--force"]


@patch("scripts.aws_cd.smoke_test_frontend")
@patch("scripts.aws_cd.deploy_cdk_application_stacks")
@patch("scripts.aws_cd.build_and_deploy_frontend")
@patch("scripts.aws_cd.run_command")
def test_cd_main_local_execution_no_cleanup(
    mock_run_cmd: MagicMock,
    mock_build_fe: MagicMock,
    mock_deploy_cdk: MagicMock,
    mock_smoke_fe: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test F: Local execution (no GITHUB_ACTIONS) performs zero Docker image or cache cleanup."""
    from scripts.aws_cd import main

    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    with (
        patch("boto3.client") as mock_boto,
        patch("scripts.aws_run_evolution.wait_for_batch_job"),
        patch("scripts.aws_run_evolution.discover_run_id_from_batch_job", return_value="run-accept-3"),
        patch("scripts.aws_run_evolution.verify_completed_manifest"),
        patch("scripts.smoke_live_api.main", return_value=0),
    ):
        _setup_mock_cd_environment(mock_boto, tei_exists=False)

        exit_code = main(
            [
                "--environment",
                "dev",
                "--source-sha",
                "6d4dcbbcd5f67ff89850d4b52c333b0804965b77",
            ]
        )
        assert exit_code == 0

        docker_cmds = [
            call[0][0] for call in mock_run_cmd.call_args_list if call[0][0][0] == "docker"
        ]

        # 3 builds + 3 pushes = 6 docker commands
        assert len(docker_cmds) == 6
        for cmd in docker_cmds:
            assert cmd[:3] != ["docker", "image", "rm"]
            assert cmd[:3] != ["docker", "builder", "prune"]
