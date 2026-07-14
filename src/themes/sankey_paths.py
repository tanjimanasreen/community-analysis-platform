from collections import defaultdict
import pandas as pd

def get_path_info(matched_df: pd.DataFrame):
    if matched_df.empty:
        return [], [], [], []

    all_community = list(matched_df['start_month_community']) + list(matched_df['end_month_community'])
    all_community = list(set(all_community))

    source_ind = []
    target_ind = []
    score = []

    for _, row in matched_df.iterrows():
        source_ind.append(all_community.index(row['start_month_community']))
        target_ind.append(all_community.index(row['end_month_community']))
        score.append(row['jaccard_score'])

    return source_ind, target_ind, score, all_community

def build_graph(source_ind, target_ind):
    graph = defaultdict(list)
    out_degrees = defaultdict(int)
    in_degrees = defaultdict(int)

    for src, tgt in zip(source_ind, target_ind):
        graph[src].append(tgt)
        out_degrees[src] += 1
        in_degrees[tgt] += 1
        if tgt not in out_degrees:
            out_degrees[tgt] = 0
        if src not in in_degrees:
            in_degrees[src] = 0

    start_nodes = [node for node in out_degrees if in_degrees[node] == 0]
    end_nodes = [node for node in out_degrees if out_degrees[node] == 0]
    return graph, start_nodes, end_nodes

def dfs_all_paths(graph, start, end, path=None):
    if path is None:
        path = []
    path = path + [start]

    if start == end:
        return [path]
    if start not in graph:
        return []

    paths = []
    for next_node in graph[start]:
        if next_node not in path:
            new_paths = dfs_all_paths(graph, next_node, end, path)
            for new_path in new_paths:
                paths.append(new_path)
    return paths

def find_all_sankey_paths(source_ind, target_ind, all_community):
    graph, start_nodes, end_nodes = build_graph(source_ind, target_ind)
    all_paths = []
    for start in start_nodes:
        for end in end_nodes:
            paths = dfs_all_paths(graph, start, end)
            for path in paths:
                all_paths.append([all_community[node] for node in path])
    return all_paths
