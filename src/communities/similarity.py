from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def get_community_members(df: pd.DataFrame) -> pd.DataFrame:
    """Extract unique source/target members for each community."""
    if df.empty:
        return pd.DataFrame(columns=["community_number", "members"])

    community_data = []
    for community_number, group in df.groupby(
        "community_number", sort=False, observed=True
    ):
        members = np.unique(group[["source", "target"]].to_numpy().ravel())
        community_data.append(
            {"community_number": community_number, "members": list(members)}
        )
    return pd.DataFrame(community_data)


def jaccard_similarity(list1, list2):
    set1 = set(list1)
    set2 = set(list2)
    union = set1 | set2
    return float(len(set1 & set2)) / len(union) if union else 0.0


def find_matching_communities(
    absolute_community_df: pd.DataFrame, weighted_community_df: pd.DataFrame
):
    if absolute_community_df.empty or weighted_community_df.empty:
        return (
            pd.DataFrame(
                columns=["abs_community", "per_community", "jaccard_score", "members"]
            ),
            pd.DataFrame(
                columns=[
                    "abs_community",
                    "absolute_members",
                    "per_community",
                    "weighted_members",
                    "jaccard_score",
                    "common_members",
                    "uncommon_members",
                ]
            ),
            pd.DataFrame(columns=["abs_community"]),
            pd.DataFrame(columns=["per_community"]),
        )

    absolute = get_community_members(absolute_community_df)
    weighted = get_community_members(weighted_community_df)

    absolute_records: list[tuple[Any, list[Any], set[Any]]] = [
        (row.community_number, list(row.members), set(row.members))
        for row in absolute.itertuples(index=False)
    ]
    weighted_records: list[tuple[Any, list[Any], set[Any]]] = [
        (row.community_number, list(row.members), set(row.members))
        for row in weighted.itertuples(index=False)
    ]
    weighted_by_member: dict[Any, set[int]] = {}
    for weighted_index, (_community_id, _members, member_set) in enumerate(
        weighted_records
    ):
        for member in member_set:
            weighted_by_member.setdefault(member, set()).add(weighted_index)

    matched: list[tuple[Any, Any, float, list[Any]]] = []
    partial: list[
        tuple[Any, list[Any], Any, list[Any], float, list[Any], list[Any]]
    ] = []
    matched_absolute: set[Any] = set()
    matched_weighted: set[Any] = set()

    for abs_id, abs_members, abs_set in absolute_records:
        candidate_indexes: set[int] = set()
        for member in abs_set:
            candidate_indexes.update(weighted_by_member.get(member, ()))
        for weighted_index in sorted(candidate_indexes):
            weighted_id, weighted_members, weighted_set = weighted_records[
                weighted_index
            ]
            union = abs_set | weighted_set
            common = abs_set & weighted_set
            score = float(len(common)) / len(union)
            if score == 1.0:
                matched.append((abs_id, weighted_id, score, abs_members))
                matched_absolute.add(abs_id)
                matched_weighted.add(weighted_id)
            elif 0.0 < score < 1.0:
                partial.append(
                    (
                        abs_id,
                        abs_members,
                        weighted_id,
                        weighted_members,
                        score,
                        list(common),
                        list(abs_set ^ weighted_set),
                    )
                )
                matched_absolute.add(abs_id)
                matched_weighted.add(weighted_id)

    matched_df = pd.DataFrame(
        matched, columns=["abs_community", "per_community", "jaccard_score", "members"]
    )
    partial_df = pd.DataFrame(
        partial,
        columns=[
            "abs_community",
            "absolute_members",
            "per_community",
            "weighted_members",
            "jaccard_score",
            "common_members",
            "uncommon_members",
        ],
    )
    unmatched_absolute = pd.DataFrame(
        [
            community_id
            for community_id, _, _ in absolute_records
            if community_id not in matched_absolute
        ],
        columns=["abs_community"],
    )
    unmatched_weighted = pd.DataFrame(
        [
            community_id
            for community_id, _, _ in weighted_records
            if community_id not in matched_weighted
        ],
        columns=["per_community"],
    )
    return matched_df, partial_df, unmatched_absolute, unmatched_weighted
