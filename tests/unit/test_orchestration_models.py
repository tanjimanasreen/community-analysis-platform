import pytest
from src.orchestration.models import DatasetIdentity, ArtifactReference, PipelineRunContext

VALID_HASH = "a" * 64

def test_dataset_identity_creation():
    di = DatasetIdentity(
        dataset_id="test-dataset",
        path="/some/path",
        sha256=VALID_HASH
    )
    assert di.dataset_id == "test-dataset"
    assert di.sha256 == VALID_HASH

def test_dataset_identity_requires_sha256():
    with pytest.raises(ValueError):
        DatasetIdentity(dataset_id="ds1", path="a", sha256="")

def test_artifact_reference_requires_sha256():
    with pytest.raises(ValueError):
        ArtifactReference(path="a", sha256="", media_type="text")

def test_pipeline_run_context_creation():
    di = DatasetIdentity(
        dataset_id="test",
        path="/path",
        sha256=VALID_HASH
    )
    ctx = PipelineRunContext.create(
        pipeline_run_id="run1",
        git_commit="commit1",
        config_digest="digest1",
        output_root="/out",
        datasets=[di]
    )
    d = ctx.to_dict()
    assert d["pipeline_run_id"] == "run1"
    assert d["dataset_identities"][0]["sha256"] == VALID_HASH
    assert ctx.prefect_flow_run_id is None

def test_dataset_identity_sha256_validation():
    # Empty
    with pytest.raises(ValueError, match="sha256 must be"):
        DatasetIdentity("test", "/path", "")
    
    # Fake/Short
    with pytest.raises(ValueError, match="64-character hexadecimal"):
        DatasetIdentity("test", "/path", "fakehash")
        
    # Non-hexadecimal 64 characters
    with pytest.raises(ValueError, match="64-character hexadecimal"):
        DatasetIdentity("test", "/path", "z" * 64)
        
    # Whitespace padding
    with pytest.raises(ValueError, match="64-character hexadecimal"):
        DatasetIdentity("test", "/path", " " + ("a" * 63))

def test_dataset_identity_sha256_normalization():
    # Uppercase normalizes to lowercase
    di = DatasetIdentity("test", "/path", ("A" * 64))
    assert di.sha256 == ("a" * 64)

def test_models_import_is_side_effect_free():
    import os
    original_env = dict(os.environ)
    import src.orchestration.models
    assert os.environ == original_env, "Importing models mutated os.environ"
