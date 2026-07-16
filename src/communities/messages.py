import pandas as pd
import ast
from datetime import datetime


def get_specific_community_info(df_community, community_number, df_network, df_user):
    community = df_community[df_community["community_number"] == community_number]

    community_details = pd.DataFrame(
        columns=[
            "producer_username",
            "producer_user_id",
            "forwarder_username",
            "forwarder_user_id",
            "total_messages",
            "messages",
            "message_ids",
        ]
    )

    rows_to_append = []

    for index, row in community.iterrows():
        result_rows = df_network[
            (df_network["from_id"] == row["source"])
            & (df_network["forwarder_id"] == row["target"])
        ]

        producer_rows = df_user.loc[
            df_user["user_id"] == row["source"], ["username", "user_id"]
        ]
        producer = (
            producer_rows.iloc[0].to_dict()
            if not producer_rows.empty
            else {"username": f"anonymous{row['source']}", "user_id": row["source"]}
        )
        producer_username = producer["username"]
        producer_user_id = producer["user_id"]

        forwarder_rows = df_user.loc[
            df_user["user_id"] == row["target"], ["username", "user_id"]
        ]
        forwarder = (
            forwarder_rows.iloc[0].to_dict()
            if not forwarder_rows.empty
            else {"username": f"anonymous{row['target']}", "user_id": row["target"]}
        )
        forwarder_username = forwarder["username"]
        forwarder_user_id = forwarder["user_id"]

        # Depending on whether translation column exists
        text_col = (
            "text_translated" if "text_translated" in result_rows.columns else "text"
        )
        messages = (
            list(result_rows[text_col]) if text_col in result_rows.columns else []
        )

        message_ids = list(result_rows["unique_id"])
        total_messages = len(messages)

        rows_to_append.append(
            {
                "producer_username": producer_username,
                "producer_user_id": producer_user_id,
                "forwarder_username": forwarder_username,
                "forwarder_user_id": forwarder_user_id,
                "total_messages": total_messages,
                "messages": messages,
                "message_ids": message_ids,
            }
        )

    if rows_to_append:
        community_details = pd.concat(
            [community_details, pd.DataFrame(rows_to_append)], ignore_index=True
        )

    return community_details


def get_community_messages(prominent_communities, community_df, df_network, df_user):
    community_messages = pd.DataFrame(
        columns=["community_number", "messages", "messages_ids", "total_messages"]
    )
    rows_to_append = []

    for i in range(len(prominent_communities)):
        specific_community_result = get_specific_community_info(
            community_df, i, df_network, df_user
        )

        # For dataframes with list columns, sum() concatenates the lists
        messages_combined = (
            specific_community_result["messages"].sum()
            if not specific_community_result.empty
            else []
        )
        message_ids_combined = (
            specific_community_result["message_ids"].sum()
            if not specific_community_result.empty
            else []
        )
        total_messages = (
            specific_community_result["total_messages"].sum()
            if not specific_community_result.empty
            else 0
        )

        rows_to_append.append(
            {
                "community_number": i,
                "messages": messages_combined,
                "messages_ids": message_ids_combined,
                "total_messages": total_messages,
            }
        )

    if rows_to_append:
        community_messages = pd.concat(
            [community_messages, pd.DataFrame(rows_to_append)], ignore_index=True
        )

    return community_messages


def get_overall_community_messages_stat(
    date_col, promiment_communities, df_community, df_network
):
    community_messages_date = pd.DataFrame(columns=[date_col])
    rows_to_append = []

    for community_number in range(len(promiment_communities)):
        community = df_community[df_community["community_number"] == community_number]

        for index, row in community.iterrows():
            result_rows = df_network[
                (df_network["from_id"] == row["source"])
                & (df_network["forwarder_id"] == row["target"])
            ]
            if not result_rows.empty:
                rows_to_append.append(result_rows[[date_col]])

    if rows_to_append:
        community_messages_date = pd.concat(rows_to_append, ignore_index=True)

    if community_messages_date.empty:
        return {}

    community_messages_date["day"] = community_messages_date[date_col].apply(
        _extract_day
    )

    daily_messages = community_messages_date["day"].value_counts()
    if daily_messages.empty:
        return {}

    min_msg = daily_messages.min()
    day_of_min = daily_messages.idxmin()
    max_msg = daily_messages.max()
    day_of_max = daily_messages.idxmax()

    avg_messages = daily_messages.mean()
    std_messages = daily_messages.std()

    messages_stat = {
        "min_msg_count": min_msg,
        "day_of_min_msg": day_of_min,
        "max_msg_count": max_msg,
        "day_of_max_msg": day_of_max,
        "std_msg_count": std_messages,
        "avg_msg_count": avg_messages,
    }

    return messages_stat


def _extract_day(value):
    """Extract day from legacy tuple strings or pass numeric day values through."""
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            return parsed[2]
        except (SyntaxError, ValueError):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).day
    return value
