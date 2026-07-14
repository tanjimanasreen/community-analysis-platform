import logging
from pathlib import Path
from unittest.mock import patch

import mlflow
from mlflow.tracking import MlflowClient

from src.tracking.contracts import TrackingSettings
from src.tracking.factory import create_experiment_tracker
from src.tracking.mlflow_tracker import MlflowExperimentTracker
from src.tracking.noop_tracker import NoOpExperimentTracker


def _settings(tmp_path: Path) -> TrackingSettings:
    database = tmp_path / "mlflow" / "mlflow.db"
    artifacts = tmp_path / "mlflow" / "artifacts"
    return TrackingSettings(
        enabled=True,
        backend="mlflow",
        experiment_name="tracker-unit-test",
        backend_store_path=str(database),
        artifact_root=str(artifacts),
        tracking_uri=f"sqlite:///{database.as_posix()}",
        artifact_uri=artifacts.as_uri(),
        nested_stage_runs=True,
        failure_policy="warn",
        log_artifact_references=True,
    )


def _config() -> dict:
    return {
        "tracking": {
            "enabled": True,
            "backend": "mlflow",
            "experiment_name": "tracker-unit-test",
            "backend_store_path": ".mlflow/mlflow.db",
            "artifact_root": ".mlflow/artifacts",
            "nested_stage_runs": True,
            "failure_policy": "warn",
            "log_artifact_references": True,
        }
    }


def _parent_tags() -> dict:
    return {
        "tracking_schema_version": "1.0",
        "tracking_adapter_version": "1.0.0",
        "pipeline_run_id": "pipeline-1",
        "prefect_flow_run_id": "prefect-1",
        "dataset_id": "dataset-1",
        "data_type": "twitter",
        "content_type": "reply",
        "month": "march",
        "year": "2017",
        "git_commit": "abc",
        "git_branch": "test",
        "dvc_revision": "",
        "config_digest": "digest",
        "orchestration_semantic_version": "1.0.0",
        "execution_mode": "local",
        "run_status": "RUNNING",
    }


def _parent_params() -> dict:
    return {
        "run_topics": True,
        "run_themes": True,
        "network_algorithm": "interaction_graph",
        "community_algorithm": "louvain",
        "topic_algorithm": "lda",
        "topic_random_seed": 100,
        "theme_prompt_version": "v1",
        "configured_primary_provider": "mock",
        "configured_primary_model": "",
        "configured_fallback_count": 0,
    }


def test_mlflow_parent_child_lifecycle_and_artifact(tmp_path):
    assert mlflow.active_run() is None
    tracker = MlflowExperimentTracker(_settings(tmp_path))
    parent = tracker.start_parent_run(
        run_name="test-parent",
        tags=_parent_tags(),
        params=_parent_params(),
    )
    assert parent is not None
    child = tracker.start_stage_run(
        parent=parent,
        stage_name="topic",
        tags={
            "tracking_schema_version": "1.0",
            "stage_name": "topic",
            "stage_semantic_version": "1.0.0",
            "run_status": "RUNNING",
        },
        params={"topic_algorithm": "lda", "random_seed": 100},
    )
    assert child is not None
    tracker.log_metrics(child.run_id, {"stage_duration_seconds": 0.5})
    tracker.log_json_artifact(
        parent.parent_run_id,
        filename="lineage_summary.json",
        payload={"schema_version": "1.0", "dataset_id": "dataset-1"},
    )
    tracker.log_tags(child.run_id, {"run_status": "FINISHED"})
    tracker.finish_run(child.run_id, "FINISHED")
    tracker.log_tags(parent.parent_run_id, {"run_status": "FINISHED"})
    tracker.finish_run(parent.parent_run_id, "FINISHED")

    client = MlflowClient(tracking_uri=parent.tracking_uri)
    stored_parent = client.get_run(parent.parent_run_id)
    stored_child = client.get_run(child.run_id)
    assert stored_parent.info.status == "FINISHED"
    assert stored_child.info.status == "FINISHED"
    assert stored_child.data.tags["mlflow.parentRunId"] == parent.parent_run_id
    assert stored_child.data.metrics["stage_duration_seconds"] == 0.5
    artifacts = client.list_artifacts(parent.parent_run_id, "summaries")
    assert [item.path for item in artifacts] == [
        "summaries/lineage_summary.json"
    ]
    assert mlflow.active_run() is None


def test_experiment_is_reused_by_name(tmp_path):
    first = MlflowExperimentTracker(_settings(tmp_path))
    second = MlflowExperimentTracker(_settings(tmp_path))
    assert first._experiment_id == second._experiment_id


def test_tracking_operation_failures_warn_without_raising(
    tmp_path, caplog
):
    tracker = MlflowExperimentTracker(_settings(tmp_path))
    parent = tracker.start_parent_run(
        run_name="test-parent",
        tags=_parent_tags(),
        params=_parent_params(),
    )
    assert parent is not None

    caplog.set_level(logging.WARNING)
    with patch.object(
        tracker.client,
        "log_metric",
        side_effect=RuntimeError("must-not-persist"),
    ):
        tracker.log_metrics(
            parent.parent_run_id,
            {"stage_duration_seconds": 0.5},
        )

    assert "RuntimeError" in caplog.text
    assert "must-not-persist" not in caplog.text
    tracker.finish_run(parent.parent_run_id, "FINISHED")


def test_unsafe_payload_warns_and_is_not_logged(tmp_path, caplog):
    tracker = MlflowExperimentTracker(_settings(tmp_path))
    parent = tracker.start_parent_run(
        run_name="test-parent",
        tags=_parent_tags(),
        params=_parent_params(),
    )
    assert parent is not None

    caplog.set_level(logging.WARNING)
    tracker.log_json_artifact(
        parent.parent_run_id,
        filename="unsafe.json",
        payload={"credentials": {"token": "must-not-persist"}},
    )
    assert "UnsafeTrackingPayload" in caplog.text
    assert "must-not-persist" not in caplog.text
    assert tracker.client.list_artifacts(parent.parent_run_id) == []
    tracker.finish_run(parent.parent_run_id, "FINISHED")


def test_initialization_failure_falls_back_to_noop(tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    with patch(
        "src.tracking.mlflow_tracker.MlflowExperimentTracker",
        side_effect=RuntimeError("must-not-persist"),
    ):
        tracker = create_experiment_tracker(_config(), tmp_path)

    assert isinstance(tracker, NoOpExperimentTracker)
    assert tracker.settings.enabled is True
    assert "RuntimeError" in caplog.text
    assert "must-not-persist" not in caplog.text
