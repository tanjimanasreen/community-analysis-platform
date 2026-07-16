import pandas as pd


def extract_network_structure(df_network, followee_id):
    """
    This function calculates two weight metrics for every follower-followee edges and returns the result row
    Input: Network dataframe, followee user's id
    Output: Resulted dataframe for the followee user with the calculated metrics
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

    followee = list(df_network["from_id"].value_counts().index)
    results = []

    for followee_id in followee:
        result = extract_network_structure(df_network, followee_id)
        if len(result) > 0:
            results.append(result)

    if results:
        followee_follower_df = pd.concat(results, ignore_index=True)
    else:
        followee_follower_df = pd.DataFrame(
            columns=["target", "shared_post", "source", "total_post", "weighted_post"]
        )

    return followee_follower_df
