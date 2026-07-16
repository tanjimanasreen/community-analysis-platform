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
    """Create a unique user dataframe from creator and spreader node columns."""
    users: list[dict[str, Any]] = []

    for _, row in df_creator.iterrows():
        users.append(normalize_username(parse_node_dict(row[creator_node_column])))

    for _, row in df_spreader.iterrows():
        users.append(normalize_username(parse_node_dict(row[spreader_node_column])))

    if not users:
        return pd.DataFrame(columns=["user_id", "username"])

    df_user = pd.DataFrame(users)
    if "user_id" not in df_user.columns:
        return pd.DataFrame(columns=["user_id", "username"])

    df_user = df_user.dropna(subset=["user_id"]).drop_duplicates("user_id")
    if "username" not in df_user.columns:
        df_user["username"] = df_user["user_id"].apply(
            lambda user_id: f"anonymous{user_id}"
        )
    else:
        df_user["username"] = df_user.apply(
            lambda row: (
                row["username"]
                if not pd.isna(row["username"]) and row["username"] not in ("", None)
                else f"anonymous{row['user_id']}"
            ),
            axis=1,
        )

    preferred = ["user_id", "username"]
    remaining = [column for column in df_user.columns if column not in preferred]
    return df_user[preferred + remaining].reset_index(drop=True)


def create_network_df(
    df_creator: pd.DataFrame, text_node_column_creator_df: str
) -> pd.DataFrame:
    """Create the normalized message/network dataframe used by IF/WIF metrics."""
    records = [
        parse_node_dict(row[text_node_column_creator_df])
        for _, row in df_creator.iterrows()
    ]
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).reset_index(drop=True)
