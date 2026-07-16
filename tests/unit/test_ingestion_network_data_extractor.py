import pandas as pd

from src.config.defaults import DEFAULT_CONFIG
from src.config.loader import normalize_month
from src.ingestion.network_data_extractor import (
    convert_neo4j_datetime_strings,
    create_network_df,
    create_user_df,
    get_creator_spreader,
    parse_node_dict,
)
from src.ingestion.schema import (
    FORWARDED_BY,
    FORWARDED_TO,
    LEGACY_EXPORT_COLUMNS,
    PRODUCED,
    RAW_TO_DERIVED_MAPPINGS,
    REPLIED_BY,
    REPLIED_TO,
    RETWEETED_BY,
    TELEGRAM_RELATION_MAP,
    TWEETED,
    TWITTER_RELATION_MAP,
)
from src.network.follower_followee import get_follower_followee_network


def test_creator_spreader_split():
    df = pd.DataFrame(
        {
            "source": ["message-1", "message-1", "message-2"],
            "target": ["u1", "u2", "u3"],
            "relation": [REPLIED_TO, REPLIED_BY, REPLIED_BY],
        }
    )

    creators, spreaders = get_creator_spreader(df, REPLIED_TO, REPLIED_BY)

    assert list(creators["relation"]) == [REPLIED_TO]
    assert list(spreaders["relation"]) == [REPLIED_BY, REPLIED_BY]


def test_create_user_df_normalizes_anonymous_usernames():
    df_creator = pd.DataFrame(
        {
            "target": [
                "{'user_id': 'u1', 'username': ''}",
                "{'user_id': 'u2', 'username': 'alice'}",
            ]
        }
    )
    df_spreader = pd.DataFrame(
        {
            "target": [
                "{'user_id': 'u3', 'username': None}",
                "{'user_id': 'u2', 'username': 'alice'}",
            ]
        }
    )

    df_user = create_user_df(df_spreader, df_creator, "target", "target")

    assert set(df_user["user_id"]) == {"u1", "u2", "u3"}
    assert df_user.loc[df_user["user_id"] == "u1", "username"].iloc[0] == "anonymousu1"
    assert df_user.loc[df_user["user_id"] == "u3", "username"].iloc[0] == "anonymousu3"
    assert df_user.loc[df_user["user_id"] == "u2", "username"].iloc[0] == "alice"


def test_parse_node_dict_and_neo4j_datetime_cleanup():
    raw = (
        "{'unique_id': 'm1', 'created_at': "
        "neo4j.time.DateTime(2019, 11, 1, 10, 0, 0, tzinfo=<UTC>), "
        "'text': 'hello'}"
    )

    cleaned = convert_neo4j_datetime_strings(raw)
    parsed = parse_node_dict(raw)

    assert "neo4j.time.DateTime" not in cleaned
    assert parsed["unique_id"] == "m1"
    assert parsed["created_at"] == "(2019, 11, 1, 10, 0, 0)"


def test_create_network_df_from_stringified_message_nodes():
    df_creator = pd.DataFrame(
        {
            "source": [
                "{'unique_id': 'm1', 'from_id': 'u1', 'forwarder_id': 'u2', "
                "'text': 'hello', 'created_at': '2017-03-01T12:00:00Z'}",
                "{'unique_id': 'm2', 'from_id': 'u1', 'forwarder_id': 'u1', "
                "'text': 'self spread', 'created_at': '2017-03-01T12:10:00Z'}",
            ]
        }
    )

    df_network = create_network_df(df_creator, "source")

    assert list(df_network["unique_id"]) == ["m1", "m2"]
    assert list(df_network["from_id"]) == ["u1", "u1"]
    assert list(df_network["forwarder_id"]) == ["u2", "u1"]


def test_follower_followee_metrics_and_self_spread_exclusion_from_normalized_df():
    df_network = pd.DataFrame(
        {
            "from_id": ["u1", "u1", "u1", "u2"],
            "forwarder_id": ["u2", "u2", "u1", "u1"],
        }
    )

    edges = get_follower_followee_network(df_network)
    u1_u2 = edges[(edges["source"] == "u1") & (edges["target"] == "u2")].iloc[0]

    assert u1_u2["total_post"] == 3
    assert u1_u2["shared_post"] == 2
    assert u1_u2["weighted_post"] == 2 / 3
    assert not ((edges["source"] == "u1") & (edges["target"] == "u1")).any()


def test_defaults_are_preserved_for_ingestion_phase():
    assert DEFAULT_CONFIG.graph.min_total_post == 10
    assert DEFAULT_CONFIG.graph.min_shared_post == 5
    assert DEFAULT_CONFIG.graph.min_members == 3
    assert DEFAULT_CONFIG.louvain.resolution == 1.0
    assert DEFAULT_CONFIG.louvain.seed == 123
    assert DEFAULT_CONFIG.lda.num_topics == 15
    assert DEFAULT_CONFIG.theme_provider.primary == "mock"
    assert DEFAULT_CONFIG.theme_provider.fallback is True
    assert DEFAULT_CONFIG.theme_provider.fallback_chain == [
        "llm7:fast",
        "nvidia:meta/llama3-70b-instruct",
    ]
    assert normalize_month("03") == 3
    assert normalize_month("october") == 10


def test_raw_to_derived_mapping_constants_use_current_thesis_export_labels():
    assert LEGACY_EXPORT_COLUMNS == ("source", "target", "relation")
    assert TELEGRAM_RELATION_MAP[PRODUCED] == ("User", "Forward_Message")
    assert TELEGRAM_RELATION_MAP[FORWARDED_BY] == ("Forward_Message", "User")
    assert FORWARDED_TO in TELEGRAM_RELATION_MAP
    assert TWITTER_RELATION_MAP[TWEETED] == ("Twitter_User", "Retweet_Quote")
    assert TWITTER_RELATION_MAP[RETWEETED_BY] == ("Retweet_Quote", "Twitter_User")

    reply_mapping = RAW_TO_DERIVED_MAPPINGS["twitter_reply"]
    assert reply_mapping.content_type == "reply"
    assert reply_mapping.creator_relation == REPLIED_TO
    assert reply_mapping.spreader_relation == REPLIED_BY
    assert reply_mapping.source_user_column == "target"
    assert reply_mapping.target_user_column == "target"
    assert reply_mapping.date_field == "created_at"
    assert reply_mapping.output_edge_fields[:5] == (
        "source",
        "target",
        "total_post",
        "shared_post",
        "weighted_post",
    )
