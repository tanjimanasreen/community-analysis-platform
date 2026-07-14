import os

import pytest

from src.orchestration.models import (
    ArtifactReference,
    DatasetIdentity,
    PipelineRunContext,
    PipelineRunResult,
)
from src.tracking.contracts import TrackingRunReference

VALID_HASH = "a" * 64


def test_dataset_identity_creation():
    identity = DatasetIdentity(
        dataset_id="test-dataset",
        path="/some/path",
        sha256=VALID_HASH,
    )
    assert identity.dataset_id == "test-dataset"
    assert identity.sha256 == VALID_HASH


def test_dataset_identity_requires_sha256():
    with pytest.raises(ValueError):
        DatasetIdentity(dataset_id="ds1", path="a", sha256="")


def test_artifact_reference_requires_sha256():
    with pytest.raises(ValueError):
        ArtifactReference(path="a", sha256="", media_type="text")


def test_pipeline_run_context_creation():
    identity = DatasetIdentity(
        dataset_id="test",
        path="/path",
        sha256=VALID_HASH,
    )
    context = PipelineRunContext.create(
        pipeline_run_id="run1",
        git_commit="commit1",
        config_digest="digest1",
        output_root="/out",
        datasets=[identity],
    )
    serialized = context.to_dict()
    assert serialized["pipeline_run_id"] == "run1"
    assert serialized["dataset_identities"][0]["sha256"] == VALID_HASH
    assert context.prefect_flow_run_id is None


def test_pipeline_result_contains_only_small_tracking_reference():
    context = PipelineRunContext.create(
        pipeline_run_id="run1",
        git_commit="commit1",
        config_digest="digest1",
        output_root="/out",
        datasets=[],
    )
    tracking = TrackingRunReference(
        backend="mlflow",
        experiment_id="1",
        parent_run_id="run-id",
        tracking_uri="sqlite:////tmp/mlflow.db",
    )
    result = PipelineRunResult(context=context, artifacts=(), tracking=tracking)
    serialized = result.to_dict()
    assert serialized["tracking"] == {
        "backend": "mlflow",
        "experiment_id": "1",
        "parent_run_id": "run-id",
        "tracking_uri": "sqlite:////tmp/mlflow.db",
    }


def test_dataset_identity_sha256_validation():
    with pytest.raises(ValueError, match="sha256 must be"):
        DatasetIdentity("test", "/path", "")
    with pytest.raises(ValueError, match="64-character hexadecimal"):
        DatasetIdentity("test", "/path", "fakehash")
    with pytest.raises(ValueError, match="64-character hexadecimal"):
        DatasetIdentity("test", "/path", "z" * 64)
    with pytest.raises(ValueError, match="64-character hexadecimal"):
        DatasetIdentity("test", "/path", " " + ("a" * 63))


def test_dataset_identity_sha256_normalization():
    identity = DatasetIdentity("test", "/path", "A" * 64)
    assert identity.sha256 == "a" * 64


def test_models_import_is_side_effect_free():
    original_env = dict(os.environ)
    import src.orchestration.models  # noqa: F401

    assert os.environ == original_env, "Importing models mutated os.environ"
