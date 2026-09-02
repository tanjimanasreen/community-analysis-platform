"""Unit tests verifying that the CDK App synthesizes without errors and obeys scoping rules."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import aws_cdk as cdk
from community_analysis_infra.baseline_stack import CommunityAnalysisBaselineStack
from community_analysis_infra.config import get_stage_config


def test_app_synthesis_dev() -> None:
    app = cdk.App(context={"stage": "dev"})
    stage_config = get_stage_config("dev")
    stack_name = stage_config.format_stack_name("baseline")
    stack = CommunityAnalysisBaselineStack(
        app,
        stack_name,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)

    synth_result = app.synth()
    assert synth_result is not None
    assert stack_name in [s.stack_name for s in synth_result.stacks]
    # Verify no application resources are declared in the baseline stack template
    template = synth_result.get_stack_by_name(stack_name).template
    assert "Resources" not in template or len(template.get("Resources", {})) == 0


def test_app_synthesis_prod() -> None:
    app = cdk.App(context={"stage": "prod"})
    stage_config = get_stage_config("prod")
    stack_name = stage_config.format_stack_name("baseline")
    stack = CommunityAnalysisBaselineStack(
        app,
        stack_name,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)

    synth_result = app.synth()
    assert synth_result is not None
    assert stack_name in [s.stack_name for s in synth_result.stacks]
    template = synth_result.get_stack_by_name(stack_name).template
    assert "Resources" not in template or len(template.get("Resources", {})) == 0


def test_app_stage_resolution_missing_fails() -> None:
    app = cdk.App()
    raw_stage = app.node.try_get_context("stage")
    with pytest.raises(ValueError, match="CDK stage is required"):
        get_stage_config(raw_stage)


def test_app_stage_resolution_invalid_fails() -> None:
    app = cdk.App(context={"stage": "invalid"})
    raw_stage = app.node.try_get_context("stage")
    with pytest.raises(ValueError, match="Unknown stage 'invalid'"):
        get_stage_config(raw_stage)


def test_app_synthesis_cicd_stack_dev() -> None:
    from community_analysis_infra.cicd_stack import CicdStack

    app = cdk.App(context={"stage": "dev"})
    stage_config = get_stage_config("dev")
    stack_name = stage_config.format_stack_name("cicd")
    CicdStack(
        app,
        stack_name,
        stage_config=stage_config,
        github_oidc_subject="repo:tanjimanasreen/community-analysis-platform:ref:refs/heads/dev",
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    synth_result = app.synth()
    assert synth_result is not None
    assert stack_name in [s.stack_name for s in synth_result.stacks]
    template = synth_result.get_stack_by_name(stack_name).template
    assert "Resources" in template


def test_app_py_cicd_only_independent_synthesis() -> None:
    """Verify that infra/app.py can synthesize CI/CD stack without any application image tags when explicit subject is provided."""
    infra_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["STAGE"] = "dev"
    env["CICD_ONLY"] = "true"
    env["GITHUB_OIDC_SUBJECT"] = (
        "repo:tanjimanasreen/community-analysis-platform:ref:refs/heads/dev"
    )
    # Ensure no image tags in environment
    env.pop("IMAGE_TAG", None)
    env.pop("BATCH_IMAGE_TAG", None)
    env.pop("TEI_IMAGE_TAG", None)
    env.pop("TEI_ANALYTICS_IMAGE_TAG", None)

    res = subprocess.run(
        [sys.executable, "app.py"],
        cwd=infra_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"app.py failed: {res.stderr}"
    assert "community-analysis-dev-cicd" in res.stderr or res.returncode == 0


def test_app_py_cicd_only_missing_subject_fails_closed() -> None:
    """Verify that app.py fails closed when synthesizing CI/CD stack without an explicit OIDC subject."""
    infra_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["STAGE"] = "dev"
    env["CICD_ONLY"] = "true"
    env.pop("GITHUB_OIDC_SUBJECT", None)

    res = subprocess.run(
        [sys.executable, "app.py"],
        cwd=infra_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "github_oidc_subject is required" in res.stderr


def test_app_py_cicd_only_immutable_subject_succeeds() -> None:
    """Verify that app.py accepts immutable owner/repo ID subject format."""
    infra_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["STAGE"] = "dev"
    env["CICD_ONLY"] = "true"
    env["GITHUB_OIDC_SUBJECT"] = (
        "repo:tanjimanasreen@123456/community-analysis-platform@789012:ref:refs/heads/dev"
    )

    res = subprocess.run(
        [sys.executable, "app.py"],
        cwd=infra_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"app.py failed with immutable subject: {res.stderr}"


def test_app_py_dev_app_only_does_not_require_subject() -> None:
    """Verify that normal dev application synthesis does not require an OIDC subject."""
    infra_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["STAGE"] = "dev"
    env["IMAGE_TAG"] = "dummy-app-sha"
    env.pop("CICD_ONLY", None)
    env.pop("GITHUB_OIDC_SUBJECT", None)

    res = subprocess.run(
        [sys.executable, "app.py"],
        cwd=infra_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"app.py failed: {res.stderr}"


def test_app_py_missing_image_tag_fails_when_required() -> None:
    """Verify that app.py fails fast when synthesizing application stacks without image_tag."""
    infra_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["STAGE"] = "dev"
    env.pop("CICD_ONLY", None)
    env.pop("IMAGE_TAG", None)

    res = subprocess.run(
        [sys.executable, "app.py"],
        cwd=infra_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "image_tag is required" in res.stderr


def test_app_py_batch_requires_three_image_identities() -> None:
    """Verify that BatchStack requires all three image tags when batch_image_tag is passed."""
    infra_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["STAGE"] = "dev"
    env["IMAGE_TAG"] = "test-api-sha"
    env["BATCH_IMAGE_TAG"] = "test-batch-sha"
    env.pop("TEI_ANALYTICS_IMAGE_TAG", None)
    env.pop("TEI_IMAGE_TAG", None)

    res = subprocess.run(
        [sys.executable, "app.py"],
        cwd=infra_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "tei_analytics_image_tag" in res.stderr


def test_app_py_prod_does_not_instantiate_cicd() -> None:
    """Verify that prod stage synthesis never instantiates Plan 097 CI/CD stack."""
    infra_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["STAGE"] = "prod"
    env["IMAGE_TAG"] = "test-prod-sha"

    res = subprocess.run(
        [sys.executable, "app.py"],
        cwd=infra_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"app.py failed for prod: {res.stderr}"
