from pathlib import Path

import pandas as pd
import pytest

from src.config.loader import load_config, validate_run_config
from src.ingestion.schema import validate_canonical_raw_mapping
from src.network.follower_followee import get_follower_followee_network
from src.pipelines.ingestion_pipeline import normalize_network_input

ROOT = Path(__file__).resolve().parents[2]


EXPECTED_MAPPINGS = {
    "configs/twitter/reply_evolution.yml": {
        "data_type": "twitter",
        "content_type": "reply",
        "creator_relation": "REPLIED_TO",
        "spreader_relation": "REPLIED_BY",
        "creator_node_column": "target",
        "spreader_node_column": "target",
        "text_node_column": "source",
        "date_column": "created_at",
    },
    "configs/twitter/retweet_quote_evolution.yml": {
        "data_type": "twitter",
        "content_type": "retweet_quote",
        "creator_relation": "TWEETED",
        "spreader_relation": "RETWEETED_BY",
        "creator_node_column": "source",
        "spreader_node_column": "target",
        "text_node_column": "target",
        "date_column": "created_at",
    },
    "configs/telegram/forwarded_message_evolution.yml": {
        "data_type": "telegram",
        "content_type": "forward",
        "creator_relation": "PRODUCED",
        "spreader_relation": "FORWARDED_BY",
        "creator_node_column": "source",
        "spreader_node_column": "target",
        "text_node_column": "target",
        "date_column": "forwarded_date",
    },
}


def test_only_canonical_production_evolution_configs_remain():
    assert not (ROOT / "configs/longitudinal").exists()
    assert not (ROOT / "configs/twitter/retweet_quote.yml").exists()
    assert not (ROOT / "configs/telegram/forwarded_message.yml").exists()
    assert {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "configs").glob("*/*_evolution.yml")
    } == set(EXPECTED_MAPPINGS)


@pytest.mark.parametrize(("config_path", "expected"), EXPECTED_MAPPINGS.items())
def test_canonical_evolution_configs_use_expected_analytical_mapping(
    config_path, expected
):
    config = load_config(ROOT / config_path)

    validate_run_config(config)
    validate_canonical_raw_mapping(config)

    for key, value in expected.items():
        assert config[key] == value
    assert config["theme"]["reply_transition_threshold"] == 0.0
    assert config["theme"]["transition_threshold"] == 0.5


def test_telegram_evolution_config_declares_january_through_october_2019(monkeypatch):
    monkeypatch.setenv("DATA_ROOT", "data/raw")
    config = load_config(ROOT / "configs/telegram/forwarded_message_evolution.yml")
    datasets = config["longitudinal_datasets"]

    assert [row["month"] for row in datasets] == [
        f"{month:02d}" for month in range(1, 11)
    ]
    assert [row["input_path"] for row in datasets] == [
        f"data/raw/telegram/forwarded_message/2019/{month}_2019.csv"
        for month in (
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
        )
    ]


def test_test_evolution_config_inherits_canonical_reply_semantics():
    config = load_config(ROOT / "tests/configs/test_evolution.yml")

    for key, value in EXPECTED_MAPPINGS["configs/twitter/reply_evolution.yml"].items():
        assert config[key] == value
    assert config["graph_thresholds"] == {
        "min_total_post": 1,
        "min_shared_post": 1,
        "min_members": 2,
    }
    assert [row["month"] for row in config["longitudinal_datasets"]] == ["03", "04"]


def test_canonical_mapping_validation_rejects_reply_with_retweet_relations():
    config = load_config(ROOT / "configs/twitter/reply_evolution.yml")
    config["creator_relation"] = "TWEETED"
    config["spreader_relation"] = "RETWEETED_BY"

    with pytest.raises(
        ValueError, match="Invalid analytical mapping for twitter/reply"
    ):
        validate_canonical_raw_mapping(config)


def test_raw_telegram_relationships_normalize_before_existing_if_wif_metrics():
    raw = pd.DataFrame(
        [
            {
                "source": "{'user_id': 'creator-1', 'username': 'creator'}",
                "target": (
                    "{'unique_id': 'm1', 'text': 'forwarded text', "
                    "'forwarded_date': '(2019, 9, 1, 10, 0, 0)'}"
                ),
                "relation": "PRODUCED",
            },
            {
                "source": (
                    "{'unique_id': 'm1', 'text': 'forwarded text', "
                    "'forwarded_date': '(2019, 9, 1, 10, 0, 0)'}"
                ),
                "target": "{'user_id': 'spreader-1', 'username': 'spreader'}",
                "relation": "FORWARDED_BY",
            },
        ]
    )
    config = load_config(ROOT / "configs/telegram/forwarded_message_evolution.yml")
    config["month"] = "09"

    network = normalize_network_input(raw, config)
    interactions = get_follower_followee_network(network)

    assert network.loc[0, "from_id"] == "creator-1"
    assert network.loc[0, "forwarder_id"] == "spreader-1"
    assert interactions.loc[0, "source"] == "creator-1"
    assert interactions.loc[0, "target"] == "spreader-1"
    assert interactions.loc[0, "shared_post"] == 1
    assert interactions.loc[0, "total_post"] == 1
    assert interactions.loc[0, "weighted_post"] == 1.0


def test_already_normalized_telegram_input_is_preserved():
    normalized = pd.DataFrame(
        {"from_id": ["u1"], "forwarder_id": ["u2"], "text": ["message"]}
    )
    config = load_config(ROOT / "configs/telegram/forwarded_message_evolution.yml")

    result = normalize_network_input(normalized, config)

    assert result is normalized
