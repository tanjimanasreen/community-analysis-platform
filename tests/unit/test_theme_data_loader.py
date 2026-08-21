import pandas as pd

from src.themes.data_loader import load_prepare_data


def test_load_prepare_data_sorts_months_and_parses_keyword_lists(tmp_path):
    columns = {
        "members": ["[1, 2]"],
        "absolute_community": [0],
        "weighted_community": [1],
        "absolute_unigram_keywords": ["['apple', 'banana']"],
        "absolute_bigram_keywords": ["['big apple']"],
        "weighted_unigram_keywords": ["orange,grape"],
        "weighted_bigram_keywords": [""],
    }
    pd.DataFrame(columns).to_parquet(tmp_path / "february_2017.parquet", index=False)
    pd.DataFrame(columns).to_parquet(tmp_path / "january_2017.parquet", index=False)

    data = load_prepare_data(str(tmp_path), "2017")

    assert list(data.keys()) == ["january", "february"]
    assert data["january"]["absolute_unigram_keywords"].iloc[0] == ["apple", "banana"]
    assert data["january"]["weighted_unigram_keywords"].iloc[0] == ["orange", "grape"]
    assert data["january"]["weighted_bigram_keywords"].iloc[0] == []
