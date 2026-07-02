import networkx as nx
import pandas as pd

from src.network.centrality import (
    get_community_network_centrality,
    get_prominent_communities_stat,
    show_hightest_in_degree,
    show_hightest_out_degree,
)


def test_centrality_summaries_on_small_directed_graph():
    graph = nx.DiGraph()
    graph.add_edge("u1", "u2")
    graph.add_edge("u1", "u3")
    graph.add_edge("u2", "u3")
    users = pd.DataFrame(
        {
            "user_id": ["u1", "u2", "u3"],
            "username": ["alice", "bob", "charlie"],
        }
    )

    out_stats = show_hightest_out_degree(graph, users)
    in_stats = show_hightest_in_degree(graph, users)
    combined = get_community_network_centrality(graph, users)

    assert out_stats["max_out_degree_user"] == "u1"
    assert out_stats["max_out_degree_val"] == 1.0
    assert in_stats["max_in_degree_user"] == "u3"
    assert in_stats["max_in_degree_val"] == 1.0
    assert combined["avg_out_degree_val"] == 0.5
    assert combined["avg_in_degree_val"] == 0.5


def test_prominent_community_stats_empty_input_returns_empty_dict():
    graph = nx.DiGraph()
    users = pd.DataFrame({"user_id": [], "username": []})

    assert get_prominent_communities_stat([], graph, users) == {}
