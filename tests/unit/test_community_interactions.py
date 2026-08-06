import networkx as nx

from src.communities.interactions import (
    COMMUNITY_INTERACTION_COLUMNS,
    build_prominent_community_interactions,
)


def _absolute_graph():
    graph = nx.MultiDiGraph()
    graph.add_edge("a", "b", shared_post=9)
    graph.add_edge("a", "c", shared_post=5)
    graph.add_edge("b", "c", shared_post=3)
    graph.add_edge("c", "a", shared_post=2)
    graph.add_edge("d", "outside", shared_post=7)
    return graph


def test_aggregates_directed_if_interactions_between_prominent_communities():
    result = build_prominent_community_interactions(
        _absolute_graph(),
        [{"a", "b"}, {"c", "d"}],
        weight_attribute="shared_post",
    )

    assert result.to_dict(orient="records") == [
        {
            "source_community_id": "0",
            "target_community_id": "1",
            "user_pair_count": 2,
            "interaction_count": 8,
            "total_weight": 8.0,
            "source_user_count": 2,
            "target_user_count": 1,
        },
        {
            "source_community_id": "1",
            "target_community_id": "0",
            "user_pair_count": 1,
            "interaction_count": 2,
            "total_weight": 2.0,
            "source_user_count": 1,
            "target_user_count": 1,
        },
    ]


def test_weighted_artifact_preserves_shared_post_provenance():
    weighted = nx.MultiDiGraph()
    weighted.add_edge("a", "b", weighted_post=0.9)
    weighted.add_edge("a", "c", weighted_post=0.5)
    weighted.add_edge("b", "c", weighted_post=0.25)
    weighted.add_edge("c", "a", weighted_post=0.2)

    result = build_prominent_community_interactions(
        weighted,
        [{"a", "b"}, {"c"}],
        weight_attribute="weighted_post",
        interaction_graph=_absolute_graph(),
    )

    assert result.loc[0, "interaction_count"] == 8
    assert result.loc[0, "total_weight"] == 0.75
    assert result.loc[1, "interaction_count"] == 2
    assert result.loc[1, "total_weight"] == 0.2


def test_excludes_same_community_and_non_prominent_endpoints():
    result = build_prominent_community_interactions(
        _absolute_graph(),
        [{"a", "b"}],
        weight_attribute="shared_post",
    )

    assert result.empty
    assert list(result.columns) == COMMUNITY_INTERACTION_COLUMNS
    assert str(result["user_pair_count"].dtype) == "int64"


def test_parallel_user_edges_count_as_one_distinct_pair_but_preserve_weight():
    graph = nx.MultiDiGraph()
    graph.add_edge("a", "c", shared_post=2)
    graph.add_edge("a", "c", shared_post=3)

    result = build_prominent_community_interactions(
        graph,
        [{"a"}, {"c"}],
        weight_attribute="shared_post",
    )

    assert result.to_dict(orient="records") == [
        {
            "source_community_id": "0",
            "target_community_id": "1",
            "user_pair_count": 1,
            "interaction_count": 5,
            "total_weight": 5.0,
            "source_user_count": 1,
            "target_user_count": 1,
        }
    ]
