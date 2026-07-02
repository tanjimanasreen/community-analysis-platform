"""Backward-compatible transition imports."""

from src.themes.community_transition import (
    find_matching_communities,
    get_community_transition,
    jaccard_similarity,
)
from src.themes.membership_changes import calculate_membership_changes
from src.themes.sankey_paths import (
    build_graph,
    dfs_all_paths,
    find_all_sankey_paths,
    get_path_info,
)

__all__ = [
    "build_graph",
    "calculate_membership_changes",
    "dfs_all_paths",
    "find_all_sankey_paths",
    "find_matching_communities",
    "get_community_transition",
    "get_path_info",
    "jaccard_similarity",
]
