import networkx as nx

from src.communities.louvain import get_prominent_communities


def test_community_graph_serializes_numeric_metric_weight():
    graph = nx.MultiDiGraph()
    graph.add_edge("author", "spreader", shared_post=7)

    frame = get_prominent_communities([{"author", "spreader"}], graph, "shared_post")

    assert frame.loc[0, "weight"] == 7.0
    assert frame.loc[0, "direction"] == "Directed"
