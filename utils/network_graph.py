import pandas as pd
import networkx as nx

def get_network_graph(followee_follower_df):
    """
    This function takes the follower_followee (source, target, and the weights) dataframe and
    generates two different networks based on the different weights

    Input: Follower followee dataframe
    Output: Two networkx graphs
    """
    data = followee_follower_df.copy()

    min_total_post = 10
    min_shared_post = 5

    data = data[(data['total_post'] >= min_total_post) & (data['shared_post'] >= min_shared_post)]

    G_absolute = nx.from_pandas_edgelist(data, "source", "target", ["shared_post"], create_using=nx.MultiDiGraph())
    G_percentage = nx.from_pandas_edgelist(data, "source", "target", ["weighted_post"], create_using=nx.MultiDiGraph())

    return G_absolute, G_percentage


def graph_info(G):
    print("Is the Graph a multigraph: ", G.is_multigraph())
    print("Number of Nodes: ", G.number_of_nodes())
    print("Number of Edges: ", G.number_of_edges())
    print("Graph Density: ", nx.density(G))
    print("Is the Graph strongly connected: ", nx.is_strongly_connected(G))


def show_hightest_out_degree(G, df_user):
    out_degree_centrality = nx.centrality.out_degree_centrality(G)  # save results in a variable to use again
    out_node = (sorted(out_degree_centrality.items(), key=lambda item: item[1], reverse=True))[:5]
    # out_node

    df_out_node = pd.DataFrame(out_node, columns=['user_id', 'value'])
    df_out = pd.merge(df_user, df_out_node, on='user_id')

    # Find the max, min, and average degrees along with their nodes
    max_centrality = max(out_degree_centrality.items(), key=lambda item: item[1])
    min_centrality = min(out_degree_centrality.items(), key=lambda item: item[1])
    average_centrality = sum(out_degree_centrality.values()) / len(out_degree_centrality)

    # print(f" Max out-Centrality User: {df_user[df_user.user_id == max_centrality[0]].username.iloc[0]} ID: {max_centrality[0]} with value of {max_centrality[1]}")
    # print(f" Min out-Centrality User: {df_user[df_user.user_id == min_centrality[0]].username.iloc[0]} ID: {min_centrality[0]} with value of {min_centrality[1]}")
    # print(f" Avg out-Centrality Score: {average_centrality}")

    return {'max_out_degree_user': max_centrality[0], 'max_out_degree_val': max_centrality[1], 'min_out_degree_user': min_centrality[0], 'min_out_degree_val': min_centrality[1],'avg_out_degree_val': average_centrality}

def show_hightest_in_degree(G, df_user):
    in_degree_centrality = nx.centrality.in_degree_centrality(G)  # save results in a variable to use again
    in_node = (sorted(in_degree_centrality.items(), key=lambda item: item[1], reverse=True))[:5]
    # out_node

    df_in_node = pd.DataFrame(in_node, columns=['user_id', 'value'])
    df_in = pd.merge(df_user, df_in_node, on='user_id')

    # Find the max, min, and average degrees along with their nodes
    max_centrality = max(in_degree_centrality.items(), key=lambda item: item[1])
    min_centrality = min(in_degree_centrality.items(), key=lambda item: item[1])
    average_centrality = sum(in_degree_centrality.values()) / len(in_degree_centrality)

    # print(f" Max in-Centrality User: {df_user[df_user.user_id == max_centrality[0]].username.iloc[0]} ID: {max_centrality[0]} with value of {max_centrality[1]}")
    # print(f" Min in-Centrality User: {df_user[df_user.user_id == min_centrality[0]].username.iloc[0]} ID: {min_centrality[0]} with value of {min_centrality[1]}")
    # print(f" Avg in-Centrality Score: {average_centrality}")

    return {'max_in_degree_user': max_centrality[0], 'max_in_degree_val': max_centrality[1], 'min_in_degree_user': min_centrality[0], 'min_in_degree_val': min_centrality[1],'avg_in_degree_val': average_centrality}
