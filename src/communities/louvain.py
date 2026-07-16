import networkx as nx
import pandas as pd


def get_louvain_community(G, weight):
    """
    Detects communities using the Louvain method with default resolution=1 and seed=123.
    """
    communities = list(
        nx.community.louvain_communities(G, weight=weight, resolution=1, seed=123)
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


def get_prominent_communities(prominent_communities, G):
    """
    Returns a DataFrame containing the edges and attributes of the prominent communities.
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
        edges = subgraph.edges(data=True)

        for edge in edges:
            source, target, data = edge
            direction = "Directed" if G.has_edge(source, target) else "Undirected"

            community_data["source"].append(source)
            community_data["target"].append(target)
            community_data["community_number"].append(community_number)
            community_data["direction"].append(direction)
            community_data["weight"].append(data)

        community_number += 1

    df_community = pd.DataFrame(community_data)
    return df_community
