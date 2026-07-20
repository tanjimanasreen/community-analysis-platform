import pytest
import pandas as pd
from src.themes.transitions import get_community_transition

def test_community_transition_expected_columns():
    df1 = pd.DataFrame({
        "absolute_community": [0],
        "members": [[1, 2, 3]],
        "absolute_theme_names": ["ThemeA"],
        "weighted_theme_names": ["ThemeB"],
        "general_theme_names": ["ThemeC"],
    })

    df2 = pd.DataFrame({
        "absolute_community": [0],
        "members": [[1, 2, 3]],
        "absolute_theme_names": ["ThemeA"],
        "weighted_theme_names": ["ThemeB"],
        "general_theme_names": ["ThemeC"],
    })
    
    theme_dict = {"month1": df1, "month2": df2}
    result_df = get_community_transition(theme_dict, "mixed")
    
    assert "start_month_community" in result_df.columns
    assert "end_month_community" in result_df.columns
    assert "jaccard_score" in result_df.columns

def test_community_transition_thresholds():
    df1 = pd.DataFrame({
        "absolute_community": [0, 1],
        "members": [[1, 2, 3], [4, 5, 6]],
        "absolute_theme_names": ["ThemeA", "ThemeX"],
        "weighted_theme_names": ["ThemeB", "ThemeY"],
        "general_theme_names": ["ThemeC", "ThemeZ"],
    })
    # Month 2: Comm 0 is completely same (1.0). Comm 1 has 50% overlap ([4, 5, 7, 8] w/ [4, 5, 6] -> 2/5 = 0.4)
    df2 = pd.DataFrame({
        "absolute_community": [0, 1],
        "members": [[1, 2, 3], [4, 5, 7, 8]],
        "absolute_theme_names": ["ThemeA", "ThemeX"],
        "weighted_theme_names": ["ThemeB", "ThemeY"],
        "general_theme_names": ["ThemeC", "ThemeZ"],
    })
    
    theme_dict = {"month1": df1, "month2": df2}
    # With threshold 0.5, the 0.4 transition should be dropped
    result_df = get_community_transition(theme_dict, "mixed")
    
    # Only the 1.0 jaccard transition should remain
    assert len(result_df) == 1
    assert result_df.iloc[0]["start_month_community"] == "month1_0"
    assert result_df.iloc[0]["end_month_community"] == "month2_0"
    assert result_df.iloc[0]["jaccard_score"] == 1.0

def test_community_transition_empty_input():
    result_df = get_community_transition({}, "mixed")
    assert isinstance(result_df, pd.DataFrame)
    assert len(result_df) == 0
