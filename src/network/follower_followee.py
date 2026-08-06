import pandas as pd


def extract_network_structure(df_network, followee_id):
    """
    Deprecated: Vectorized logic inside get_follower_followee_network handles this now.
    Included for backward compatibility if imported elsewhere.
    """
    temp_df = df_network[df_network["from_id"] == followee_id]
    total_post = len(temp_df)
    result = temp_df["forwarder_id"].value_counts().reset_index()
    result.columns = ["target", "shared_post"]

    # Removes the rows where the followee is also their message forwarder
    result = result[result["target"] != followee_id]
    result["source"] = followee_id
    result["total_post"] = total_post
    result["weighted_post"] = result["shared_post"] / total_post

    return result


def get_follower_followee_network(df_network):
    """
    This function takes the Network dataframe and creates the follower-followee dataframe along
    with their edges weight metrics for the NetworkX library to generate the graph.
    Here, source->followee user, target->follower user, total_post-> The total number of posts of the followee,
    shared_post-> The number of shared posts of the followee by the follower
    weighted_post-> The percentage number of the shared_post in respect to total_posts of the followee by the follower

    Input: Network dataframe
    Output: Follower-followee dataframe
    """
    if df_network.empty:
        return pd.DataFrame(
            columns=["target", "shared_post", "source", "total_post", "weighted_post"]
        )

    # 1. Total posts per followee
    total_posts = df_network.groupby("from_id").size().reset_index(name="total_post")

    # 2. Shared posts (source -> target edges)
    edges = (
        df_network.groupby(["from_id", "forwarder_id"])
        .size()
        .reset_index(name="shared_post")
    )

    # 3. Rename columns to match expected output
    edges = edges.rename(columns={"from_id": "source", "forwarder_id": "target"})

    # 4. Filter out self-loops
    edges = edges[edges["source"] != edges["target"]]

    if edges.empty:
        return pd.DataFrame(
            columns=["target", "shared_post", "source", "total_post", "weighted_post"]
        )

    # 5. Merge total posts to calculate weighted post
    result = edges.merge(total_posts, left_on="source", right_on="from_id", how="left")
    result["weighted_post"] = result["shared_post"] / result["total_post"]

    # Drop intermediate merge column and organize columns
    result = result.drop(columns=["from_id"])

    # Reorder columns to match legacy behavior (not strictly necessary, but safe)
    result = result[["target", "shared_post", "source", "total_post", "weighted_post"]]

    return result
