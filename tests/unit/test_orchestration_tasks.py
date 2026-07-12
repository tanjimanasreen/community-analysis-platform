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
    
def test_resolve_dataset_identity_task_computed_hash(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("dummy")
    ident = resolve_dataset_identity_task.fn(
        path=str(f),
        dataset_id="test"
    )
    assert ident.sha256 != "a"*64
    assert len(ident.sha256) == 64
