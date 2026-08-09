from __future__ import annotations

import ast
from typing import Any

import numpy as np
import pandas as pd

from src.config.defaults import DEFAULT_CONFIG

TRANSITION_COLUMNS = [
    "start_month",
    "end_month",
    "start_month_community",
    "end_month_community",
    "jaccard_score",
    "common_members",
    "uncommon_members",
    "start_month_members",
    "total_start_month_members",
    "end_month_members",
    "total_end_month_members",
    "start_month_absolute_theme",
    "end_month_absolute_theme",
    "start_month_weighted_theme",
    "end_month_weighted_theme",
    "start_month_general_theme",
    "end_month_general_theme",
]


def _native_member(value: Any) -> Any:
    """Convert NumPy scalar member IDs to stable Python scalar values."""
    return value.item() if isinstance(value, np.generic) else value


def _normalize_members(values: list[Any] | tuple[Any, ...] | set[Any]) -> list[Any]:
    return [_native_member(value) for value in values]


def _members(value: Any) -> list[Any]:
    if isinstance(value, list):
        return _normalize_members(value)
    if isinstance(value, tuple):
        return _normalize_members(value)
    if value is None or (not isinstance(value, (list, tuple, str)) and pd.isna(value)):
        return []
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return []
        return (
            _normalize_members(parsed) if isinstance(parsed, (list, tuple, set)) else []
        )
    if hasattr(value, "tolist"):
        parsed = value.tolist()
        values = parsed if isinstance(parsed, list) else [parsed]
        return [_native_member(member) for member in values]
    return []


def jaccard_similarity(list1, list2):
    set1 = set(list1)
    set2 = set(list2)
    union = set1 | set2
    return float(len(set1 & set2)) / len(union) if union else 0.0


def _theme_value(record: dict[str, Any], column: str) -> str:
    value = record.get(column, "")
    return "" if value is None else str(value)


def find_matching_communities(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    month1: str,
    month2: str,
    content_type: str,
    *,
    threshold: float | None = None,
) -> pd.DataFrame:
    """Compare consecutive-month communities with pre-parsed member sets."""
    if df1.empty or df2.empty:
        return pd.DataFrame(columns=TRANSITION_COLUMNS)

    if threshold is None:
        threshold = (
            DEFAULT_CONFIG.similarity.reply_transition_threshold
            if content_type == "reply"
            else DEFAULT_CONFIG.similarity.default_transition_threshold
        )
    threshold = float(threshold)

    left = []
    for record in df1.to_dict(orient="records"):
        members = _members(record.get("members", []))
        left.append((record, members, set(members)))
    right = []
    right_by_member: dict[Any, set[int]] = {}
    for right_index, record in enumerate(df2.to_dict(orient="records")):
        members = _members(record.get("members", []))
        member_set = set(members)
        right.append((record, members, member_set))
        for member in member_set:
            right_by_member.setdefault(member, set()).add(right_index)

    matched: list[dict[str, Any]] = []
    for row1, members1, set1 in left:
        # Every accepted Jaccard score is positive, so only communities sharing
        # at least one member can match. The sorted candidate indexes preserve
        # the legacy left-then-right output order while avoiding the full
        # Cartesian product for sparse monthly memberships.
        candidate_indexes: set[int] = set()
        for member in set1:
            candidate_indexes.update(right_by_member.get(member, ()))
        for right_index in sorted(candidate_indexes):
            row2, members2, set2 = right[right_index]
            union = set1 | set2
            common = set1 & set2
            score = float(len(common)) / len(union)
            if not (threshold <= score <= 1.0):
                continue

            start_comm = row1.get("absolute_community", "0")
            end_comm = row2.get("absolute_community", "0")
            matched.append(
                {
                    "start_month": month1,
                    "end_month": month2,
                    "start_month_community": f"{month1}_{start_comm}",
                    "end_month_community": f"{month2}_{end_comm}",
                    "jaccard_score": score,
                    "common_members": str(sorted(common, key=str)),
                    "uncommon_members": str(sorted(set1 ^ set2, key=str)),
                    "start_month_members": str(members1),
                    "total_start_month_members": len(members1),
                    "end_month_members": str(members2),
                    "total_end_month_members": len(members2),
                    "start_month_absolute_theme": _theme_value(
                        row1, "absolute_theme_names"
                    ),
                    "end_month_absolute_theme": _theme_value(
                        row2, "absolute_theme_names"
                    ),
                    "start_month_weighted_theme": _theme_value(
                        row1, "weighted_theme_names"
                    ),
                    "end_month_weighted_theme": _theme_value(
                        row2, "weighted_theme_names"
                    ),
                    "start_month_general_theme": _theme_value(
                        row1, "general_theme_names"
                    ),
                    "end_month_general_theme": _theme_value(
                        row2, "general_theme_names"
                    ),
                }
            )

    return pd.DataFrame(matched, columns=TRANSITION_COLUMNS)


def get_community_transition(
    theme_dict: dict[str, pd.DataFrame],
    content_type: str,
    *,
    threshold: float | None = None,
) -> pd.DataFrame:
    """Calculate transitions for consecutive months in insertion order."""
    all_matched = []
    month_names = list(theme_dict.keys())
    for index in range(1, len(month_names)):
        month1 = month_names[index - 1]
        month2 = month_names[index]
        result = find_matching_communities(
            theme_dict[month1],
            theme_dict[month2],
            month1,
            month2,
            content_type,
            threshold=threshold,
        )
        if not result.empty:
            all_matched.append(result)
    return (
        pd.concat(all_matched, ignore_index=True)
        if all_matched
        else pd.DataFrame(columns=TRANSITION_COLUMNS)
    )
