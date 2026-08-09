from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.api.errors import ArtifactNotFoundError, ArtifactUnavailableError
from src.api.services.artifact_reader import ArtifactReader, normalize_value
from src.artifacts.models import ArtifactCategory


class EvolutionService:
    def __init__(self, reader: ArtifactReader):
        self.reader = reader

    def transitions(self, run_id: str, *, limit: int, offset: int) -> dict[str, Any]:
        try:
            record = self.reader.get_record(run_id, "community_transitions")
        except ArtifactNotFoundError as exc:
            raise ArtifactUnavailableError(run_id, "community_transitions") from exc
        frame = self.reader.read_parquet_record_slice(
            run_id,
            record,
            offset=offset,
            limit=limit,
        )
        records, _ = self.reader.page(frame, limit=limit, offset=0)
        total = self.reader.parquet_row_count(run_id, record)
        for item in records:
            for field in ("start_month", "end_month"):
                if item.get(field) is not None:
                    item[field] = str(item[field]).zfill(2)
        return {
            "run_id": run_id,
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _all_transitions(self, run_id: str) -> list[dict[str, Any]]:
        """Load the authoritative transition table without an arbitrary cap."""
        try:
            record = self.reader.get_record(run_id, "community_transitions")
        except ArtifactNotFoundError as exc:
            raise ArtifactUnavailableError(run_id, "community_transitions") from exc
        frame = self.reader.read_parquet_record(run_id, record)
        records, _ = self.reader.page(frame, limit=len(frame), offset=0)
        for item in records:
            for field in ("start_month", "end_month"):
                if item.get(field) is not None:
                    item[field] = str(item[field]).zfill(2)
        return records

    def paths(self, run_id: str) -> dict[str, Any]:
        """Read persisted DFS community paths; never reconstruct them in the API."""
        frame = self._read_required_parquet(run_id, "community_paths")
        records, _ = self.reader.page(frame, limit=len(frame), offset=0)
        by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in records:
            by_path[str(item.get("path_id", ""))].append(item)

        paths: list[dict[str, Any]] = []
        for path_id, items in by_path.items():
            ordered = sorted(
                items,
                key=lambda item: (
                    int(item.get("display_order") or 0),
                    int(item.get("step_index") or 0),
                ),
            )
            scores = [
                score
                for item in ordered
                if (score := _nullable_float(item.get("jaccard_from_previous")))
                is not None
            ]
            retained = sum(
                (_nullable_int(item.get("retained_count")) or 0) for item in ordered
            )
            steps = []
            for item in ordered:
                steps.append(
                    {
                        "step_index": int(item.get("step_index") or 0),
                        "month": str(item.get("month") or ""),
                        "community_key": str(item.get("community_key") or ""),
                        "community_id": str(item.get("community_id") or ""),
                        "member_count": int(item.get("member_count") or 0),
                        "members": _as_list(item.get("members")),
                        "previous_month": _nullable_text(item.get("previous_month")),
                        "previous_community_key": _nullable_text(
                            item.get("previous_community_key")
                        ),
                        "previous_community_id": _nullable_text(
                            item.get("previous_community_id")
                        ),
                        "jaccard_from_previous": _nullable_float(
                            item.get("jaccard_from_previous")
                        ),
                        "retained_count": _nullable_int(item.get("retained_count")),
                        "absolute_theme": _nullable_text(item.get("absolute_theme"))
                        or "",
                        "weighted_theme": _nullable_text(item.get("weighted_theme"))
                        or "",
                        "general_theme": _nullable_text(item.get("general_theme"))
                        or "",
                    }
                )
            paths.append(
                {
                    "path_id": path_id,
                    "display_order": int(ordered[0].get("display_order") or 0),
                    "duration": len(ordered),
                    "transition_count": max(0, len(ordered) - 1),
                    "average_jaccard": (
                        round(sum(scores) / len(scores), 6) if scores else 0.0
                    ),
                    "total_retained_members": retained,
                    "months": [str(item.get("month") or "") for item in ordered],
                    "steps": steps,
                }
            )
        paths.sort(key=lambda item: (item["display_order"], item["path_id"]))
        return {
            "run_id": run_id,
            "paths": paths,
            "total": len(paths),
            "methodology": self._methodology(run_id),
        }

    def path_membership(self, run_id: str, path_id: str) -> dict[str, Any]:
        frame = self._read_required_parquet(run_id, "community_path_membership")
        if "path_id" in frame.columns:
            frame = frame[frame["path_id"].astype(str) == str(path_id)]
        records, _ = self.reader.page(frame, limit=len(frame), offset=0)
        normalized = []
        for item in sorted(records, key=lambda row: int(row.get("step_index") or 0)):
            normalized.append(
                {
                    "path_id": str(item.get("path_id") or ""),
                    "display_order": int(item.get("display_order") or 0),
                    "step_index": int(item.get("step_index") or 0),
                    "month": str(item.get("month") or ""),
                    "community_key": str(item.get("community_key") or ""),
                    "community_id": str(item.get("community_id") or ""),
                    "member_count": int(item.get("member_count") or 0),
                    "size_delta": _nullable_int(item.get("size_delta")),
                    "existing_count": int(item.get("existing_count") or 0),
                    "new_count": int(item.get("new_count") or 0),
                    "lost_count": int(item.get("lost_count") or 0),
                    "reappearing_count": int(item.get("reappearing_count") or 0),
                    "members": _as_list(item.get("members")),
                    "existing_members": _as_list(item.get("existing_members")),
                    "new_members": _as_list(item.get("new_members")),
                    "lost_members": _as_list(item.get("lost_members")),
                    "reappearing_members": _as_list(item.get("reappearing_members")),
                }
            )
        return {"run_id": run_id, "path_id": path_id, "records": normalized}

    def path_theme_similarity(
        self, run_id: str, path_id: str, *, theme_type: str
    ) -> dict[str, Any]:
        frame = self._read_required_parquet(run_id, "community_path_theme_similarity")
        if "path_id" in frame.columns:
            frame = frame[frame["path_id"].astype(str) == str(path_id)]
        if "theme_type" in frame.columns:
            frame = frame[frame["theme_type"].astype(str) == str(theme_type)]
        records, _ = self.reader.page(frame, limit=len(frame), offset=0)
        if not records:
            return {
                "run_id": run_id,
                "path_id": path_id,
                "theme_type": theme_type,
                "months": [],
                "communities": [],
                "themes": [],
                "matrix": [],
            }

        indexes: dict[int, dict[str, str]] = {}
        for item in records:
            left_index = int(item.get("left_step_index") or 0)
            right_index = int(item.get("right_step_index") or 0)
            indexes.setdefault(
                left_index,
                {
                    "month": str(item.get("left_month") or ""),
                    "community": str(item.get("left_community_key") or ""),
                    "theme": str(item.get("left_theme") or ""),
                },
            )
            indexes.setdefault(
                right_index,
                {
                    "month": str(item.get("right_month") or ""),
                    "community": str(item.get("right_community_key") or ""),
                    "theme": str(item.get("right_theme") or ""),
                },
            )
        order = sorted(indexes)
        position = {step: index for index, step in enumerate(order)}
        matrix = [[0.0 for _ in order] for _ in order]
        for item in records:
            left = position[int(item.get("left_step_index") or 0)]
            right = position[int(item.get("right_step_index") or 0)]
            score = float(item.get("cosine_similarity") or 0.0)
            matrix[left][right] = score
            matrix[right][left] = score
        first = records[0]
        return {
            "run_id": run_id,
            "path_id": path_id,
            "theme_type": theme_type,
            "months": [indexes[step]["month"] for step in order],
            "communities": [indexes[step]["community"] for step in order],
            "themes": [indexes[step]["theme"] for step in order],
            "matrix": matrix,
            "embedding_provider": _nullable_text(first.get("embedding_provider")),
            "embedding_model": _nullable_text(first.get("embedding_model")),
            "embedding_model_revision": _nullable_text(
                first.get("embedding_model_revision")
            ),
        }

    def persistent_communities(self, run_id: str) -> dict[str, Any]:
        # New runs expose the exact persisted DFS paths.  Keep the previous
        # connected-component fallback only for old immutable run bundles.
        try:
            paths = self.paths(run_id)["paths"]
        except ArtifactUnavailableError:
            paths = None
        if paths is not None:
            communities = [
                {
                    "persistent_id": item["path_id"],
                    "communities": [step["community_key"] for step in item["steps"]],
                    "months": item["months"],
                    "transition_count": item["transition_count"],
                    "average_jaccard": item["average_jaccard"],
                }
                for item in paths
            ]
            return {
                "run_id": run_id,
                "communities": communities,
                "total": len(communities),
            }

        transitions = self._all_transitions(run_id)
        components = _transition_components(transitions)
        result = []
        for index, nodes in enumerate(components, start=1):
            component_edges = [
                row
                for row in transitions
                if _node(row, "start") in nodes or _node(row, "end") in nodes
            ]
            scores = [float(row.get("jaccard_score") or 0.0) for row in component_edges]
            result.append(
                {
                    "persistent_id": f"persistent-{index}",
                    "communities": sorted(nodes),
                    "months": sorted({node.split(":", 1)[0] for node in nodes}),
                    "transition_count": len(component_edges),
                    "average_jaccard": (
                        round(sum(scores) / len(scores), 6) if scores else 0.0
                    ),
                }
            )
        result.sort(key=lambda item: (-len(item["months"]), item["persistent_id"]))
        return {"run_id": run_id, "communities": result, "total": len(result)}

    def membership_changes(self, run_id: str) -> dict[str, Any]:
        transitions = self._all_transitions(run_id)
        result = []
        for row in transitions:
            start_members = _as_set(row.get("start_month_members"))
            end_members = _as_set(row.get("end_month_members"))
            common = _as_set(row.get("common_members")) or start_members & end_members
            result.append(
                {
                    "start_month": str(row.get("start_month", "")),
                    "end_month": str(row.get("end_month", "")),
                    "start_community": str(row.get("start_month_community", "")),
                    "end_community": str(row.get("end_month_community", "")),
                    "retained_count": len(common),
                    "joined_count": len(end_members - common),
                    "exited_count": len(start_members - common),
                    "start_count": int(
                        row.get("total_start_month_members") or len(start_members)
                    ),
                    "end_count": int(
                        row.get("total_end_month_members") or len(end_members)
                    ),
                }
            )
        return {"run_id": run_id, "records": result, "total": len(result)}

    def theme_similarity(self, run_id: str) -> dict[str, Any]:
        data_records = self.reader.find_records(
            run_id, path_contains="theme_similarity", category=ArtifactCategory.DATA
        )
        matrix = None
        labels: list[str] = []
        for record in data_records:
            if record.key == "community_path_theme_similarity":
                continue
            frame = self.reader.read_parquet_record(run_id, record)
            if frame.empty:
                continue
            labels = [str(column) for column in frame.columns]
            try:
                matrix = frame.astype(float).values.tolist()
            except (TypeError, ValueError):
                matrix = None
            break

        report_records = self.reader.find_records(
            run_id,
            path_contains="theme_similarity",
            category=ArtifactCategory.REPORT,
        )
        artifacts = [
            {
                "artifact_key": record.key,
                "media_type": record.media_type,
                "path": record.path,
            }
            for record in report_records
        ]
        if matrix is None and not artifacts:
            raise ArtifactUnavailableError(run_id, "theme_similarity")
        return {
            "run_id": run_id,
            "matrix": matrix,
            "labels": labels,
            "artifacts": artifacts,
        }

    def _read_required_parquet(self, run_id: str, artifact_key: str):
        try:
            record = self.reader.get_record(run_id, artifact_key)
        except ArtifactNotFoundError as exc:
            raise ArtifactUnavailableError(run_id, artifact_key) from exc
        return self.reader.read_parquet_record(run_id, record)

    def _methodology(self, run_id: str) -> dict[str, Any]:
        config = self.reader.read_safe_config(run_id)
        content_type = str(config.get("content_type") or "")
        theme = config.get("theme", {})
        theme = theme if isinstance(theme, dict) else {}
        threshold_key = (
            "reply_transition_threshold"
            if content_type == "reply"
            else "transition_threshold"
        )
        return {
            "content_type": content_type,
            "transition_threshold": _nullable_float(theme.get(threshold_key)),
            "similarity_provider": _nullable_text(theme.get("similarity_provider")),
            "similarity_model": _nullable_text(theme.get("similarity_model")),
            "similarity_model_revision": _nullable_text(
                theme.get("similarity_model_revision")
            ),
        }


def _transition_components(rows: list[dict[str, Any]]) -> list[set[str]]:
    parent: dict[str, str] = {}

    def find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for row in rows:
        union(_node(row, "start"), _node(row, "end"))

    groups: dict[str, set[str]] = defaultdict(set)
    for node in parent:
        groups[find(node)].add(node)
    return list(groups.values())


def _node(row: dict[str, Any], side: str) -> str:
    return f"{row.get(f'{side}_month', '')}:{row.get(f'{side}_month_community', '')}"


def _as_set(value: Any) -> set[str]:
    return set(_as_list(value))


def _as_list(value: Any) -> list[str]:
    normalized = normalize_value(value)
    if normalized is None:
        return []
    if isinstance(normalized, (list, tuple, set)):
        return [str(item) for item in normalized]
    return [str(normalized)]


def _nullable_text(value: Any) -> str | None:
    normalized = normalize_value(value)
    if normalized is None or normalized == "":
        return None
    return str(normalized)


def _nullable_float(value: Any) -> float | None:
    normalized = normalize_value(value)
    if normalized is None or normalized == "":
        return None
    try:
        return float(normalized)
    except (TypeError, ValueError):
        return None


def _nullable_int(value: Any) -> int | None:
    normalized = normalize_value(value)
    if normalized is None or normalized == "":
        return None
    try:
        return int(normalized)
    except (TypeError, ValueError):
        return None
