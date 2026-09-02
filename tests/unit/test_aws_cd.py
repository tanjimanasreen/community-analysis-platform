"""Unit tests for scripts/aws_cd.py deployment helper."""

from __future__ import annotations

import io
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.aws_cd import (
    APPROVED_DEV_APPLICATION_STACKS,
    build_and_deploy_frontend,
    check_ecr_image_exists,
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
