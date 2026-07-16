import pytest
from pathlib import Path
from src.config.loader import load_config, validate_run_config
from src.tracking.factory import parse_tracking_settings


def test_sample_config_remains_valid():
    """
    Proves that the primary sample configuration remains valid
    as the schema evolves.
    """
    config_path = Path("configs/sample_twitter_reply.yml")
    assert config_path.exists(), "Sample configuration file must exist"

    # Should not raise an exception
    config = load_config(str(config_path))
    validate_run_config(config)

    assert config.get("data_type") == "twitter"
    assert config.get("content_type") == "reply"
    assert config.get("lda", {}).get("num_topics") == 15
    assert config.get("theme", {}).get("enable_gpt") is False


def test_tracking_is_disabled_when_sample_config_omits_section():
    config = load_config("configs/sample_twitter_reply.yml")
    validate_run_config(config)
    settings = parse_tracking_settings(config, Path.cwd())
    assert settings.enabled is False
    assert settings.backend is None


def test_invalid_enabled_tracking_config_is_rejected():
    config = load_config("configs/sample_twitter_reply.yml")
    config["tracking"] = {
        "enabled": True,
        "backend": "mlflow",
        "experiment_name": "tests",
        "backend_store_path": "../escape.db",
        "artifact_root": ".mlflow/artifacts",
        "nested_stage_runs": True,
        "failure_policy": "warn",
        "log_artifact_references": True,
    }
    with pytest.raises(ValueError, match="escapes the repository root"):
        validate_run_config(config)
