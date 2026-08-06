from __future__ import annotations

import ast
import re
from typing import Any

import pandas as pd

NEO4J_DATETIME_RE = re.compile(
    r"neo4j\.time\.DateTime\((?P<args>.*?)(?:,\s*)?tzinfo=<UTC>\)", re.DOTALL
)


def get_creator_spreader(
    df_data: pd.DataFrame, creator_relation: str, spreader_relation: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split legacy exported rows into creator and spreader relationship rows."""
    if "relation" not in df_data.columns:
        raise KeyError("Expected legacy graph export column: relation")

    df_creator = df_data[df_data["relation"] == creator_relation].copy()
    df_spreader = df_data[df_data["relation"] == spreader_relation].copy()
    return df_creator.reset_index(drop=True), df_spreader.reset_index(drop=True)


def convert_neo4j_datetime_strings(value: Any) -> Any:
    """Convert stringified Neo4j DateTime calls into tuple strings.

    The original thesis code later used `eval(date_value)[2]` to read the day
    component for daily message statistics, so this keeps that tuple-like shape.
    """
    if not isinstance(value, str):
        return value

    def replace_datetime(match: re.Match[str]) -> str:
        args = match.group("args").strip()
        if args.endswith(","):
            args = args[:-1].strip()
        return repr(f"({args})")

    return NEO4J_DATETIME_RE.sub(replace_datetime, value)


def parse_node_dict(value: Any) -> dict[str, Any]:
    """Parse a Neo4j node dictionary from a dict or legacy stringified dict."""
    if isinstance(value, dict):
        return {key: convert_neo4j_datetime_strings(val) for key, val in value.items()}
    if pd.isna(value):
        return {}
    if not isinstance(value, str):
        return {}

    cleaned = convert_neo4j_datetime_strings(value)
    parsed = ast.literal_eval(cleaned)
    if not isinstance(parsed, dict):
        return {}

    return {key: convert_neo4j_datetime_strings(val) for key, val in parsed.items()}


def normalize_username(user: dict[str, Any]) -> dict[str, Any]:
    """Fill missing usernames as `anonymous<user_id>`."""
    normalized = dict(user)
    user_id = normalized.get("user_id")
    username = normalized.get("username")
    if pd.isna(username) or username in ("", None):
        normalized["username"] = f"anonymous{user_id}"
    return normalized


def create_user_df(
    df_spreader: pd.DataFrame,
    df_creator: pd.DataFrame,
    creator_node_column: str,
    spreader_node_column: str,
) -> pd.DataFrame:
    """Create a unique user dataframe from creator and spreader node columns.

    Legacy exports repeat the same stringified user node for every message.
    De-duplicating the raw node representations before ``ast.literal_eval``
    avoids millions of redundant parses on full Twitter datasets while
    preserving the first-observed user record.
    """
    raw_users = pd.concat(
        [
            df_creator[creator_node_column],
            df_spreader[spreader_node_column],
        ],
        ignore_index=True,
    ).dropna()
    raw_users = raw_users.drop_duplicates(keep="first")

    users = [normalize_username(parse_node_dict(value)) for value in raw_users]
    users = [user for user in users if user.get("user_id") is not None]
    if not users:
        return pd.DataFrame(columns=["user_id", "username"])

    df_user = pd.DataFrame(users).drop_duplicates("user_id", keep="first")
    if "username" not in df_user.columns:
        df_user["username"] = pd.NA

    missing_username = df_user["username"].isna() | df_user["username"].astype(
        str
    ).str.strip().eq("")
    df_user.loc[missing_username, "username"] = "anonymous" + df_user.loc[
        missing_username, "user_id"
    ].astype(str)

    preferred = ["user_id", "username"]
    remaining = [column for column in df_user.columns if column not in preferred]
    return df_user[preferred + remaining].reset_index(drop=True)


def create_network_df(
    df_creator: pd.DataFrame, text_node_column_creator_df: str
) -> pd.DataFrame:
    """Create the normalized message/network dataframe used by IF/WIF metrics."""
    if df_creator.empty:
        return pd.DataFrame()

    records = df_creator[text_node_column_creator_df].map(parse_node_dict).tolist()

    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).reset_index(drop=True)
