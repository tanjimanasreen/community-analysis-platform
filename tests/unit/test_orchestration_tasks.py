import pytest
import os
from src.orchestration.tasks import validate_run_configuration_task, resolve_dataset_identity_task
from src.orchestration.retry_policy import PipelineError

def test_validate_run_configuration_task():
    config = {"output_dir": "/mock/out", "other": "val"}
    val_config = validate_run_configuration_task.fn(config)
    assert val_config.output_root == "/mock/out"
    assert "other" in val_config.raw_config
    assert val_config.config_digest is not None

def test_validate_run_configuration_task_missing_output_dir():
    config = {"other": "val"}
    with pytest.raises(PipelineError, match="output_dir is required"):
        validate_run_configuration_task.fn(config)

def test_resolve_dataset_identity_task_missing_file():
    with pytest.raises(PipelineError, match="Input dataset not found"):
        resolve_dataset_identity_task.fn(
            path="/does/not/exist.csv",
            dataset_id="test",
            known_sha256="a"*64
        )

def test_resolve_dataset_identity_task_known_hash(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("dummy")
    ident = resolve_dataset_identity_task.fn(
        path=str(f),
        dataset_id="test",
        known_sha256="a"*64
    )
    assert ident.sha256 == "a"*64
    assert ident.identity_source == "supplied"
    
def test_resolve_dataset_identity_task_computed_hash(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("dummy")
    ident = resolve_dataset_identity_task.fn(
        path=str(f),
        dataset_id="test"
    )
    assert ident.sha256 != "a"*64
    assert len(ident.sha256) == 64
    assert ident.identity_source == "computed"

def test_resolve_dataset_identity_task_malformed_hash(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("dummy")
    with pytest.raises(PipelineError, match="Malformed SHA-256 hash"):
        resolve_dataset_identity_task.fn(
            path=str(f),
            dataset_id="test",
            known_sha256="short"
        )

def test_resolve_dataset_identity_task_verify_hash_success(tmp_path):
    from src.orchestration.hashing import hash_file
    f = tmp_path / "data.csv"
    f.write_text("dummy")
    correct_hash = hash_file(str(f))
    ident = resolve_dataset_identity_task.fn(
        path=str(f),
        dataset_id="test",
        known_sha256=correct_hash,
        verify_file_hash=True
    )
    assert ident.sha256 == correct_hash
    assert ident.identity_source == "verified"

def test_resolve_dataset_identity_task_verify_hash_mismatch(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("dummy")
    with pytest.raises(PipelineError, match="Dataset hash mismatch"):
        resolve_dataset_identity_task.fn(
            path=str(f),
            dataset_id="test",
            known_sha256="a"*64,
            verify_file_hash=True
        )
