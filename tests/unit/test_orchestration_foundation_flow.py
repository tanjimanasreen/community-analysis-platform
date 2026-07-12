import pytest
import os
from prefect.testing.utilities import prefect_test_harness
from src.orchestration.foundation_flow import run_orchestration_foundation_flow

@pytest.fixture(autouse=True, scope="session")
def prefect_test_fixture():
    with prefect_test_harness():
        yield

def test_foundation_flow(tmp_path):
    config = {"key": "value"}
    dataset_metadata = {
        "dataset_id": "ds-test",
        "path": "/mock/path.csv",
        "sha256": "abcdef123"
    }
    output_root = str(tmp_path / "output")
    
    # Run the offline flow
    result = run_orchestration_foundation_flow(
        config=config,
        dataset_metadata=dataset_metadata,
        output_root=output_root
    )
    
    # Verify small serializable metadata is returned
    assert result["pipeline_run_id"] is not None
    assert result["prefect_flow_run_id"] is not None
    assert result["config_digest"] is not None
    assert result["artifact_ref_hash"] is not None
    
    # Verify artifact was created in temporary test directory
    assert os.path.exists(result["artifact_ref_path"])
    assert result["artifact_ref_path"].startswith(output_root)
