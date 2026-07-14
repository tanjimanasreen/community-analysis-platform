import pandas as pd
from src.pipelines.social_network_pipeline import run_network_community_pipeline
from unittest.mock import patch
import os

def test_direct_domain_execution(tmp_path):
    """Prove the domain function is callable without Prefect wrappers."""
    df = pd.DataFrame({
        "target": [
            "{'username': 'user1', 'user_id': 1}",
            "{'username': 'user2', 'user_id': 2}",
        ],
        "source": [
            "{'from_id': 2, 'forwarder_id': 1, 'unique_id': 'm1', 'created_at': '2017-03-01 10:00:00', 'text': 'Hello user1'}",
            "{'from_id': 1, 'forwarder_id': 2, 'unique_id': 'm2', 'created_at': '2017-03-01 10:05:00', 'text': 'Hello user2'}",
        ],
        "relation": ["REPLIED_TO", "REPLIED_BY"]
    })

    # We patch networkx and community detection to avoid heavy work in a small sanity test
    with patch("src.pipelines.social_network_pipeline.get_network_graph") as mock_graph, \
         patch("src.pipelines.social_network_pipeline.get_louvain_community") as mock_louvain:

        import networkx as nx
        G = nx.DiGraph()
        G.add_node(1)
        G.add_node(2)
        mock_graph.return_value = (G, G)
        mock_louvain.return_value = ([[1, 2]], {1: 1, 2: 1})

        # Calling directly, without prefect
        result = run_network_community_pipeline(
            df=df,
            content_type="reply",
            data_type="twitter",
            month="march",
            year="2017",
            date_column="created_at",
            creator_relation="REPLIED_TO",
            spreader_relation="REPLIED_BY",
            creator_node_column="target",
            spreader_node_column="target",
            text_node_column_creator_df="source",
            min_total_post=0,
            min_shared_post=0,
            min_members=1,
            output_dir=str(tmp_path)
        )
        assert result is True

def test_no_prefect_imports_in_domain():
    import subprocess
    import os

    # Run ripgrep/grep to ensure no prefect imports in domain modules
    domain_dirs = ["src/pipelines", "src/communities", "src/topics", "src/graph_store"]
    for d in domain_dirs:
        if not os.path.exists(d):
            continue
        cmd = f"grep -rn -E 'import prefect|from prefect' {d}"
        try:
            output = subprocess.check_output(cmd, shell=True, text=True)
            assert False, f"Found Prefect imports in {d}:\n{output}"
        except subprocess.CalledProcessError as e:
            # grep returns non-zero when no match is found, which is what we want!
            assert e.returncode == 1
