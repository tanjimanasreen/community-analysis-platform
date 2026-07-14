import pandas as pd
import networkx as nx

def graph_info(G):
    info = {
        "is_multigraph": G.is_multigraph(),
        "number_of_nodes": G.number_of_nodes(),
        "number_of_edges": G.number_of_edges(),
        "density": nx.density(G) if G.number_of_nodes() > 0 else 0,
        "is_strongly_connected": nx.is_strongly_connected(G) if G.number_of_nodes() > 0 else False
    }
    return info

def show_hightest_out_degree(G, df_user):
    out_degree_centrality = nx.centrality.out_degree_centrality(G)
    if not out_degree_centrality:
        return {}

    out_node = (sorted(out_degree_centrality.items(), key=lambda item: item[1], reverse=True))[:5]

    df_out_node = pd.DataFrame(out_node, columns=['user_id', 'value'])
    df_out = pd.merge(df_user, df_out_node, on='user_id')

    max_centrality = max(out_degree_centrality.items(), key=lambda item: item[1])
    min_centrality = min(out_degree_centrality.items(), key=lambda item: item[1])
    average_centrality = sum(out_degree_centrality.values()) / len(out_degree_centrality)

    return {
        'max_out_degree_user': max_centrality[0],
        'max_out_degree_val': max_centrality[1],
        'min_out_degree_user': min_centrality[0],
        'min_out_degree_val': min_centrality[1],
        'avg_out_degree_val': average_centrality
    }

def show_hightest_in_degree(G, df_user):
    in_degree_centrality = nx.centrality.in_degree_centrality(G)
    if not in_degree_centrality:
        return {}

    in_node = (sorted(in_degree_centrality.items(), key=lambda item: item[1], reverse=True))[:5]

    df_in_node = pd.DataFrame(in_node, columns=['user_id', 'value'])
    df_in = pd.merge(df_user, df_in_node, on='user_id')

    max_centrality = max(in_degree_centrality.items(), key=lambda item: item[1])
    min_centrality = min(in_degree_centrality.items(), key=lambda item: item[1])
    average_centrality = sum(in_degree_centrality.values()) / len(in_degree_centrality)

    return {
        'max_in_degree_user': max_centrality[0],
        'max_in_degree_val': max_centrality[1],
        'min_in_degree_user': min_centrality[0],
        'min_in_degree_val': min_centrality[1],
        'avg_in_degree_val': average_centrality
    }

def get_community_network_centrality(G, df_user):
    graph_info(G)
    result_out = show_hightest_out_degree(G, df_user)
    result_in = show_hightest_in_degree(G, df_user)

    if isinstance(result_in, dict) and isinstance(result_out, dict):
        return {**result_in, **result_out}
    return {}

def get_prominent_communities_stat(prominent_communities, G, df_user):
    if not prominent_communities:
        return {}
    all_community_nodes = set().union(*prominent_communities)
    subgraph = G.subgraph(all_community_nodes)
    degree_result = get_community_network_centrality(subgraph, df_user)
    return degree_result
