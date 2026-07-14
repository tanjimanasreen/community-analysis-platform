import pytest
import pandas as pd
from src.themes.transitions import jaccard_similarity, get_community_transition, build_graph

def test_jaccard_similarity():
    assert jaccard_similarity([1, 2, 3], [2, 3, 4]) == 0.5
    assert jaccard_similarity([1], [2]) == 0.0

def test_get_community_transition():
    # month1 has community 0 with members 1, 2, 3
    # month2 has community 0 with members 1, 2, 4 (2/4 = 0.5 jaccard)
    # month2 has community 1 with members 5, 6

    df1 = pd.DataFrame({
        'absolute_community': [0],
        'members': [[1, 2, 3]],
        'absolute_theme_names': ['ThemeA'],
        'weighted_theme_names': ['ThemeB'],
        'general_theme_names': ['ThemeC']
    })

    df2 = pd.DataFrame({
        'absolute_community': [0, 1],
        'members': [[1, 2, 4], [5, 6]],
        'absolute_theme_names': ['ThemeA', 'ThemeD'],
        'weighted_theme_names': ['ThemeB', 'ThemeE'],
        'general_theme_names': ['ThemeC', 'ThemeF']
    })

    theme_dict = {'january': df1, 'february': df2}

    # Using 'mixed' threshold is 0.5, so 0.5 is NOT > 0.5, it is equal to 0.5.
    # Wait, the threshold is 0.5 in code: `if threshold < jscore <= 1:`. 0.5 is not > 0.5.
    # Let's adjust members to [1, 2, 3] and [1, 2, 3, 4] -> J = 3/4 = 0.75
    df2.at[0, 'members'] = [1, 2, 3, 4]

    matched_df = get_community_transition(theme_dict, 'mixed')

    assert len(matched_df) == 1
    assert matched_df['start_month_community'].iloc[0] == 'january_0'
    assert matched_df['end_month_community'].iloc[0] == 'february_0'
    assert matched_df['jaccard_score'].iloc[0] == 0.75

def test_build_graph():
    source = [1, 2, 2]
    target = [2, 3, 4]

    graph, starts, ends = build_graph(source, target)
    assert 1 in starts
    assert 3 in ends
    assert 4 in ends
    assert len(graph[2]) == 2
