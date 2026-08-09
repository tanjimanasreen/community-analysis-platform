import numpy as np
import pandas as pd

from src.themes.community_transition import get_community_transition

from src.themes.community_paths import (
    build_community_path_artifact,
    build_membership_mobility_artifact,
    build_path_theme_similarity_artifact,
)


class FakeEmbedder:
    def encode(self, sentences):
        vectors = {
            "['alpha']": [1.0, 0.0],
            "['beta']": [1.0, 0.0],
            "['gamma']": [0.0, 1.0],
            "['a']": [1.0, 0.0],
            "['b']": [1.0, 0.0],
            "['c']": [0.0, 1.0],
        }
        return [vectors.get(str(sentence), [0.5, 0.5]) for sentence in sentences]


def _transition(
    start,
    end,
    start_members,
    end_members,
    *,
    score=0.6,
    start_theme="['alpha']",
    end_theme="['beta']",
):
    start_month = start.split("_", 1)[0]
    end_month = end.split("_", 1)[0]
    common = sorted(set(start_members) & set(end_members))
    return {
        "start_month": start_month,
        "end_month": end_month,
        "start_month_community": start,
        "end_month_community": end,
        "jaccard_score": score,
        "common_members": str(common),
        "uncommon_members": str(sorted(set(start_members) ^ set(end_members))),
        "start_month_members": str(start_members),
        "total_start_month_members": len(start_members),
        "end_month_members": str(end_members),
        "total_end_month_members": len(end_members),
        "start_month_absolute_theme": start_theme,
        "end_month_absolute_theme": end_theme,
        "start_month_weighted_theme": start_theme,
        "end_month_weighted_theme": end_theme,
        "start_month_general_theme": start_theme,
        "end_month_general_theme": end_theme,
    }


def test_branching_transition_graph_materializes_distinct_dfs_paths():
    transitions = pd.DataFrame(
        [
            _transition(
                "january_1", "february_2", ["a", "b"], ["a", "b", "c"], score=0.66
            ),
            _transition(
                "february_2", "march_4", ["a", "b", "c"], ["a", "b"], score=0.66
            ),
            _transition(
                "february_2", "march_5", ["a", "b", "c"], ["b", "c"], score=0.66
            ),
            _transition("january_8", "february_9", ["x", "y"], ["x", "y"], score=1.0),
            _transition("february_9", "march_10", ["x", "y"], ["x", "y"], score=1.0),
        ]
    )

    paths = build_community_path_artifact(transitions)

    grouped = [
        group.sort_values("step_index")["community_key"].tolist()
        for _, group in paths.groupby("path_id", sort=False)
    ]
    assert ["january_1", "february_2", "march_4"] in grouped
    assert ["january_1", "february_2", "march_5"] in grouped
    assert ["january_8", "february_9", "march_10"] in grouped
    assert len(grouped) == 3
    assert sorted(paths["display_order"].unique().tolist()) == [1, 2, 3]


def test_membership_artifact_preserves_reappearing_semantics():
    transitions = pd.DataFrame(
        [
            _transition("january_1", "february_2", ["A", "B", "C"], ["A", "B", "D"]),
            _transition("february_2", "march_3", ["A", "B", "D"], ["A", "C", "D"]),
        ]
    )
    paths = build_community_path_artifact(transitions)

    mobility = build_membership_mobility_artifact(paths)
    march = mobility[mobility["month"] == "march"].iloc[0]

    assert march["existing_count"] == 2
    assert march["new_count"] == 1
    assert march["lost_count"] == 1
    assert march["reappearing_count"] == 1
    assert '"C"' in march["reappearing_members"]


def test_path_theme_similarity_is_path_scoped_and_uses_raw_theme_strings():
    transitions = pd.DataFrame(
        [
            _transition(
                "january_1",
                "february_2",
                ["A"],
                ["A"],
                start_theme="['a']",
                end_theme="['b']",
            ),
            _transition(
                "february_2",
                "march_3",
                ["A"],
                ["A"],
                start_theme="['b']",
                end_theme="['c']",
            ),
        ]
    )
    paths = build_community_path_artifact(transitions)

    similarity = build_path_theme_similarity_artifact(
        paths,
        model=FakeEmbedder(),
        model_name="paraphrase-MiniLM-L6-v2",
        embedding_provider="mock",
        embedding_model="sentence-transformers/paraphrase-MiniLM-L6-v2",
        embedding_model_revision="fixture",
    )

    general = similarity[similarity["theme_type"] == "general"]
    assert len(general) == 6
    jan_feb = general[
        (general["left_month"] == "january") & (general["right_month"] == "february")
    ].iloc[0]
    jan_mar = general[
        (general["left_month"] == "january") & (general["right_month"] == "march")
    ].iloc[0]
    assert jan_feb["cosine_similarity"] == 1.0
    assert jan_mar["cosine_similarity"] == 0.0
    assert jan_feb["left_theme"] == "['a']"


def test_numpy_backed_transition_members_survive_path_and_mobility_artifacts():
    january = pd.DataFrame(
        {
            "absolute_community": [46],
            "members": [[np.int64(1), np.int64(2), np.int64(3)]],
            "absolute_theme_names": ["ThemeA"],
            "weighted_theme_names": ["ThemeA"],
            "general_theme_names": ["ThemeA"],
        }
    )
    february = pd.DataFrame(
        {
            "absolute_community": [74],
            "members": [[np.int64(1), np.int64(2), np.int64(4)]],
            "absolute_theme_names": ["ThemeA"],
            "weighted_theme_names": ["ThemeA"],
            "general_theme_names": ["ThemeA"],
        }
    )
    march = pd.DataFrame(
        {
            "absolute_community": [37],
            "members": [[np.int64(1), np.int64(2), np.int64(3)]],
            "absolute_theme_names": ["ThemeA"],
            "weighted_theme_names": ["ThemeA"],
            "general_theme_names": ["ThemeA"],
        }
    )

    transitions = get_community_transition(
        {"01": january, "02": february, "03": march},
        "mixed",
        threshold=0.0,
    )
    paths = build_community_path_artifact(transitions)
    mobility = build_membership_mobility_artifact(paths)

    assert paths["community_id"].tolist() == ["46", "74", "37"]
    assert paths["member_count"].tolist() == [3, 3, 3]
    assert paths["retained_count"].tolist()[1:] == [2.0, 2.0]

    january_row = mobility[mobility["month"] == "01"].iloc[0]
    february_row = mobility[mobility["month"] == "02"].iloc[0]
    march_row = mobility[mobility["month"] == "03"].iloc[0]

    assert january_row["existing_count"] == 3
    assert february_row["existing_count"] == 2
    assert february_row["new_count"] == 1
    assert february_row["lost_count"] == 1
    assert february_row["reappearing_count"] == 0
    assert march_row["existing_count"] == 2
    assert march_row["new_count"] == 1
    assert march_row["lost_count"] == 1
    assert march_row["reappearing_count"] == 1
    assert "3" in march_row["reappearing_members"]
