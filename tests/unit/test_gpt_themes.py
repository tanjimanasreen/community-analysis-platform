import pytest
import pandas as pd
from unittest.mock import MagicMock
from src.themes.gpt_themes import (
    call_gpt_theme_api,
    map_theme,
    extract_unique_keywords,
    generate_gpt_theme,
)


def test_map_theme():
    reference_df = pd.DataFrame(
        {
            "absolute_community": [[0, 1], [2]],
            "absolute_theme_gpt": ["ThemeA", "ThemeB"],
            "absolute_theme_names": ["NameA", "NameB"],
        }
    )

    result = map_theme(
        0,
        reference_df,
        "absolute_community",
        "absolute_theme_gpt",
        "absolute_theme_names",
    )
    assert result[0] == "ThemeA"
    assert result[1] == "NameA"

    result_none = map_theme(
        5,
        reference_df,
        "absolute_community",
        "absolute_theme_gpt",
        "absolute_theme_names",
    )
    assert result_none[0] is None


def test_extract_unique_keywords():
    month_df = pd.DataFrame(
        {
            "absolute_unigram_keywords": [["apple", "banana"]],
            "absolute_bigram_keywords": [["big apple"]],
            "weighted_unigram_keywords": [["orange"]],
            "weighted_bigram_keywords": [["big orange"]],
        }
    )

    df = extract_unique_keywords(month_df)

    assert "apple,banana,bigapple,orange,bigorange" in df["all_keywords"].iloc[0]
    assert "apple,banana,bigapple" in df["absolute_keywords"].iloc[0]
    assert "orange,bigorange" in df["weighted_keywords"].iloc[0]


def test_generate_gpt_theme():
    month_df = pd.DataFrame(
        {
            "absolute_community": [0, 1],
            "weighted_community": [0, 1],
            "absolute_unigram_keywords": [["apple"], ["banana"]],
            "absolute_bigram_keywords": [["big apple"], ["big banana"]],
            "weighted_unigram_keywords": [["orange"], ["grape"]],
            "weighted_bigram_keywords": [["big orange"], ["big grape"]],
        }
    )

    from unittest.mock import patch

    with patch("src.providers.factory.build_theme_provider") as mock_build:
        mock_provider = MagicMock()
        mock_provider.generate_theme.return_value = {"Theme 1": ["kw1", "kw2"]}
        mock_build.return_value = mock_provider

        df = generate_gpt_theme(month_df)

        assert "absolute_theme_gpt" in df.columns
        assert "weighted_theme_gpt" in df.columns
        assert "general_theme_gpt" in df.columns

        assert "Theme 1" in df["absolute_theme_names"].iloc[0]
        assert mock_provider.generate_theme.call_count > 0
