"""Unit test verifying that the CDK App synthesizes without errors."""

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
