import pytest
from src.orchestration.models import DatasetIdentity, ArtifactReference, PipelineRunContext

def test_dataset_identity_immutability():
    identity = DatasetIdentity(
        dataset_id="ds1",
        path="data/raw.csv",
        sha256="abc"
    )
    with pytest.raises(Exception):
        identity.dataset_id = "ds2"

def test_dataset_identity_requires_sha256():
    with pytest.raises(ValueError):
        DatasetIdentity(dataset_id="ds1", path="a", sha256="")

def test_artifact_reference_requires_sha256():
    with pytest.raises(ValueError):
        ArtifactReference(path="a", sha256="", media_type="text")

def test_pipeline_run_context_serialization():
    identity = DatasetIdentity(dataset_id="ds1", path="data.csv", sha256="hash123")
    ctx = PipelineRunContext.create(
        pipeline_run_id="run1",
        git_commit="commit1",
        config_digest="digest1",
        output_root="out/",
        datasets=[identity]
    )
    d = ctx.to_dict()
    assert d["pipeline_run_id"] == "run1"
    assert d["dataset_identities"][0]["sha256"] == "hash123"
    assert ctx.prefect_flow_run_id is None
