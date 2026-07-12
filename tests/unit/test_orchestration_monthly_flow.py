import pytest
import os
import pandas as pd
from prefect.testing.utilities import prefect_test_harness
from src.orchestration.pipeline_flow import run_monthly_network_foundation_flow
from src.orchestration.models import ArtifactReference

@pytest.fixture(autouse=True, scope="session")
def prefect_test_fixture():
    with prefect_test_harness():
        yield

def test_run_monthly_network_foundation_flow(tmp_path):
    # Setup tiny fixture
    input_df = pd.DataFrame({
        "source": [
            "{'unique_id': 'm1', 'from_id': 'u1', 'forwarder_id': 'u2', 'text': 'hello', 'created_at': '2017-03-01'}",
            "{'unique_id': 'm2', 'from_id': 'u2', 'forwarder_id': 'u3', 'text': 'hello2', 'created_at': '2017-03-02'}",
            "{'unique_id': 'm2', 'from_id': 'u2', 'forwarder_id': 'u3', 'text': 'hello2', 'created_at': '2017-03-02'}",
        ],
        "target": [
            "{'user_id': 'u1', 'username': 'u1'}",
            "{'user_id': 'u2', 'username': 'u2'}",
            "{'user_id': 'u3', 'username': 'u3'}"
        ],
        "relation": ["REPLIED_TO", "REPLIED_BY", "REPLIED_BY"]
    })
    input_path = tmp_path / "tiny_input.csv"
    input_df.to_csv(input_path, index=False)
    
    output_root = tmp_path / "output"
    
    config = {
        "output_dir": str(output_root),
        "content_type": "reply",
        "data_type": "twitter",
        "month": "march",
        "year": "2017",
        # Force low thresholds so it passes filtering
        "min_total_post": 0,
        "min_shared_post": 0,
        "min_members": 1,
        "date_column": "created_at"
    }
    
    # Execution
    result = run_monthly_network_foundation_flow(
        config=config,
        dataset_path=str(input_path),
        dataset_id="tiny_test"
    )
    
    # Verify outputs
    assert result["pipeline_run_id"] is not None
    assert result["prefect_flow_run_id"] is not None
    assert result["config_digest"] is not None
    assert result["dataset_identity"].dataset_id == "tiny_test"
    
    artifacts = result["artifacts"]
    assert len(artifacts) > 0
    for art in artifacts:
        assert isinstance(art, ArtifactReference)
        assert os.path.exists(art.path)
        assert art.path.startswith(str(output_root))
        assert len(art.sha256) == 64
