import ast

import numpy as np
import pandas as pd
import pytest
from src.themes.transitions import get_community_transition


def test_community_transition_expected_columns():
    df1 = pd.DataFrame(
        {
            "absolute_community": [0],
            "members": [[1, 2, 3]],
            "absolute_theme_names": ["ThemeA"],
            "weighted_theme_names": ["ThemeB"],
            "general_theme_names": ["ThemeC"],
        }
    )

    df2 = pd.DataFrame(
        {
            "absolute_community": [0],
            "members": [[1, 2, 3]],
            "absolute_theme_names": ["ThemeA"],
            "weighted_theme_names": ["ThemeB"],
            "general_theme_names": ["ThemeC"],
        }
    )

    theme_dict = {"month1": df1, "month2": df2}
    result_df = get_community_transition(theme_dict, "mixed")

    assert "start_month_community" in result_df.columns
    assert "end_month_community" in result_df.columns
    assert "jaccard_score" in result_df.columns


def test_community_transition_thresholds():
    df1 = pd.DataFrame(
        {
            "absolute_community": [0, 1],
            "members": [[1, 2, 3], [4, 5, 6]],
            "absolute_theme_names": ["ThemeA", "ThemeX"],
            "weighted_theme_names": ["ThemeB", "ThemeY"],
            "general_theme_names": ["ThemeC", "ThemeZ"],
        }
    )
    # Month 2: Comm 0 is completely same (1.0). Comm 1 has 50% overlap ([4, 5, 7, 8] w/ [4, 5, 6] -> 2/5 = 0.4)
    df2 = pd.DataFrame(
        {
            "absolute_community": [0, 1],
            "members": [[1, 2, 3], [4, 5, 7, 8]],
            "absolute_theme_names": ["ThemeA", "ThemeX"],
            "weighted_theme_names": ["ThemeB", "ThemeY"],
            "general_theme_names": ["ThemeC", "ThemeZ"],
        }
    )

    theme_dict = {"month1": df1, "month2": df2}
    # With threshold 0.5, the 0.4 transition should be dropped
    result_df = get_community_transition(theme_dict, "mixed")

    # Only the 1.0 jaccard transition should remain
    assert len(result_df) == 1
    assert result_df.iloc[0]["start_month_community"] == "month1_0"
    assert result_df.iloc[0]["end_month_community"] == "month2_0"
    assert result_df.iloc[0]["jaccard_score"] == 1.0


def test_reply_zero_threshold_excludes_zero_overlap_and_accepts_positive_candidates():
    df1 = pd.DataFrame(
        {
            "absolute_community": [0, 1],
            "members": [[1, 2], [10, 11]],
            "absolute_theme_names": ["ThemeA", "ThemeB"],
            "weighted_theme_names": ["ThemeC", "ThemeD"],
            "general_theme_names": ["ThemeE", "ThemeF"],
        }
    )
    df2 = pd.DataFrame(
        {
            "absolute_community": [0, 1, 2],
            "members": [[2, 3], [11, 12], [20, 21]],
            "absolute_theme_names": ["ThemeA", "ThemeB", "ThemeG"],
            "weighted_theme_names": ["ThemeC", "ThemeD", "ThemeH"],
            "general_theme_names": ["ThemeE", "ThemeF", "ThemeI"],
        }
    )

    result = get_community_transition({"month1": df1, "month2": df2}, "reply")

    assert list(
        zip(
            result["start_month_community"],
            result["end_month_community"],
            result["jaccard_score"],
            strict=True,
        )
    ) == [
        ("month1_0", "month2_0", pytest.approx(1 / 3)),
        ("month1_1", "month2_1", pytest.approx(1 / 3)),
    ]
    assert "month2_2" not in set(result["end_month_community"])


def test_community_transition_empty_input():
    result_df = get_community_transition({}, "mixed")
    assert isinstance(result_df, pd.DataFrame)
    assert len(result_df) == 0


def test_transition_serialization_normalizes_numpy_scalar_members():
    df1 = pd.DataFrame(
        {
            "absolute_community": [46],
            "members": [[np.int64(1), np.int64(2), np.str_("u3")]],
            "absolute_theme_names": ["ThemeA"],
            "weighted_theme_names": ["ThemeB"],
            "general_theme_names": ["ThemeC"],
        }
    )
    df2 = pd.DataFrame(
        {
            "absolute_community": [74],
            "members": [[np.int64(1), np.int64(2), np.str_("u4")]],
            "absolute_theme_names": ["ThemeA"],
            "weighted_theme_names": ["ThemeB"],
            "general_theme_names": ["ThemeC"],
        }
    )

    result = get_community_transition({"01": df1, "02": df2}, "mixed", threshold=0.0)
    row = result.iloc[0]

    assert row["jaccard_score"] == 0.5
    assert ast.literal_eval(row["start_month_members"]) == [1, 2, "u3"]
    assert ast.literal_eval(row["end_month_members"]) == [1, 2, "u4"]
    assert ast.literal_eval(row["common_members"]) == [1, 2]
    assert ast.literal_eval(row["uncommon_members"]) == ["u3", "u4"]
    assert "np." not in row["start_month_members"]
    assert "np." not in row["end_month_members"]
    assert "np." not in row["common_members"]
    assert "np." not in row["uncommon_members"]
