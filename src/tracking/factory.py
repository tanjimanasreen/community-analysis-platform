from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping

from src.tracking.contracts import ExperimentTracker, TrackingSettings
from src.tracking.noop_tracker import NoOpExperimentTracker

logger = logging.getLogger(__name__)

_ALLOWED_KEYS = {
    "enabled",
    "backend",
    "experiment_name",
    "backend_store_path",
    "artifact_root",
    "nested_stage_runs",
    "failure_policy",
    "log_artifact_references",
}
_REQUIRED_ENABLED_KEYS = _ALLOWED_KEYS - {"enabled"}


def _resolve_under_root(project_root: Path, raw_path: object, field_name: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"tracking.{field_name} must be a non-empty relative path")
    candidate = Path(raw_path)
    if candidate.is_absolute():
        raise ValueError(f"tracking.{field_name} must be repository-relative")
    resolved = (project_root / candidate).resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError(f"tracking.{field_name} escapes the repository root") from exc
    return resolved


def parse_tracking_settings(
    config: Mapping[str, Any], project_root: str | Path
) -> TrackingSettings:
    raw = config.get("tracking")
    if raw is None:
        return TrackingSettings(enabled=False)
    if not isinstance(raw, Mapping):
        raise ValueError("tracking must be a mapping")

    unknown = set(raw) - _ALLOWED_KEYS
    if unknown:
        raise ValueError(f"Unknown tracking keys: {', '.join(sorted(unknown))}")

    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("tracking.enabled must be a boolean")
    if not enabled:
        return TrackingSettings(enabled=False)

    missing = [key for key in sorted(_REQUIRED_ENABLED_KEYS) if key not in raw]
    if missing:
        raise ValueError(f"Missing required tracking keys: {', '.join(missing)}")
    if raw["backend"] != "mlflow":
        raise ValueError("tracking.backend must be 'mlflow'")
    if raw["failure_policy"] != "warn":
        raise ValueError("tracking.failure_policy must be 'warn'")
    if (
        not isinstance(raw["experiment_name"], str)
        or not raw["experiment_name"].strip()
    ):
        raise ValueError("tracking.experiment_name must be non-empty")
    if not isinstance(raw["nested_stage_runs"], bool):
        raise ValueError("tracking.nested_stage_runs must be a boolean")
    if not isinstance(raw["log_artifact_references"], bool):
        raise ValueError("tracking.log_artifact_references must be a boolean")

    root = Path(project_root).resolve()
    backend_store = _resolve_under_root(
        root, raw["backend_store_path"], "backend_store_path"
    )
    artifact_root = _resolve_under_root(root, raw["artifact_root"], "artifact_root")

    return TrackingSettings(
        enabled=True,
        backend="mlflow",
        experiment_name=raw["experiment_name"].strip(),
        backend_store_path=str(backend_store),
        artifact_root=str(artifact_root),
        tracking_uri=f"sqlite:///{backend_store.as_posix()}",
        artifact_uri=artifact_root.as_uri(),
        nested_stage_runs=raw["nested_stage_runs"],
        failure_policy="warn",
        log_artifact_references=raw["log_artifact_references"],
    )


def create_experiment_tracker(
    config: Mapping[str, Any], project_root: str | Path
) -> ExperimentTracker:
    settings = parse_tracking_settings(config, project_root)
    if not settings.enabled:
        return NoOpExperimentTracker(settings)

    try:
        from src.tracking.mlflow_tracker import MlflowExperimentTracker

        return MlflowExperimentTracker(settings)
    except Exception as exc:
        logger.warning(
            "MLflow tracking initialization failed; continuing without tracking (%s)",
            type(exc).__name__,
        )
        return NoOpExperimentTracker(settings)
