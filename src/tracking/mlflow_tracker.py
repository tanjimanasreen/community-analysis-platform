from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, TypeVar

from src.tracking.contracts import (
    METRIC_KEYS,
    PARENT_PARAM_KEYS,
    PARENT_TAG_KEYS,
    STAGE_PARAM_KEYS,
    STAGE_TAG_KEYS,
    STATUS_TAG_KEYS,
    StageRunReference,
    TrackingRunReference,
    TrackingSettings,
)
from src.tracking.sanitization import (
    encode_bounded_json,
    sanitize_metrics,
    sanitize_scalar_mapping,
)

logger = logging.getLogger(__name__)
_T = TypeVar("_T")


class MlflowExperimentTracker:
    """Explicit-client MLflow adapter with warning-only failure semantics."""

    def __init__(self, settings: TrackingSettings) -> None:
        if not settings.enabled or not settings.tracking_uri:
            raise ValueError("Enabled MLflow settings are required")

        from mlflow.tracking import MlflowClient

        self.settings = settings
        Path(settings.backend_store_path or "").parent.mkdir(
            parents=True, exist_ok=True
        )
        Path(settings.artifact_root or "").mkdir(parents=True, exist_ok=True)
        self._client = MlflowClient(tracking_uri=settings.tracking_uri)
        self._experiment_id = self._ensure_experiment()

    @property
    def client(self):
        """Expose the client for narrow adapter tests; never persist it."""
        return self._client

    def _safe(self, operation: str, fn: Callable[[], _T], default: _T) -> _T:
        try:
            return fn()
        except Exception as exc:
            logger.warning(
                "MLflow tracking operation %s failed; analysis continues (%s)",
                operation,
                type(exc).__name__,
            )
            return default

    def _ensure_experiment(self) -> str:
        experiment_name = self.settings.experiment_name or "community-analysis"
        experiment = self._client.get_experiment_by_name(experiment_name)
        if experiment is not None:
            return str(experiment.experiment_id)
        return str(
            self._client.create_experiment(
                experiment_name,
                artifact_location=self.settings.artifact_uri,
            )
        )

    @staticmethod
    def _string_values(payload: Mapping[str, Any]) -> dict[str, str]:
        return {
            str(key): str(value) for key, value in payload.items() if value is not None
        }

    def start_parent_run(
        self,
        *,
        run_name: str,
        tags: Mapping[str, Any],
        params: Mapping[str, Any],
    ) -> TrackingRunReference | None:
        def create() -> TrackingRunReference:
            clean_tags = sanitize_scalar_mapping(tags, allowed_keys=PARENT_TAG_KEYS)
            clean_params = sanitize_scalar_mapping(
                params, allowed_keys=PARENT_PARAM_KEYS
            )
            run_tags = self._string_values(clean_tags)
            run_tags["mlflow.runName"] = run_name
            run = self._client.create_run(self._experiment_id, tags=run_tags)
            run_id = run.info.run_id
            for key, value in self._string_values(clean_params).items():
                self._client.log_param(run_id, key, value)
            return TrackingRunReference(
                backend="mlflow",
                experiment_id=self._experiment_id,
                parent_run_id=run_id,
                tracking_uri=self.settings.tracking_uri or "",
            )

        return self._safe("start_parent_run", create, None)

    def start_stage_run(
        self,
        *,
        parent: TrackingRunReference,
        stage_name: str,
        tags: Mapping[str, Any],
        params: Mapping[str, Any],
    ) -> StageRunReference | None:
        if not self.settings.nested_stage_runs:
            return None

        def create() -> StageRunReference:
            clean_tags = sanitize_scalar_mapping(tags, allowed_keys=STAGE_TAG_KEYS)
            clean_params = sanitize_scalar_mapping(
                params, allowed_keys=STAGE_PARAM_KEYS
            )
            run_tags = self._string_values(clean_tags)
            run_tags.update(
                {
                    "mlflow.runName": (f"{stage_name}-{parent.parent_run_id[:8]}"),
                    "mlflow.parentRunId": parent.parent_run_id,
                    "stage_name": stage_name,
                }
            )
            run = self._client.create_run(parent.experiment_id, tags=run_tags)
            run_id = run.info.run_id
            for key, value in self._string_values(clean_params).items():
                self._client.log_param(run_id, key, value)
            return StageRunReference(run_id=run_id, stage_name=stage_name)

        return self._safe("start_stage_run", create, None)

    def log_metrics(self, run_id: str, metrics: Mapping[str, Any]) -> None:
        def log() -> None:
            clean = sanitize_metrics(metrics, allowed_keys=METRIC_KEYS)
            for key, value in clean.items():
                self._client.log_metric(run_id, key, value)

        self._safe("log_metrics", log, None)

    def log_tags(self, run_id: str, tags: Mapping[str, Any]) -> None:
        def log() -> None:
            clean = sanitize_scalar_mapping(tags, allowed_keys=STATUS_TAG_KEYS)
            for key, value in self._string_values(clean).items():
                self._client.set_tag(run_id, key, value)

        self._safe("log_tags", log, None)

    def log_params(self, run_id: str, params: Mapping[str, Any]) -> None:
        def log() -> None:
            clean = sanitize_scalar_mapping(
                params, allowed_keys=PARENT_PARAM_KEYS | STAGE_PARAM_KEYS
            )
            for key, value in self._string_values(clean).items():
                self._client.log_param(run_id, key, value)

        self._safe("log_params", log, None)

    def log_json_artifact(
        self,
        run_id: str,
        *,
        filename: str,
        payload: Mapping[str, Any],
        artifact_path: str = "summaries",
    ) -> None:
        def log() -> None:
            safe_filename = Path(filename).name
            if not safe_filename.endswith(".json"):
                raise ValueError("Tracking artifacts must be JSON files")
            encoded = encode_bounded_json(payload)
            with tempfile.TemporaryDirectory(
                prefix="community-analysis-mlflow-"
            ) as tmp:
                path = Path(tmp) / safe_filename
                path.write_bytes(encoded)
                self._client.log_artifact(
                    run_id,
                    str(path),
                    artifact_path=artifact_path,
                )

        self._safe(f"log_json_artifact:{Path(filename).name}", log, None)

    def log_table(
        self,
        run_id: str,
        *,
        filename: str,
        df: Any,
    ) -> None:
        def log() -> None:
            import mlflow

            if self.settings.tracking_uri:
                mlflow.set_tracking_uri(self.settings.tracking_uri)
            with mlflow.start_run(run_id=run_id):
                mlflow.log_table(data=df, artifact_file=filename)

        self._safe(f"log_table:{filename}", log, None)

    def finish_run(self, run_id: str, status: str) -> None:
        if status not in {"FINISHED", "FAILED", "KILLED"}:
            raise ValueError(f"Unsupported MLflow termination status: {status}")
        self._safe(
            f"finish_run:{status}",
            lambda: self._client.set_terminated(run_id, status=status),
            None,
        )
