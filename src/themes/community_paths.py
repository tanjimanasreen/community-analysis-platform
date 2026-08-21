from __future__ import annotations

import ast
import hashlib
import json
from collections import OrderedDict
from typing import Any, Iterable

import pandas as pd

from src.themes.membership_changes import calculate_membership_changes
from src.themes.sankey_paths import find_all_sankey_paths, get_path_info
from src.themes.theme_similarity import calculate_sentence_similarity_with_missing

COMMUNITY_PATH_COLUMNS = [
    "path_id",
    "display_order",
    "step_index",
    "month",
    "community_key",
    "community_id",
    "member_count",
    "members",
    "previous_month",
    "previous_community_key",
    "previous_community_id",
    "jaccard_from_previous",
    "retained_count",
    "absolute_theme",
    "weighted_theme",
    "general_theme",
]

COMMUNITY_PATH_MEMBERSHIP_COLUMNS = [
    "path_id",
    "display_order",
    "step_index",
    "month",
    "community_key",
    "community_id",
    "member_count",
    "size_delta",
    "existing_count",
    "new_count",
    "lost_count",
    "reappearing_count",
    "members",
    "existing_members",
    "new_members",
    "lost_members",
    "reappearing_members",
]

COMMUNITY_PATH_THEME_SIMILARITY_COLUMNS = [
    "path_id",
    "display_order",
    "theme_type",
    "left_step_index",
    "right_step_index",
    "left_month",
    "right_month",
    "left_community_key",
    "right_community_key",
    "left_theme",
    "right_theme",
    "cosine_similarity",
    "embedding_provider",
    "embedding_model",
    "embedding_model_revision",
]

_THEME_COLUMNS = {
    "absolute": "absolute_theme",
    "weighted": "weighted_theme",
    "general": "general_theme",
}


def build_community_path_artifact(transitions: pd.DataFrame) -> pd.DataFrame:
    """Materialize the thesis-preserving start-to-end DFS community paths.

    Path discovery deliberately delegates to the existing Sankey-path functions so
    the analytical behavior remains identical to the thesis implementation.  This
    function only converts those paths into a deterministic, dashboard-friendly
    table and does not change transition acceptance or Jaccard semantics.
    """
    if transitions.empty:
        return pd.DataFrame(columns=COMMUNITY_PATH_COLUMNS)

    source_ind, target_ind, _, all_community = get_path_info(transitions)
    raw_paths = find_all_sankey_paths(source_ind, target_ind, all_community)
    if not raw_paths:
        return pd.DataFrame(columns=COMMUNITY_PATH_COLUMNS)

    node_metadata = _node_metadata(transitions)
    edge_metadata = _edge_metadata(transitions)
    ranked_paths = sorted(
        raw_paths,
        key=lambda path: (
            -len(path),
            -sum(
                _retained_count(edge_metadata.get((left, right), {}))
                for left, right in zip(path, path[1:])
            ),
            str(path[0]) if path else "",
            tuple(map(str, path)),
        ),
    )

    records: list[dict[str, Any]] = []
    for display_order, path in enumerate(ranked_paths, start=1):
        path_id = _stable_path_id(path)
        for step_index, community_key in enumerate(path):
            metadata = node_metadata.get(str(community_key), {})
            previous_key = str(path[step_index - 1]) if step_index > 0 else None
            edge = (
                edge_metadata.get((previous_key, str(community_key)), {})
                if previous_key
                else {}
            )
            members = _members(metadata.get("members"))
            month = str(metadata.get("month") or _month_from_key(str(community_key)))
            community_id = str(
                metadata.get("community_id")
                or _community_id_from_key(str(community_key), month)
            )
            previous_month = None
            previous_community_id = None
            if previous_key:
                previous_metadata = node_metadata.get(previous_key, {})
                previous_month = str(
                    previous_metadata.get("month") or _month_from_key(previous_key)
                )
                previous_community_id = str(
                    previous_metadata.get("community_id")
                    or _community_id_from_key(previous_key, previous_month)
                )
            records.append(
                {
                    "path_id": path_id,
                    "display_order": display_order,
                    "step_index": step_index,
                    "month": month,
                    "community_key": str(community_key),
                    "community_id": community_id,
                    "member_count": len(members),
                    "members": _json_list(members),
                    "previous_month": previous_month,
                    "previous_community_key": previous_key,
                    "previous_community_id": previous_community_id,
                    "jaccard_from_previous": _finite_float(edge.get("jaccard_score")),
                    "retained_count": _retained_count(edge) if previous_key else None,
                    "absolute_theme": _theme_text(metadata.get("absolute_theme")),
                    "weighted_theme": _theme_text(metadata.get("weighted_theme")),
                    "general_theme": _theme_text(metadata.get("general_theme")),
                }
            )
    return pd.DataFrame(records, columns=COMMUNITY_PATH_COLUMNS)


def build_membership_mobility_artifact(path_frame: pd.DataFrame) -> pd.DataFrame:
    """Persist per-path member states using the existing thesis mobility logic."""
    if path_frame.empty:
        return pd.DataFrame(columns=COMMUNITY_PATH_MEMBERSHIP_COLUMNS)

    records: list[dict[str, Any]] = []
    for path_id, group in path_frame.groupby("path_id", sort=False):
        ordered = group.sort_values("step_index", kind="stable")
        communities: "OrderedDict[str, list[Any]]" = OrderedDict()
        for row in ordered.itertuples(index=False):
            communities[str(row.community_key)] = _members(row.members)
        changes = calculate_membership_changes(communities)
        previous_size: int | None = None
        for row in ordered.itertuples(index=False):
            key = str(row.community_key)
            change = changes[key]
            members = _sorted_values(change["members"])
            existing = _sorted_values(change["existing_members"])
            new = _sorted_values(change["new_members"])
            lost = _sorted_values(change["lost_members"])
            reappearing = _sorted_values(change["reappearing_members"])
            member_count = len(members)
            records.append(
                {
                    "path_id": str(path_id),
                    "display_order": int(row.display_order),
                    "step_index": int(row.step_index),
                    "month": str(row.month),
                    "community_key": key,
                    "community_id": str(row.community_id),
                    "member_count": member_count,
                    "size_delta": (
                        None if previous_size is None else member_count - previous_size
                    ),
                    "existing_count": len(existing),
                    "new_count": len(new),
                    "lost_count": len(lost),
                    "reappearing_count": len(reappearing),
                    "members": _json_list(members),
                    "existing_members": _json_list(existing),
                    "new_members": _json_list(new),
                    "lost_members": _json_list(lost),
                    "reappearing_members": _json_list(reappearing),
                }
            )
            previous_size = member_count
    return pd.DataFrame(records, columns=COMMUNITY_PATH_MEMBERSHIP_COLUMNS)


def build_path_theme_similarity_artifact(
    path_frame: pd.DataFrame,
    *,
    model,
    model_name: str,
    embedding_provider: str,
    embedding_model: str,
    embedding_model_revision: str,
) -> pd.DataFrame:
    """Compute the same sentence-embedding cosine similarity per persisted path.

    The strings passed to the embedder are the raw generated theme strings carried
    by the transition artifact, matching the existing heatmap methodology.
    """
    if path_frame.empty:
        return pd.DataFrame(columns=COMMUNITY_PATH_THEME_SIMILARITY_COLUMNS)

    records: list[dict[str, Any]] = []
    for path_id, group in path_frame.groupby("path_id", sort=False):
        ordered = group.sort_values("step_index", kind="stable").reset_index(drop=True)
        display_order = int(ordered.iloc[0]["display_order"])
        for theme_type, column in _THEME_COLUMNS.items():
            themes = [_theme_text(value) for value in ordered[column].tolist()]
            matrix = calculate_sentence_similarity_with_missing(
                themes, model_name=model_name, model=model
            )
            for left_index in range(len(ordered)):
                for right_index in range(left_index, len(ordered)):
                    left = ordered.iloc[left_index]
                    right = ordered.iloc[right_index]
                    records.append(
                        {
                            "path_id": str(path_id),
                            "display_order": display_order,
                            "theme_type": theme_type,
                            "left_step_index": int(left["step_index"]),
                            "right_step_index": int(right["step_index"]),
                            "left_month": str(left["month"]),
                            "right_month": str(right["month"]),
                            "left_community_key": str(left["community_key"]),
                            "right_community_key": str(right["community_key"]),
                            "left_theme": themes[left_index],
                            "right_theme": themes[right_index],
                            "cosine_similarity": _finite_float(
                                matrix[left_index][right_index]
                            ),
                            "embedding_provider": embedding_provider,
                            "embedding_model": embedding_model,
                            "embedding_model_revision": embedding_model_revision,
                        }
                    )
    return pd.DataFrame(records, columns=COMMUNITY_PATH_THEME_SIMILARITY_COLUMNS)


def paths_as_lists(path_frame: pd.DataFrame) -> list[list[str]]:
    """Return persisted paths in display order for legacy visualization functions."""
    if path_frame.empty:
        return []
    result: list[list[str]] = []
    for _, group in path_frame.sort_values(["display_order", "step_index"]).groupby(
        "path_id", sort=False
    ):
        result.append([str(value) for value in group["community_key"].tolist()])
    return result


def _node_metadata(transitions: pd.DataFrame) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for row in transitions.to_dict(orient="records"):
        start_key = str(row.get("start_month_community", ""))
        end_key = str(row.get("end_month_community", ""))
        metadata.setdefault(
            start_key,
            {
                "month": row.get("start_month"),
                "community_id": _community_id_from_key(
                    start_key, str(row.get("start_month", ""))
                ),
                "members": row.get("start_month_members"),
                "absolute_theme": row.get("start_month_absolute_theme"),
                "weighted_theme": row.get("start_month_weighted_theme"),
                "general_theme": row.get("start_month_general_theme"),
            },
        )
        metadata.setdefault(
            end_key,
            {
                "month": row.get("end_month"),
                "community_id": _community_id_from_key(
                    end_key, str(row.get("end_month", ""))
                ),
                "members": row.get("end_month_members"),
                "absolute_theme": row.get("end_month_absolute_theme"),
                "weighted_theme": row.get("end_month_weighted_theme"),
                "general_theme": row.get("end_month_general_theme"),
            },
        )
    return metadata


def _edge_metadata(transitions: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in transitions.to_dict(orient="records"):
        key = (
            str(row.get("start_month_community", "")),
            str(row.get("end_month_community", "")),
        )
        result.setdefault(key, row)
    return result


def _stable_path_id(path: Iterable[Any]) -> str:
    payload = "\x1f".join(str(value) for value in path)
    return f"path_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _retained_count(edge: dict[str, Any]) -> int:
    return len(_members(edge.get("common_members")))


def _members(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return _sorted_values(value)
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
        parsed = value.tolist()
        return parsed if isinstance(parsed, list) else [parsed]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(stripped)
            except (json.JSONDecodeError, SyntaxError, ValueError, TypeError):
                continue
            if isinstance(parsed, (list, tuple, set)):
                return list(parsed)
        return []
    return []


def _json_list(values: Iterable[Any]) -> str:
    return json.dumps(list(values), ensure_ascii=False, default=str)


def _sorted_values(values: Iterable[Any]) -> list[Any]:
    return sorted(list(values), key=lambda value: str(value))


def _theme_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _finite_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if pd.notna(parsed) else None


def _month_from_key(community_key: str) -> str:
    return community_key.split("_", 1)[0] if "_" in community_key else community_key


def _community_id_from_key(community_key: str, month: str) -> str:
    prefix = f"{month}_" if month else ""
    if prefix and community_key.startswith(prefix):
        return community_key[len(prefix) :]
    return community_key.split("_", 1)[1] if "_" in community_key else community_key
