from pathlib import Path

import pytest

from src.tracking.factory import parse_tracking_settings


def _enabled_config() -> dict:
    return {
        "tracking": {
            "enabled": True,
            "backend": "mlflow",
            "experiment_name": "community-analysis-tests",
            "backend_store_path": ".mlflow-test/mlflow.db",
            "artifact_root": ".mlflow-test/artifacts",
            "nested_stage_runs": True,
            "failure_policy": "warn",
            "log_artifact_references": True,
        }
    }


def test_tracking_is_disabled_when_configuration_is_absent(tmp_path):
    settings = parse_tracking_settings({}, tmp_path)
    assert settings.enabled is False
    assert not (tmp_path / ".mlflow").exists()


def test_explicit_disabled_configuration_does_not_validate_paths(tmp_path):
    settings = parse_tracking_settings(
        {"tracking": {"enabled": False}},
        tmp_path,
    )
    assert settings.enabled is False
    assert not any(tmp_path.iterdir())


def test_tracking_enabled_paths_resolve_under_project_root(tmp_path):
    settings = parse_tracking_settings(_enabled_config(), tmp_path)
    assert settings.enabled is True
    assert settings.backend == "mlflow"
    assert Path(settings.backend_store_path).is_relative_to(tmp_path)
    assert Path(settings.artifact_root).is_relative_to(tmp_path)
    assert settings.tracking_uri.startswith("sqlite:///")
    assert settings.artifact_uri.startswith("file://")
    assert not Path(settings.backend_store_path).exists()


@pytest.mark.parametrize(
    "mutation, message",
    [
        (
            lambda cfg: cfg["tracking"].pop("experiment_name"),
            "Missing required",
        ),
        (
            lambda cfg: cfg["tracking"].update({"backend": "other"}),
            "must be 'mlflow'",
        ),
        (
            lambda cfg: cfg["tracking"].update({"failure_policy": "strict"}),
            "must be 'warn'",
        ),
        (
            lambda cfg: cfg["tracking"].update({"unknown": True}),
            "Unknown tracking keys",
        ),
        (
            lambda cfg: cfg["tracking"].update({"artifact_root": "/tmp/absolute"}),
            "repository-relative",
        ),
        (
            lambda cfg: cfg["tracking"].update({"backend_store_path": "../escape.db"}),
            "escapes",
        ),
    ],
)
def test_invalid_tracking_configuration_fails(tmp_path, mutation, message):
    config = _enabled_config()
    mutation(config)
    with pytest.raises(ValueError, match=message):
        parse_tracking_settings(config, tmp_path)
