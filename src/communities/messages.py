from __future__ import annotations

import ast
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommunityMessageIndex:
    """Reusable edge-to-message index for community aggregation.

    The legacy implementation scanned the complete network dataframe once for
    every community edge.  This index builds the edge groups once and is reused
    by IF messages, WIF messages, and daily statistics.  The stored position
    arrays preserve the source dataframe row order, so the resulting message and
    message-id lists retain thesis ordering.
    """

    edge_positions: dict[tuple[Any, Any], np.ndarray]
    text_values: np.ndarray | None
    message_id_values: np.ndarray
    date_values: dict[str, np.ndarray]
    user_names: dict[Any, Any]

    @classmethod
    def build(
        cls,
        df_network: pd.DataFrame,
        df_user: pd.DataFrame | None = None,
        *,
        date_columns: Iterable[str] = (),
    ) -> "CommunityMessageIndex":
        required = {"from_id", "forwarder_id"}
        missing = sorted(required - set(df_network.columns))
        if missing:
            raise KeyError(f"Network dataframe is missing columns: {missing}")

        text_column = (
            "text_translated" if "text_translated" in df_network.columns else "text"
        )
        text_values = (
            df_network[text_column].to_numpy(copy=False)
            if text_column in df_network.columns
            else None
        )
        if "unique_id" not in df_network.columns:
            raise KeyError("Network dataframe is missing column: unique_id")
        message_ids = df_network["unique_id"].to_numpy(copy=False)

        # ``indices`` contains integer row positions and avoids materializing a
        # second dataframe with list-valued columns for every network edge.
        grouped = df_network.groupby(
            ["from_id", "forwarder_id"], sort=False, dropna=False
        ).indices
        edge_positions = {
            (source, target): np.asarray(positions, dtype=np.int64)
            for (source, target), positions in grouped.items()
        }

        dates = {
            column: df_network[column].to_numpy(copy=False)
            for column in date_columns
            if column in df_network.columns
        }

        user_names: dict[Any, Any] = {}
        if df_user is not None and {"user_id", "username"}.issubset(df_user.columns):
            # Preserve the first user row, matching the legacy iloc[0] lookup.
            unique_users = df_user.drop_duplicates("user_id", keep="first")
            user_names = dict(
                zip(unique_users["user_id"].tolist(), unique_users["username"].tolist())
            )

        return cls(
            edge_positions=edge_positions,
            text_values=text_values,
            message_id_values=message_ids,
            date_values=dates,
            user_names=user_names,
        )

    def positions(self, source: Any, target: Any) -> np.ndarray:
        return self.edge_positions.get((source, target), np.empty(0, dtype=np.int64))

    def messages(self, source: Any, target: Any) -> list[Any]:
        positions = self.positions(source, target)
        if self.text_values is None or not len(positions):
            return []
        return self.text_values.take(positions).tolist()

    def message_ids(self, source: Any, target: Any) -> list[Any]:
        positions = self.positions(source, target)
        return self.message_id_values.take(positions).tolist() if len(positions) else []

    def dates(self, source: Any, target: Any, date_column: str) -> list[Any]:
        values = self.date_values.get(date_column)
        if values is None:
            return []
        positions = self.positions(source, target)
        if not len(positions):
            return []
        selected = values.take(positions)
        if np.issubdtype(selected.dtype, np.datetime64):
            return pd.to_datetime(selected).tolist()
        return selected.tolist()

    def username(self, user_id: Any) -> Any:
        username = self.user_names.get(user_id)
        if username is None or pd.isna(username) or username == "":
            return f"anonymous{user_id}"
        return username


def build_community_message_index(
    df_network: pd.DataFrame,
    df_user: pd.DataFrame | None = None,
    *,
    date_columns: Iterable[str] = (),
) -> CommunityMessageIndex:
    return CommunityMessageIndex.build(df_network, df_user, date_columns=date_columns)


def get_specific_community_info(
    df_community: pd.DataFrame,
    community_number: Any,
    df_network: pd.DataFrame,
    df_user: pd.DataFrame,
    *,
    message_index: CommunityMessageIndex | None = None,
) -> pd.DataFrame:
    index = message_index or build_community_message_index(df_network, df_user)
    community = df_community[df_community["community_number"] == community_number]

    rows: list[dict[str, Any]] = []
    for row in community.itertuples(index=False):
        source = getattr(row, "source")
        target = getattr(row, "target")
        messages = index.messages(source, target)
        message_ids = index.message_ids(source, target)
        rows.append(
            {
                "producer_username": index.username(source),
                "producer_user_id": source,
                "forwarder_username": index.username(target),
                "forwarder_user_id": target,
                "total_messages": len(messages),
                "messages": messages,
                "message_ids": message_ids,
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "producer_username",
            "producer_user_id",
            "forwarder_username",
            "forwarder_user_id",
            "total_messages",
            "messages",
            "message_ids",
        ],
    )


def _progress_step(total: int, progress_every: int | None) -> int:
    if total <= 0:
        return 1
    if progress_every is not None:
        return max(1, int(progress_every))
    return max(1, total // 10)


def get_community_messages(
    prominent_communities,
    community_df: pd.DataFrame,
    df_network: pd.DataFrame,
    df_user: pd.DataFrame,
    *,
    message_index: CommunityMessageIndex | None = None,
    progress_label: str = "community_messages",
    progress_every: int | None = None,
) -> pd.DataFrame:
    """Aggregate messages for each prominent community in linear-time lookups."""
    index = message_index or build_community_message_index(df_network, df_user)
    total = len(prominent_communities)
    grouped = {
        community_number: group
        for community_number, group in community_df.groupby(
            "community_number", sort=False
        )
    }
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    step = _progress_step(total, progress_every)

    logger.info(
        "%s started communities=%d network_rows=%d indexed_edges=%d",
        progress_label,
        total,
        len(df_network),
        len(index.edge_positions),
    )

    for community_number in range(total):
        messages: list[Any] = []
        message_ids: list[Any] = []
        community = grouped.get(community_number)
        if community is not None:
            for row in community.itertuples(index=False):
                source = getattr(row, "source")
                target = getattr(row, "target")
                positions = index.positions(source, target)
                if len(positions):
                    if index.text_values is not None:
                        messages.extend(index.text_values.take(positions).tolist())
                    message_ids.extend(index.message_id_values.take(positions).tolist())

        rows.append(
            {
                "community_number": community_number,
                "messages": messages,
                "messages_ids": message_ids,
                "total_messages": len(messages),
            }
        )

        completed = community_number + 1
        if completed == total or completed % step == 0:
            logger.info(
                "%s progress completed=%d total=%d elapsed_seconds=%.2f",
                progress_label,
                completed,
                total,
                time.perf_counter() - started,
            )

    return pd.DataFrame(
        rows,
        columns=["community_number", "messages", "messages_ids", "total_messages"],
    )


def get_overall_community_messages_stat(
    date_col,
    promiment_communities,
    df_community,
    df_network,
    *,
    message_index: CommunityMessageIndex | None = None,
):
    index = message_index or build_community_message_index(
        df_network, date_columns=(date_col,)
    )
    if date_col not in index.date_values:
        return {}

    days: list[Any] = []
    # Community rows already contain only prominent-community edges.  One pass is
    # sufficient; the previous implementation repeatedly filtered the full
    # network once for every edge and every community.
    for row in df_community.itertuples(index=False):
        source = getattr(row, "source")
        target = getattr(row, "target")
        days.extend(
            _extract_day(value) for value in index.dates(source, target, date_col)
        )

    if not days:
        return {}

    daily_messages = pd.Series(days).value_counts()
    if daily_messages.empty:
        return {}

    return {
        "min_msg_count": daily_messages.min(),
        "day_of_min_msg": daily_messages.idxmin(),
        "max_msg_count": daily_messages.max(),
        "day_of_max_msg": daily_messages.idxmax(),
        "std_msg_count": daily_messages.std(),
        "avg_msg_count": daily_messages.mean(),
    }


def _extract_day(value):
    """Extract day from legacy tuple strings or ISO/pandas datetime values."""
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            return parsed[2]
        except (SyntaxError, ValueError, TypeError, IndexError):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).day
    if isinstance(value, np.datetime64):
        return pd.Timestamp(value).day
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.day
    return value
