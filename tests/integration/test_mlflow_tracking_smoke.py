from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import mlflow
import pandas as pd
import pytest
from mlflow.tracking import MlflowClient
from prefect.testing.utilities import prefect_test_harness

from src.orchestration.composition_flow import run_monthly_analysis_flow
from src.orchestration.models import PipelineRunResult
from src.orchestration.retry_policy import ErrorCategory, PipelineError
from tests.integration.test_orchestration_smoke import (
    _assert_result_boundary,
    _fake_network_domain,
    _fake_theme_domain,
    _fake_topic_domain,
    _full_config,
)


def _tracked_config(dataset: Path, output_root: Path) -> dict:
    config = _full_config(dataset, output_root)
    config["tracking"] = {
        "enabled": True,
        "backend": "mlflow",
        "experiment_name": "community-analysis-integration",
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


def _run_full_flow(config: dict, dataset: Path) -> PipelineRunResult:
    with (
        patch(
            "src.pipelines.social_network_pipeline.run_network_community_pipeline",
            side_effect=_fake_network_domain,
        ),
        patch(
            "src.pipelines.social_network_pipeline.run_topic_phase",
            side_effect=_fake_topic_domain,
        ),
        patch(
            "src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data",
            side_effect=_fake_theme_domain,
        ),
    ):
        return run_monthly_analysis_flow(
            config=config,
            dataset_path=str(dataset),
            dataset_id="smoke-dataset",
            run_topics=True,
            run_themes=True,
            dvc_revision="revision-1",
        )


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
    dataset = project_root / "data" / "dataset.csv"
    dataset.parent.mkdir()
    pd.DataFrame({"value": [1]}).to_csv(dataset, index=False)
    Path(f"{dataset}.dvc").write_text(
        "outs:\n- md5: dvc-content-hash\n  path: dataset.csv\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "output"
    monkeypatch.setattr(
        "src.orchestration.composition_flow.get_project_root",
        lambda: str(project_root),
    )

    assert mlflow.active_run() is None
    with prefect_test_harness():
        result = _run_full_flow(
            _tracked_config(dataset, output_root),
            dataset,
        )

    assert isinstance(result, PipelineRunResult)
    assert result.tracking is not None
    _assert_result_boundary(result)
    assert mlflow.active_run() is None

    client = MlflowClient(tracking_uri=result.tracking.tracking_uri)
    runs = _all_runs(client, result.tracking.experiment_id)
    assert len(runs) == 4
    by_stage = {
        run.data.tags.get("stage_name", "parent"): run for run in runs
    }
    assert set(by_stage) == {
        "parent",
        "network_community",
        "topic",
        "theme",
    }
    assert all(run.info.status == "FINISHED" for run in runs)
    for stage_name in ("network_community", "topic", "theme"):
        assert (
            by_stage[stage_name].data.tags["mlflow.parentRunId"]
            == result.tracking.parent_run_id
        )

    parent = by_stage["parent"]
    assert parent.data.metrics["stage_count"] == 3
    assert parent.data.metrics["completed_stage_count"] == 3
    assert parent.data.tags["run_status"] == "FINISHED"
    _assert_no_secrets_in_runs(runs)

    summary_paths = {
        item.path
        for item in client.list_artifacts(parent.info.run_id, "summaries")
    }
    assert summary_paths == {
        "summaries/artifact_reference_manifest.json",
        "summaries/lineage_summary.json",
        "summaries/provider_run_summary.json",
        "summaries/run_metrics_summary.json",
    }

    state_root = project_root / ".mlflow-test"
    assert not list(state_root.rglob(dataset.name))
    persisted = b"".join(
        path.read_bytes() for path in state_root.rglob("*") if path.is_file()
    )
    assert b"must-not-persist" not in persisted
    assert b"secret-password" not in persisted

    lineage_files = list(state_root.rglob("lineage_summary.json"))
    assert len(lineage_files) == 1
    lineage = json.loads(lineage_files[0].read_text(encoding="utf-8"))
    dataset_lineage = lineage["datasets"][0]
    assert dataset_lineage["dataset_relative_path"] == "data/dataset.csv"
    assert dataset_lineage["dvc_file_relative_path"] == "data/dataset.csv.dvc"
    assert dataset_lineage["dvc_content_hash"] == "dvc-content-hash"
    assert dataset_lineage["dvc_revision"] == "revision-1"
    assert str(project_root) not in json.dumps(lineage)


def test_tracking_disabled_creates_no_mlflow_state(monkeypatch, tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    dataset = project_root / "dataset.csv"
    pd.DataFrame({"value": [1]}).to_csv(dataset, index=False)
    output_root = tmp_path / "output"
    monkeypatch.setattr(
        "src.orchestration.composition_flow.get_project_root",
        lambda: str(project_root),
    )

    with prefect_test_harness():
        result = _run_full_flow(
            _full_config(dataset, output_root),
            dataset,
        )

    assert result.tracking is None
    assert not (project_root / ".mlflow").exists()
    assert not (project_root / ".mlflow-test").exists()


def test_analytical_failure_marks_parent_and_stage_failed(
    monkeypatch, tmp_path
):
    project_root = tmp_path / "project"
    project_root.mkdir()
    dataset = project_root / "dataset.csv"
    pd.DataFrame({"value": [1]}).to_csv(dataset, index=False)
    output_root = tmp_path / "output"
    config = _tracked_config(dataset, output_root)
    monkeypatch.setattr(
        "src.orchestration.composition_flow.get_project_root",
        lambda: str(project_root),
    )

    failure = PipelineError(
        "safe analytical failure",
        ErrorCategory.SCHEMA_VIOLATION,
    )
    with prefect_test_harness(), patch(
        "src.pipelines.social_network_pipeline.run_network_community_pipeline",
        side_effect=failure,
    ):
        with pytest.raises(PipelineError, match="safe analytical failure"):
            run_monthly_analysis_flow(
                config=config,
                dataset_path=str(dataset),
                dataset_id="smoke-dataset",
            )

    tracking_uri = f"sqlite:///{project_root / '.mlflow-test' / 'mlflow.db'}"
    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(
        "community-analysis-integration"
    )
    assert experiment is not None
    runs = _all_runs(client, experiment.experiment_id)
    assert len(runs) == 2
    assert all(run.info.status == "FAILED" for run in runs)
    for run in runs:
        assert run.data.tags["run_status"] == "FAILED"
        assert run.data.tags["failure_category"] == "SCHEMA_VIOLATION"
        assert run.data.tags["failure_stage"] == "network_community"
        assert run.data.tags["exception_type"] == "PipelineError"


def test_mlflow_write_failure_does_not_change_analytical_success(
    monkeypatch, tmp_path, caplog
):
    caplog.set_level("WARNING")
    project_root = tmp_path / "project"
    project_root.mkdir()
    dataset = project_root / "dataset.csv"
    pd.DataFrame({"value": [1]}).to_csv(dataset, index=False)
    output_root = tmp_path / "output"
    monkeypatch.setattr(
        "src.orchestration.composition_flow.get_project_root",
        lambda: str(project_root),
    )

    with prefect_test_harness(), patch(
        "mlflow.tracking.MlflowClient.log_metric",
        side_effect=RuntimeError("must-not-persist"),
    ):
        result = _run_full_flow(
            _tracked_config(dataset, output_root),
            dataset,
        )

    assert isinstance(result, PipelineRunResult)
    assert result.artifacts
    assert "RuntimeError" in caplog.text
    assert "must-not-persist" not in caplog.text
