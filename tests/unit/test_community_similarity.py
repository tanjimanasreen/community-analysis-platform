import pytest
import pandas as pd
from src.communities.similarity import get_community_members, jaccard_similarity, find_matching_communities

def test_jaccard_similarity():
    assert jaccard_similarity([1, 2, 3], [1, 2, 3]) == 1.0
    assert jaccard_similarity([1, 2], [3, 4]) == 0.0
    assert jaccard_similarity([1, 2, 3], [2, 3, 4]) == 0.5

def test_get_community_members():
    df = pd.DataFrame({
        'community_number': [0, 0, 1],
        'source': ['a', 'b', 'd'],
        'target': ['b', 'c', 'e']
    })
    members_df = get_community_members(df)

    assert len(members_df) == 2
    # Community 0 should have a, b, c
    assert set(members_df.iloc[0]['members']) == {'a', 'b', 'c'}
    # Community 1 should have d, e
    assert set(members_df.iloc[1]['members']) == {'d', 'e'}

def test_find_matching_communities():
    abs_df = pd.DataFrame({
        'community_number': [0, 1],
        'source': ['a', 'x'],
        'target': ['b', 'y']
    })
    # Community 0 is exactly {a, b}
    # Community 1 is exactly {x, y}

    per_df = pd.DataFrame({
        'community_number': [0, 1, 2],
        'source': ['a', 'x', 'm'],
        'target': ['b', 'z', 'n']
    })
    # Community 0 is exactly {a, b} -> MATCHES abs 0
    # Community 1 is {x, z} -> PARTIAL MATCH with abs 1 ({x, y} vs {x, z}, J=1/3)
    # Community 2 is {m, n} -> UNMATCHED

    matched, partial, unmatched_abs, unmatched_per = find_matching_communities(abs_df, per_df)

    assert len(matched) == 1
    assert matched['abs_community'].iloc[0] == 0
    assert matched['per_community'].iloc[0] == 0

    assert len(partial) == 1
    assert partial['abs_community'].iloc[0] == 1
    assert partial['per_community'].iloc[0] == 1

    assert len(unmatched_abs) == 0
    assert len(unmatched_per) == 1
    assert unmatched_per['per_community'].iloc[0] == 2
