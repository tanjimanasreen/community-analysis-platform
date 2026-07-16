import pandas as pd
import numpy as np


def get_community_members(df):
    """
    Extracts all unique members (source and target) for each community_number.
    """
    community_data = []
    grouped = df.groupby("community_number")

    for community_number, group in grouped:
        members = np.unique(group[["source", "target"]].values.flatten())
        community_data.append(
            {"community_number": community_number, "members": list(members)}
        )

    community_df = pd.DataFrame(community_data)
    return community_df


def jaccard_similarity(list1, list2):
    """Define Jaccard Similarity function for two sets"""
    set1 = set(list1)
    set2 = set(list2)
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return float(intersection) / union if union > 0 else 0.0


def find_matching_communities(absolute_community_df, weighted_community_df):
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

    df1 = get_community_members(absolute_community_df)
    df2 = get_community_members(weighted_community_df)

    matched = []
    unmatched_df1 = df1["community_number"].tolist() if not df1.empty else []
    unmatched_df2 = df2["community_number"].tolist() if not df2.empty else []
    partial_matched = []

    # Finding matching communities
    for index1, row1 in df1.iterrows():
        for index2, row2 in df2.iterrows():
            jscore = jaccard_similarity(list(row1["members"]), list(row2["members"]))
            if jscore == 1:
                matched.append(
                    (
                        row1["community_number"],
                        row2["community_number"],
                        jscore,
                        list(row1["members"]),
                    )
                )
                if row1["community_number"] in unmatched_df1:
                    unmatched_df1.remove(row1["community_number"])
                if row2["community_number"] in unmatched_df2:
                    unmatched_df2.remove(row2["community_number"])
            elif 1 > jscore > 0:
                common_members = list(
                    set(list(row1["members"])) & set(list(row2["members"]))
                )
                uncommon_members = list(
                    set(list(row1["members"])) ^ set(list(row2["members"]))
                )
                partial_matched.append(
                    (
                        row1["community_number"],
                        row1["members"],
                        row2["community_number"],
                        row2["members"],
                        jscore,
                        common_members,
                        uncommon_members,
                    )
                )
                if row1["community_number"] in unmatched_df1:
                    unmatched_df1.remove(row1["community_number"])
                if row2["community_number"] in unmatched_df2:
                    unmatched_df2.remove(row2["community_number"])

    # Create dataframes for matched and unmatched communities
    matched_df = pd.DataFrame(
        matched, columns=["abs_community", "per_community", "jaccard_score", "members"]
    )
    partial_matched_df = pd.DataFrame(
        partial_matched,
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

    unmatched_df1_df = pd.DataFrame(unmatched_df1, columns=["abs_community"])
    unmatched_df2_df = pd.DataFrame(unmatched_df2, columns=["per_community"])

    return matched_df, partial_matched_df, unmatched_df1_df, unmatched_df2_df
