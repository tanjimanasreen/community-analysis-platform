from __future__ import annotations

from collections import defaultdict
from typing import Hashable, Iterable

import networkx as nx
import pandas as pd

COMMUNITY_INTERACTION_COLUMNS = [
    "source_community_id",
    "target_community_id",
    "user_pair_count",
    "interaction_count",
    "total_weight",
    "source_user_count",
    "target_user_count",
]


def build_prominent_community_interactions(
    graph: nx.Graph,
    prominent_communities: Iterable[set[Hashable]],
    *,
    weight_attribute: str,
    interaction_graph: nx.Graph | None = None,
    interaction_attribute: str = "shared_post",
) -> pd.DataFrame:
    """Aggregate directed interactions between prominent communities.

    Community IDs are the metric-local enumeration already used by
    ``get_prominent_communities``. The selected metric is aggregated without
    redefining it. ``interaction_count`` always preserves the existing
    ``shared_post`` count for provenance, including in the weighted artifact.
    """

    membership: dict[Hashable, str] = {}
    for community_id, members in enumerate(prominent_communities):
        for member in members:
            membership[member] = str(community_id)

    if not membership:
        return _empty_frame()

    selected_pair_weights = _directed_pair_weights(graph, weight_attribute)
    interaction_pair_weights = _directed_pair_weights(
        interaction_graph if interaction_graph is not None else graph,
        interaction_attribute,
    )

    aggregates: dict[tuple[str, str], dict[str, object]] = {}
    for (source, target), selected_weight in selected_pair_weights.items():
        source_community = membership.get(source)
        target_community = membership.get(target)
        if (
            source_community is None
            or target_community is None
            or source_community == target_community
        ):
            continue

        key = (source_community, target_community)
        aggregate = aggregates.setdefault(
            key,
            {
                "user_pairs": set(),
                "source_users": set(),
                "target_users": set(),
                "interaction_count": 0.0,
                "total_weight": 0.0,
            },
        )
        aggregate["user_pairs"].add((source, target))
        aggregate["source_users"].add(source)
        aggregate["target_users"].add(target)
        aggregate["interaction_count"] += interaction_pair_weights.get(
            (source, target), 0.0
        )
        aggregate["total_weight"] += selected_weight

    rows = []
    for (source_community, target_community), aggregate in aggregates.items():
        rows.append(
            {
                "source_community_id": source_community,
                "target_community_id": target_community,
                "user_pair_count": len(aggregate["user_pairs"]),
                "interaction_count": int(round(aggregate["interaction_count"])),
                "total_weight": float(aggregate["total_weight"]),
                "source_user_count": len(aggregate["source_users"]),
                "target_user_count": len(aggregate["target_users"]),
            }
        )

    if not rows:
        return _empty_frame()

    result = pd.DataFrame(rows, columns=COMMUNITY_INTERACTION_COLUMNS)
    result["_source_sort"] = result["source_community_id"].map(_community_sort_key)
    result["_target_sort"] = result["target_community_id"].map(_community_sort_key)
    result = result.sort_values(["_source_sort", "_target_sort"], kind="stable").drop(
        columns=["_source_sort", "_target_sort"]
    )
    return result.reset_index(drop=True)


def _directed_pair_weights(
    graph: nx.Graph,
    weight_attribute: str,
) -> dict[tuple[Hashable, Hashable], float]:
    weights: defaultdict[tuple[Hashable, Hashable], float] = defaultdict(float)
    for source, target, data in graph.edges(data=True):
        raw_weight = data.get(weight_attribute, 0.0)
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            weight = 0.0
        weights[(source, target)] += weight
    return dict(weights)


def _community_sort_key(value: str) -> tuple[int, int | str]:
    text = str(value)
    if text.lstrip("-").isdigit():
        return (0, int(text))
    return (1, text)


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_community_id": pd.Series(dtype="string"),
            "target_community_id": pd.Series(dtype="string"),
            "user_pair_count": pd.Series(dtype="int64"),
            "interaction_count": pd.Series(dtype="int64"),
            "total_weight": pd.Series(dtype="float64"),
            "source_user_count": pd.Series(dtype="int64"),
            "target_user_count": pd.Series(dtype="int64"),
        },
        columns=COMMUNITY_INTERACTION_COLUMNS,
    )
