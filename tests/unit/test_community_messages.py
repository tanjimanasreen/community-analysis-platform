import pytest
import pandas as pd
from src.communities.messages import (
    get_specific_community_info,
    get_community_messages,
    get_overall_community_messages_stat,
)


@pytest.fixture
def sample_data():
    df_user = pd.DataFrame(
        {"user_id": ["u1", "u2", "u3"], "username": ["alice", "bob", "charlie"]}
    )

    df_network = pd.DataFrame(
        {
            "from_id": ["u1", "u1", "u2"],
            "forwarder_id": ["u2", "u2", "u3"],
            "text": ["msg1", "msg2", "msg3"],
            "unique_id": ["m1", "m2", "m3"],
            "date": [
                "(2019, 11, 1, 10, 0, 0)",
                "(2019, 11, 2, 10, 0, 0)",
                "(2019, 11, 1, 10, 0, 0)",
            ],
        }
    )

    df_community = pd.DataFrame(
        {"source": ["u1", "u2"], "target": ["u2", "u3"], "community_number": [0, 0]}
    )

    return df_user, df_network, df_community


def test_get_specific_community_info(sample_data):
    df_user, df_network, df_community = sample_data

    info = get_specific_community_info(df_community, 0, df_network, df_user)
    assert len(info) == 2
    assert info["producer_username"].iloc[0] == "alice"
    assert info["total_messages"].iloc[0] == 2
    assert "msg1" in info["messages"].iloc[0]


def test_get_community_messages(sample_data):
    df_user, df_network, df_community = sample_data
    prominent = [{"u1", "u2", "u3"}]

    messages = get_community_messages(prominent, df_community, df_network, df_user)
    assert len(messages) == 1
    assert messages["total_messages"].iloc[0] == 3
    assert "msg1" in messages["messages"].iloc[0]


def test_get_overall_community_messages_stat(sample_data):
    df_user, df_network, df_community = sample_data
    prominent = [{"u1", "u2", "u3"}]

    stats = get_overall_community_messages_stat(
        "date", prominent, df_community, df_network
    )
    # Day 1 has 2 messages, Day 2 has 1 message
    assert stats["max_msg_count"] == 2
    assert stats["min_msg_count"] == 1
    assert stats["day_of_max_msg"] == 1
    assert stats["day_of_min_msg"] == 2


def test_get_overall_community_messages_stat_accepts_iso_dates(sample_data):
    df_user, df_network, df_community = sample_data
    df_network = df_network.copy()
    df_network["created_at"] = [
        "2017-03-01T12:00:00Z",
        "2017-03-02T12:00:00Z",
        "2017-03-01T12:00:00Z",
    ]
    prominent = [{"u1", "u2", "u3"}]

    stats = get_overall_community_messages_stat(
        "created_at", prominent, df_community, df_network
    )

    assert stats["max_msg_count"] == 2
    assert stats["day_of_max_msg"] == 1
