from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import mlflow
import pytest
from mlflow.tracking import MlflowClient
from prefect.testing.utilities import prefect_test_harness

from src.cli import validate_config
from src.orchestration.composition_flow import run_evolution_analysis_flow
from src.orchestration.models import PipelineRunResult
from src.orchestration.retry_policy import ErrorCategory, PipelineError
from tests.integration.test_orchestration_smoke import _assert_result_boundary


def _tracked_evolution_config(output_root: Path, *, enabled: bool = True) -> dict:
    config = validate_config("tests/configs/test_evolution.yml")
    config["output_base_path"] = str(output_root)
    config["theme_provider"] = {
        "primary": "mock",
        "fallback": False,
        "fallback_chain": [],
    }
    config["orchestration"] = {"month_workers": 1}
    config["tracking"] = {
        "enabled": enabled,
        "backend": "mlflow",
        "experiment_name": "community-analysis-evolution-integration",
        "backend_store_path": ".mlflow-test/mlflow.db",
        "artifact_root": ".mlflow-test/artifacts",
        "nested_stage_runs": True,
        "failure_policy": "warn",
        "log_artifact_references": True,
    }
    config["provider"] = {
        "credentials": {
            "token": "must-not-persist",
            "password": "secret-password",
        }
    }
    return config


def _run_full_flow(config: dict) -> PipelineRunResult:
    return run_evolution_analysis_flow(config=config)


def _all_runs(client: MlflowClient, experiment_id: str):
    return client.search_runs([experiment_id], max_results=100)


def _assert_no_secrets_in_runs(runs) -> None:
    serialized = json.dumps(
        [
            {
                "tags": run.data.tags,
                "params": run.data.params,
                "metrics": run.data.metrics,
            }
            for run in runs
        ],
        sort_keys=True,
    )
    assert "must-not-persist" not in serialized
    assert "secret-password" not in serialized
    assert "credentials" not in serialized


def test_tracked_full_flow_creates_parent_children_and_safe_summaries(
    monkeypatch, tmp_path
):
    project_root = tmp_path / "project"
    project_root.mkdir()
    output_root = tmp_path / "output"
    monkeypatch.setattr(
        "src.orchestration.composition_flow.get_project_root",
        lambda: str(project_root),
    )

    assert mlflow.active_run() is None
    with prefect_test_harness():
        result = _run_full_flow(
            _tracked_evolution_config(output_root, enabled=True)
        )

    assert isinstance(result, PipelineRunResult)
    assert result.tracking is not None
    _assert_result_boundary(result)
    assert mlflow.active_run() is None

    client = MlflowClient(tracking_uri=result.tracking.tracking_uri)
    runs = _all_runs(client, result.tracking.experiment_id)
    assert len(runs) == 6
    by_stage = {run.data.tags.get("stage_name", "parent"): run for run in runs}
    assert set(by_stage) == {
        "parent",
        "network_03",
        "topic_03",
        "network_04",
        "topic_04",
        "evolution_theme",
    }
    assert all(run.info.status == "FINISHED" for run in runs)
    for stage_name in (
        "network_03",
        "topic_03",
        "network_04",
        "topic_04",
        "evolution_theme",
    ):
        assert (
            by_stage[stage_name].data.tags["mlflow.parentRunId"]
            == result.tracking.parent_run_id
        )

    parent = by_stage["parent"]
    assert parent.data.metrics["stage_count"] == 5
    assert parent.data.metrics["completed_stage_count"] == 5
    assert parent.data.tags["run_status"] == "FINISHED"
    _assert_no_secrets_in_runs(runs)

    summary_paths = {
        item.path for item in client.list_artifacts(parent.info.run_id, "summaries")
    }
    assert summary_paths >= {
        "summaries/artifact_reference_manifest.json",
        "summaries/lineage_summary.json",
        "summaries/run_metrics_summary.json",
    }

    state_root = project_root / ".mlflow-test"
    persisted = b"".join(
        path.read_bytes() for path in state_root.rglob("*") if path.is_file()
    )
    assert b"must-not-persist" not in persisted
    assert b"secret-password" not in persisted

    lineage_files = list(state_root.rglob("lineage_summary.json"))
    assert len(lineage_files) >= 1
    lineage = json.loads(lineage_files[0].read_text(encoding="utf-8"))
    assert len(lineage["datasets"]) == 2
    assert str(project_root) not in json.dumps(lineage)


def test_tracking_disabled_creates_no_mlflow_state(monkeypatch, tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    output_root = tmp_path / "output"
    monkeypatch.setattr(
        "src.orchestration.composition_flow.get_project_root",
        lambda: str(project_root),
    )

    with prefect_test_harness():
        result = _run_full_flow(
            _tracked_evolution_config(output_root, enabled=False)
        )

    assert result.tracking is None
    assert not (project_root / ".mlflow").exists()
    assert not (project_root / ".mlflow-test").exists()


def test_analytical_failure_marks_parent_and_stage_failed(monkeypatch, tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    output_root = tmp_path / "output"
    config = _tracked_evolution_config(output_root, enabled=True)
    monkeypatch.setattr(
        "src.orchestration.composition_flow.get_project_root",
        lambda: str(project_root),
    )

    failure = PipelineError(
        "safe analytical failure",
        ErrorCategory.SCHEMA_VIOLATION,
    )
    with (
        prefect_test_harness(),
        patch(
            "src.pipelines.social_network_pipeline.run_network_community_pipeline",
            side_effect=failure,
        ),
    ):
        with pytest.raises(PipelineError, match="safe analytical failure"):
            run_evolution_analysis_flow(config=config)

    tracking_uri = f"sqlite:///{project_root / '.mlflow-test' / 'mlflow.db'}"
    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name("community-analysis-evolution-integration")
    assert experiment is not None
    runs = _all_runs(client, experiment.experiment_id)
    assert len(runs) == 3

    by_stage = {
        run.data.tags.get("stage_name", "parent"): run
        for run in runs
    }
    assert set(by_stage) == {"parent", "network_03", "network_04"}

    parent = by_stage["parent"]
    network_03 = by_stage["network_03"]
    network_04 = by_stage["network_04"]

    assert parent.info.status == "FAILED"
    assert network_03.info.status == "FAILED"
    assert network_04.info.status == "FAILED"

    assert parent.data.tags["run_status"] == "FAILED"
    assert network_03.data.tags["run_status"] == "FAILED"
    assert network_04.data.tags["run_status"] == "FAILED"

    assert parent.data.tags["failure_category"] == "SCHEMA_VIOLATION"
    assert parent.data.tags["exception_type"] == "PipelineError"

    assert network_03.data.tags["failure_category"] == "SCHEMA_VIOLATION"
    assert network_03.data.tags["failure_stage"] == "network_03"
    assert network_03.data.tags["exception_type"] == "PipelineError"
    assert network_03.data.tags["mlflow.parentRunId"] == parent.info.run_id

    assert network_04.data.tags["failure_category"] == "SCHEMA_VIOLATION"
    assert network_04.data.tags["failure_stage"] == "network_04"
    assert network_04.data.tags["exception_type"] == "PipelineError"
    assert network_04.data.tags["mlflow.parentRunId"] == parent.info.run_id


def test_mlflow_write_failure_does_not_change_analytical_success(
    monkeypatch, tmp_path, caplog
):
    caplog.set_level("WARNING")
    project_root = tmp_path / "project"
    project_root.mkdir()
    output_root = tmp_path / "output"
    monkeypatch.setattr(
        "src.orchestration.composition_flow.get_project_root",
        lambda: str(project_root),
    )

    with (
        prefect_test_harness(),
        patch(
            "mlflow.tracking.MlflowClient.log_metric",
            side_effect=RuntimeError("must-not-persist"),
        ),
    ):
        result = _run_full_flow(
            _tracked_evolution_config(output_root, enabled=True)
        )

    assert isinstance(result, PipelineRunResult)
    assert result.artifacts
    assert "RuntimeError" in caplog.text
    assert "must-not-persist" not in caplog.text
