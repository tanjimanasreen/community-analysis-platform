import pandas as pd

from src.themes.sankey_paths import find_all_sankey_paths, get_path_info


def test_get_path_info_and_find_all_sankey_paths():
    matched_df = pd.DataFrame(
        {
            "start_month_community": ["january_0", "february_0"],
            "end_month_community": ["february_0", "march_1"],
            "jaccard_score": [0.75, 0.5],
        }
    )

    source, target, score, communities = get_path_info(matched_df)
    paths = find_all_sankey_paths(source, target, communities)

    assert score == [0.75, 0.5]
    assert paths == [["january_0", "february_0", "march_1"]]
