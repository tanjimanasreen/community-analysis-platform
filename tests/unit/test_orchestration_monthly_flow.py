import pytest

pytestmark = pytest.mark.requires_loopback

import os
from pathlib import Path

import pandas as pd
import pytest
from prefect.testing.utilities import prefect_test_harness
from src.orchestration.pipeline_flow import run_monthly_network_foundation_flow
from src.artifacts import RunStatus, load_run_manifest, run_root_path


@pytest.fixture(autouse=True, scope="session")
def prefect_test_fixture():
    with prefect_test_harness():
        yield


def test_run_monthly_network_foundation_flow(tmp_path):
    # Setup tiny fixture
    input_df = pd.DataFrame(
        {
            "source": [
                "{'unique_id': 'm1', 'from_id': 'u1', 'forwarder_id': 'u2', 'text': 'hello', 'created_at': '2017-03-01'}",
                "{'unique_id': 'm2', 'from_id': 'u2', 'forwarder_id': 'u3', 'text': 'hello2', 'created_at': '2017-03-02'}",
                "{'unique_id': 'm2', 'from_id': 'u2', 'forwarder_id': 'u3', 'text': 'hello2', 'created_at': '2017-03-02'}",
            ],
            "target": [
                "{'user_id': 'u1', 'username': 'u1'}",
                "{'user_id': 'u2', 'username': 'u2'}",
                "{'user_id': 'u3', 'username': 'u3'}",
            ],
            "relation": ["REPLIED_TO", "REPLIED_BY", "REPLIED_BY"],
        }
    )
    input_path = tmp_path / "tiny_input.csv"
    input_df.to_csv(input_path, index=False)

    output_root = tmp_path / "output"

    config = {
        "output_base_path": str(output_root),
        "input_path": str(input_path),
        "content_type": "reply",
        "data_type": "twitter",
        "month": "march",
        "year": "2017",
        "creator_relation": "REPLIED_TO",
        "spreader_relation": "REPLIED_BY",
        "creator_node_column": "target",
        "spreader_node_column": "target",
        "text_node_column": "source",
        "date_column": "created_at",
        "graph_thresholds": {
            "min_total_post": 0,
            "min_shared_post": 0,
            "min_members": 1,
        },
    }

    # Execution
    result = run_monthly_network_foundation_flow(
        config=config, dataset_path=str(input_path), dataset_id="tiny_test"
    )

    # Verify outputs
    assert result.context.pipeline_run_id is not None
    assert result.context.output_root == str(output_root)
    assert len(result.context.dataset_identities) == 1

    assert len(result.artifacts) > 0
    run_root = run_root_path(output_root, result.context.pipeline_run_id)
    manifest = load_run_manifest(run_root)
    assert manifest.status is RunStatus.COMPLETED
    assert (run_root / "resolved_config.yaml").is_file()
    assert (run_root / "inputs/datasets.json").is_file()
    assert any(record.key == "network_data_march" for record in manifest.artifacts)

    # ensure everything is written into the pipeline run root
    for art in result.artifacts:
        assert os.path.exists(art.path)
        assert Path(art.path).resolve().is_relative_to(run_root.resolve())
        assert len(art.sha256) == 64
