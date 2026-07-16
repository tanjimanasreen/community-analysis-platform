import pandas as pd
import networkx as nx

from src.network.graphs import get_network_graph


def test_get_network_graph_thresholds():
    # Min total_post = 10, Min shared_post = 5
    df = pd.DataFrame(
        {
            "source": ["u1", "u2", "u3"],
            "target": ["u2", "u3", "u1"],
            "total_post": [12, 10, 8],  # u3 doesn't meet total threshold
            "shared_post": [6, 4, 10],  # u2 doesn't meet shared threshold
            "weighted_post": [0.5, 0.4, 1.25],
        }
    )

    G_abs, G_perc = get_network_graph(df)

    # Only u1->u2 should be included since it has total_post=12 (>=10) and shared_post=6 (>=5)
    assert G_abs.number_of_edges() == 1
    assert G_abs.has_edge("u1", "u2")

    assert G_perc.number_of_edges() == 1
    assert G_perc.has_edge("u1", "u2")

    # Verify the weight is correctly assigned in the edge attributes
    assert G_abs["u1"]["u2"][0]["shared_post"] == 6
    assert G_perc["u1"]["u2"][0]["weighted_post"] == 0.5


def test_get_network_graph_allows_custom_thresholds():
    df = pd.DataFrame(
        {
            "source": ["u1", "u2"],
            "target": ["u2", "u3"],
            "total_post": [2, 3],
            "shared_post": [1, 3],
            "weighted_post": [0.5, 1.0],
        }
    )

    G_abs, G_perc = get_network_graph(
        df,
        min_total_post=2,
        min_shared_post=1,
    )

    assert isinstance(G_abs, nx.MultiDiGraph)
    assert isinstance(G_perc, nx.MultiDiGraph)
    assert G_abs.number_of_edges() == 2
    assert G_perc.number_of_edges() == 2
    assert G_abs["u2"]["u3"][0]["shared_post"] == 3
    assert G_perc["u2"]["u3"][0]["weighted_post"] == 1.0
