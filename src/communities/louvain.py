import networkx as nx
import pandas as pd

from src.config.defaults import DEFAULT_CONFIG


def get_louvain_community(
    G,
    weight,
    *,
    resolution: float = DEFAULT_CONFIG.louvain.resolution,
    seed: int = DEFAULT_CONFIG.louvain.seed,
):
    """Detect communities with configurable, thesis-preserving defaults."""
    communities = list(
        nx.community.louvain_communities(
            G,
            weight=weight,
            resolution=float(resolution),
            seed=int(seed),
        )
    )
    partition = {
        node: idx for idx, community in enumerate(communities) for node in community
    }

    return communities, partition


def detect_prominent_communities(communities, min_members):
    """
    Filters communities to only include those with at least min_members.
    """
    prominent_communities = [
        community for community in communities if len(community) >= min_members
    ]
    return prominent_communities


def get_prominent_communities(prominent_communities, G, weight_attribute=None):
    """Return frontend-ready prominent-community edges.

    NetworkX returns the complete edge-attribute mapping as ``data``.  The
    legacy implementation wrote that mapping into the public ``weight`` column,
    which made Parquet/API consumers see non-numeric values.  This function
    preserves the graph and community behavior while serializing the selected
    IF/WIF edge weight as a number.
    """
    community_number = 0
    community_data = {
        "source": [],
        "target": [],
        "community_number": [],
        "direction": [],
        "weight": [],
    }

    for community in prominent_communities:
        subgraph = G.subgraph(community)
        for source, target, data in subgraph.edges(data=True):
            if weight_attribute is not None:
                raw_weight = data.get(weight_attribute, 0.0)
            elif "weight" in data:
                raw_weight = data["weight"]
            elif len(data) == 1:
                raw_weight = next(iter(data.values()))
            else:
                raw_weight = 0.0

            community_data["source"].append(source)
            community_data["target"].append(target)
            community_data["community_number"].append(community_number)
            community_data["direction"].append(
                "Directed" if G.is_directed() else "Undirected"
            )
            community_data["weight"].append(float(raw_weight))

        community_number += 1

    return pd.DataFrame(community_data)
