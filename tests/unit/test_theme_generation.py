import pytest
import pandas as pd
from unittest.mock import MagicMock
from src.themes.theme_generation import (
    call_gpt_theme_api,
    extract_unique_keywords,
    generate_gpt_theme,
)


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

    assert df["all_keywords"].iloc[0] == (
        "apple",
        "banana",
        "big apple",
        "orange",
        "big orange",
    )
    assert df["absolute_keywords"].iloc[0] == (
        "apple",
        "banana",
        "big apple",
    )
    assert df["weighted_keywords"].iloc[0] == ("orange", "big orange")


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
