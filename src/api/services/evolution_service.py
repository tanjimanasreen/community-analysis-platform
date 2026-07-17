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
            frame = self.reader.read_csv(run_id, "community_transitions")
        except ArtifactNotFoundError as exc:
            raise ArtifactUnavailableError(run_id, "community_transitions") from exc
        records, total = self.reader.page(frame, limit=limit, offset=offset)
        for record in records:
            for field in ("start_month", "end_month"):
                if record.get(field) is not None:
                    record[field] = str(record[field]).zfill(2)
        return {
            "run_id": run_id,
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def persistent_communities(self, run_id: str) -> dict[str, Any]:
        transitions = self.transitions(run_id, limit=100000, offset=0)["records"]
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
        transitions = self.transitions(run_id, limit=100000, offset=0)["records"]
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
            if record.media_type != "text/csv":
                continue
            frame = self.reader.read_csv_record(run_id, record)
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
    normalized = normalize_value(value)
    if normalized is None:
        return set()
    if isinstance(normalized, (list, tuple, set)):
        return {str(item) for item in normalized}
    return {str(normalized)}
