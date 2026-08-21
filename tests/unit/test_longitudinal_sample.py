import csv
import json
from pathlib import Path

import pandas as pd

from src.ingestion.network_data_extractor import create_network_df, get_creator_spreader
from src.network.follower_followee import get_follower_followee_network
from src.pipelines.theme_pipeline import run_theme_pipeline_from_bundle
from src.providers.mock import MockProvider
from src.themes.theme_inputs import load_theme_inputs, save_theme_inputs
from src.topics.topic_inputs import load_topic_inputs, save_topic_inputs

LONGITUDINAL_FIXTURES = [
    Path("tests/fixtures/longitudinal/twitter_reply_03_2017.csv"),
    Path("tests/fixtures/longitudinal/twitter_reply_04_2017.csv"),
]

MATCHED_LDA_COLUMNS = [
    "absolute_community",
    "absolute_unigram_topic",
    "absolute_unigram_keywords",
    "weighted_community",
    "weighted_unigram_topic",
    "weighted_unigram_keywords",
    "absolute_bigram_topic",
    "absolute_bigram_keywords",
    "weighted_bigram_topic",
    "weighted_bigram_keywords",
    "members",
]
THEMED_COLUMNS = MATCHED_LDA_COLUMNS + [
    "all_keywords",
    "absolute_keywords",
    "weighted_keywords",
    "general_theme_gpt",
    "general_theme_names",
    "absolute_theme_gpt",
    "absolute_theme_names",
    "weighted_theme_gpt",
    "weighted_theme_names",
]


def _community_messages(month):
    return pd.DataFrame(
        {
            "community_number": [0],
            "messages": [[f"{month} apple orange discussion"]],
            "messages_ids": [[f"{month}_1"]],
            "total_messages": [1],
        }
    )


def _matched_communities():
    return pd.DataFrame(
        {
            "abs_community": [0],
            "per_community": [0],
            "jaccard_score": [1.0],
            "members": [[1, 2, 3]],
        }
    )


def _partial_matched():
    return pd.DataFrame(
        columns=[
            "abs_community",
            "absolute_members",
            "per_community",
            "weighted_members",
            "jaccard_score",
            "common_members",
            "uncommon_members",
        ]
    )


def _matched_lda_frame(members=None):
    return pd.DataFrame(
        {
            "absolute_community": [0],
            "absolute_unigram_topic": [0],
            "absolute_unigram_keywords": [["apple"]],
            "weighted_community": [0],
            "weighted_unigram_topic": [0],
            "weighted_unigram_keywords": [["orange"]],
            "absolute_bigram_topic": [0],
            "absolute_bigram_keywords": [["big apple"]],
            "weighted_bigram_topic": [0],
            "weighted_bigram_keywords": [["big orange"]],
            "members": [members or [1, 2, 3]],
        }
    )


def test_longitudinal_topic_inputs_save_load_two_months(tmp_path):
    for month in ("03", "04"):
        save_topic_inputs(
            absolute_community_messages=_community_messages(month),
            weighted_community_messages=_community_messages(month),
            matched_communities=_matched_communities(),
            partial_matched_communities=_partial_matched(),
            output_base_path=str(tmp_path),
            data_type="twitter",
            content_type="reply",
            month=month,
            year="2017",
        )

    march = load_topic_inputs(
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        month="03",
        year="2017",
    )
    april = load_topic_inputs(
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        month="04",
        year="2017",
    )

    assert march.absolute_community_messages.loc[0, "messages"] == [
        "03 apple orange discussion"
    ]
    assert april.matched_communities.loc[0, "members"] == [1, 2, 3]


def test_longitudinal_theme_manifest_accumulates_two_months_with_hashes(tmp_path):
    for month in ("03", "04"):
        path = tmp_path / f"{month}_2017.parquet"
        _matched_lda_frame().to_parquet(path, index=False)
        save_theme_inputs(
            matched_lda_csv=path,
            output_base_path=str(tmp_path),
            data_type="twitter",
            content_type="reply",
            month=month,
            year="2017",
        )

    bundle = load_theme_inputs(
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        year="2017",
    )

    assert bundle.manifest["months"] == ["03", "04"]
    assert set(bundle.manifest["filenames"].values()) == {
        "03_2017.parquet",
        "04_2017.parquet",
    }
    assert all(len(value) == 64 for value in bundle.manifest["hashes"].values())
    assert set(bundle.monthly_data) == {"03", "04"}


def test_longitudinal_theme_inputs_produce_transition(tmp_path):
    for month, members in [("03", [1, 2, 3]), ("04", [1, 2, 3, 4])]:
        path = tmp_path / f"{month}_2017.parquet"
        _matched_lda_frame(members).to_parquet(path, index=False)
        save_theme_inputs(
            matched_lda_csv=path,
            output_base_path=str(tmp_path),
            data_type="twitter",
            content_type="reply",
            month=month,
            year="2017",
        )

    bundle = load_theme_inputs(
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        year="2017",
    )
    transitions = run_theme_pipeline_from_bundle(
        bundle,
        year="2017",
        content_type="reply",
        output_dir=str(tmp_path / "theme-output"),
        provider=MockProvider({"Fruit Theme": ["apple", "orange"]}),
        render_visuals=False,
    )

    assert not transitions.empty
    assert (tmp_path / "theme-output" / "community_transition.parquet").exists()


def test_longitudinal_fixtures_preserve_contract_and_self_spread_exclusion():
    for fixture in LONGITUDINAL_FIXTURES:
        with fixture.open(encoding="utf-8", newline="") as handle:
            assert next(csv.reader(handle)) == ["source", "target", "relation"]

        df = pd.read_csv(fixture)
        assert set(df["relation"]) == {"REPLIED_TO", "REPLIED_BY"}

        creators, spreaders = get_creator_spreader(df, "REPLIED_TO", "REPLIED_BY")
        assert len(creators) == len(spreaders)
        network_df = create_network_df(creators, "source")
        follower_df = get_follower_followee_network(network_df)

        assert ((network_df["from_id"] == 2) & (network_df["forwarder_id"] == 2)).any()
        assert not ((follower_df["source"] == 2) & (follower_df["target"] == 2)).any()
        assert {
            "source",
            "target",
            "shared_post",
            "total_post",
            "weighted_post",
        }.issubset(follower_df.columns)


def test_longitudinal_public_schema_columns_remain_stable():
    matched = _matched_lda_frame()
    themed = matched.copy()
    themed["all_keywords"] = "apple,orange"
    themed["absolute_keywords"] = "apple,bigapple"
    themed["weighted_keywords"] = "orange,bigorange"
    themed["general_theme_gpt"] = "{'Fruit Theme': ['apple']}"
    themed["general_theme_names"] = "Fruit Theme"
    themed["absolute_theme_gpt"] = "{'Fruit Theme': ['apple']}"
    themed["absolute_theme_names"] = "Fruit Theme"
    themed["weighted_theme_gpt"] = "{'Fruit Theme': ['orange']}"
    themed["weighted_theme_names"] = "Fruit Theme"

    assert list(matched.columns) == MATCHED_LDA_COLUMNS
    assert list(themed.columns) == THEMED_COLUMNS
