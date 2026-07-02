import pandas as pd
import networkx as nx

from src.config.defaults import default_config


def get_network_graph(
    followee_follower_df,
    min_total_post=None,
    min_shared_post=None,
):
    """
    This function takes the follower_followee (source, target, and the weights) dataframe and 
    generates two different networks based on the different weights

    Input: Follower followee dataframe
    Output: Two networkx graphs 
    """
    data = followee_follower_df.copy()
    if min_total_post is None:
        min_total_post = default_config.graph.min_total_post
    if min_shared_post is None:
        min_shared_post = default_config.graph.min_shared_post
    
    data = data[(data['total_post'] >= min_total_post) & (data['shared_post'] >= min_shared_post)]
    
    G_absolute = nx.from_pandas_edgelist(data, "source", "target", ["shared_post"], create_using=nx.MultiDiGraph())
    G_percentage = nx.from_pandas_edgelist(data, "source", "target", ["weighted_post"], create_using=nx.MultiDiGraph())

    return G_absolute, G_percentage
