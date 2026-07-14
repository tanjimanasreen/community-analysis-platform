import pytest
import networkx as nx
import pandas as pd
from src.communities.louvain import get_louvain_community, detect_prominent_communities, get_prominent_communities

def test_louvain_community_defaults():
    G = nx.Graph()
    G.add_edge(1, 2, weight=1.0)
    G.add_edge(2, 3, weight=1.0)
    G.add_edge(4, 5, weight=1.0)

    communities, partition = get_louvain_community(G, 'weight')
    assert len(communities) == 2

def test_detect_prominent_communities():
    communities = [{1, 2, 3}, {4, 5}, {6}]
    prominent = detect_prominent_communities(communities, min_members=2)
    assert len(prominent) == 2
    assert {6} not in prominent

def test_get_prominent_communities_df():
    G = nx.DiGraph()
    G.add_edge(1, 2, weight=1.5)
    G.add_edge(2, 3, weight=2.0)
    prominent = [{1, 2, 3}]

    df = get_prominent_communities(prominent, G)
    assert len(df) == 2
    assert 'community_number' in df.columns
    assert 'source' in df.columns
    assert 'weight' in df.columns
    assert df['community_number'].iloc[0] == 0
