"""Unit tests for StageConfig and stage resolution."""

import pytest
from community_analysis_infra.config import (
    ALLOWED_STAGES,
    StageConfig,
    get_stage_config,
)


def test_allowed_stages() -> None:
    assert "dev" in ALLOWED_STAGES
    assert "prod" in ALLOWED_STAGES


def test_stage_config_defaults() -> None:
    cfg = StageConfig(stage_name="dev")
    assert cfg.stage_name == "dev"
    assert cfg.project_name == "community-analysis"
    assert cfg.region == "us-east-1"
    assert cfg.tags == {
        "Project": "community-analysis",
        "Environment": "dev",
        "ManagedBy": "aws-cdk",
    }
    assert cfg.format_stack_name("storage") == "community-analysis-dev-storage"


def test_stage_config_invalid_stage() -> None:
    with pytest.raises(ValueError, match="Invalid stage 'staging'"):
        StageConfig(stage_name="staging")


def test_get_stage_config_dev() -> None:
    cfg = get_stage_config("dev")
    assert cfg.stage_name == "dev"
    assert cfg.format_stack_name("api") == "community-analysis-dev-api"


def test_get_stage_config_prod() -> None:
    cfg = get_stage_config("prod")
    assert cfg.stage_name == "prod"
    assert cfg.format_stack_name("batch") == "community-analysis-prod-batch"


def test_get_stage_config_invalid() -> None:
    with pytest.raises(ValueError, match="Unknown stage 'qa'"):
        get_stage_config("qa")


def test_get_stage_config_missing_none() -> None:
    with pytest.raises(ValueError, match="CDK stage is required"):
        get_stage_config(None)


def test_get_stage_config_missing_empty() -> None:
    with pytest.raises(ValueError, match="CDK stage is required"):
        get_stage_config("")


def test_get_stage_config_missing_whitespace() -> None:
    with pytest.raises(ValueError, match="CDK stage is required"):
        get_stage_config("   ")
