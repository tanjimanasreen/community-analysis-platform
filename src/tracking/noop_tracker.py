from __future__ import annotations

from typing import Any, Mapping

from src.tracking.contracts import (
    StageRunReference,
    TrackingRunReference,
    TrackingSettings,
)


class NoOpExperimentTracker:
    def __init__(self, settings: TrackingSettings | None = None) -> None:
        self.settings = settings or TrackingSettings(enabled=False)

    def start_parent_run(
        self, *, run_name: str, tags: Mapping[str, Any], params: Mapping[str, Any]
    ) -> TrackingRunReference | None:
        return None

    def start_stage_run(
        self,
        *,
        parent: TrackingRunReference,
        stage_name: str,
        tags: Mapping[str, Any],
        params: Mapping[str, Any],
    ) -> StageRunReference | None:
        return None

    def log_metrics(self, run_id: str, metrics: Mapping[str, Any]) -> None:
        return None

    def log_tags(self, run_id: str, tags: Mapping[str, Any]) -> None:
        return None

    def log_params(self, run_id: str, params: Mapping[str, Any]) -> None:
        return None

    def log_json_artifact(
        self,
        run_id: str,
        *,
        filename: str,
        payload: Mapping[str, Any],
        artifact_path: str = "summaries",
    ) -> None:
        return None

    def log_table(
        self,
        run_id: str,
        *,
        filename: str,
        df: Any,
    ) -> None:
        return None

    def finish_run(self, run_id: str, status: str) -> None:
        return None
