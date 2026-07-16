from __future__ import annotations

from dataclasses import dataclass

USER = "User"
MESSAGE = "Message"
CHANNEL = "Channel"
FORWARD_MESSAGE = "Forward_Message"
TWITTER_USER = "Twitter_User"
RETWEET_QUOTE = "Retweet_Quote"
REPLY = "Reply"

CREATED = "CREATED"
SENT_TO = "SENT_TO"
PRODUCED = "PRODUCED"
ORIGINATED = "ORIGINATED"
FORWARDED_BY = "FORWARDED_BY"
FORWARDED_TO = "FORWARDED_TO"
TWEETED = "TWEETED"
RETWEETED_BY = "RETWEETED_BY"
REPLIED_TO = "REPLIED_TO"
REPLIED_BY = "REPLIED_BY"

TELEGRAM_NODE_LABELS = (USER, MESSAGE, CHANNEL, FORWARD_MESSAGE)
TWITTER_NODE_LABELS = (TWITTER_USER, RETWEET_QUOTE, REPLY)

TELEGRAM_RELATION_TYPES = (
    CREATED,
    SENT_TO,
    PRODUCED,
    ORIGINATED,
    FORWARDED_BY,
    FORWARDED_TO,
)
TWITTER_RELATION_TYPES = (TWEETED, RETWEETED_BY, REPLIED_TO, REPLIED_BY)

TELEGRAM_RELATION_MAP = {
    CREATED: (USER, MESSAGE),
    SENT_TO: (MESSAGE, CHANNEL),
    PRODUCED: (USER, FORWARD_MESSAGE),
    ORIGINATED: (CHANNEL, FORWARD_MESSAGE),
    FORWARDED_BY: (FORWARD_MESSAGE, USER),
    FORWARDED_TO: (FORWARD_MESSAGE, CHANNEL),
}

TWITTER_RELATION_MAP = {
    TWEETED: (TWITTER_USER, RETWEET_QUOTE),
    RETWEETED_BY: (RETWEET_QUOTE, TWITTER_USER),
    REPLIED_TO: (REPLY, TWITTER_USER),
    REPLIED_BY: (REPLY, TWITTER_USER),
}

PRIMARY_KEYS = {
    USER: "user_id",
    TWITTER_USER: "user_id",
    MESSAGE: "unique_id",
    FORWARD_MESSAGE: "unique_id",
    RETWEET_QUOTE: "unique_id",
    REPLY: "unique_id",
    CHANNEL: "channel_id",
}

LEGACY_EXPORT_COLUMNS = ("source", "target", "relation")
INTERACTION_EDGE_COLUMNS = (
    "source",
    "target",
    "total_post",
    "shared_post",
    "weighted_post",
    "data_type",
    "content_type",
    "month",
    "year",
)


@dataclass(frozen=True)
class RawToDerivedMapping:
    content_type: str
    creator_relation: str
    spreader_relation: str
    source_user_column: str
    target_user_column: str
    message_node_column: str
    date_field: str
    output_edge_fields: tuple[str, ...] = INTERACTION_EDGE_COLUMNS


RAW_TO_DERIVED_MAPPINGS = {
    "telegram_forward": RawToDerivedMapping(
        content_type="forward",
        creator_relation=PRODUCED,
        spreader_relation=FORWARDED_BY,
        source_user_column="source",
        target_user_column="target",
        message_node_column="target",
        date_field="forwarded_date",
    ),
    "twitter_retweet_quote": RawToDerivedMapping(
        content_type="retweet_quote",
        creator_relation=TWEETED,
        spreader_relation=RETWEETED_BY,
        source_user_column="source",
        target_user_column="target",
        message_node_column="target",
        date_field="created_at",
    ),
    "twitter_reply": RawToDerivedMapping(
        content_type="reply",
        creator_relation=REPLIED_TO,
        spreader_relation=REPLIED_BY,
        source_user_column="target",
        target_user_column="target",
        message_node_column="source",
        date_field="created_at",
    ),
}
