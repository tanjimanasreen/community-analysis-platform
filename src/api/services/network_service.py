from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.api.errors import (
    ArtifactNotFoundError,
    ArtifactUnavailableError,
    GraphRequestTooLargeError,
)
from src.api.services.artifact_reader import ArtifactReader, normalize_value


@dataclass(frozen=True)
class GraphLimits:
    max_nodes: int = 1000
    max_edges: int = 5000


class NetworkService:
    def __init__(self, reader: ArtifactReader, limits: GraphLimits):
        self.reader = reader
        self.limits = limits

    @staticmethod
    def artifact_key(metric: str) -> str:
        return "communities_absolute" if metric == "if" else "communities_weighted"

    def graph(
        self,
        run_id: str,
        *,
        metric: str,
        community_id: str | None,
        min_weight: float,
        max_nodes: int,
        max_edges: int,
    ) -> dict[str, Any]:
        self._check_limits(run_id, max_nodes, max_edges)
        key = self.artifact_key(metric)
        try:
            frame = self.reader.read_csv(run_id, key)
        except ArtifactNotFoundError as exc:
            raise ArtifactUnavailableError(run_id, key) from exc
        frame = _normalize_graph_frame(frame)
        if community_id is not None:
            frame = frame.loc[
                frame["community_number"].astype(str) == str(community_id)
            ]
        frame = frame.loc[frame["weight"] >= float(min_weight)]
        frame = frame.sort_values("weight", ascending=False, kind="stable")

        available_edges = len(frame)
        available_nodes = len(
            set(frame["source"].astype(str)) | set(frame["target"].astype(str))
        )

        selected_rows: list[dict[str, Any]] = []
        selected_nodes: set[str] = set()
        for row in frame.to_dict(orient="records"):
            if len(selected_rows) >= max_edges:
                break
            source = str(row["source"])
            target = str(row["target"])
            proposed = selected_nodes | {source, target}
            if len(proposed) > max_nodes:
                continue
            selected_nodes = proposed
            selected_rows.append(row)

        memberships: dict[str, set[str]] = defaultdict(set)
        edges = []
        for row in selected_rows:
            community = _optional_string(row.get("community_number"))
            source = str(row["source"])
            target = str(row["target"])
            if community is not None:
                memberships[source].add(community)
                memberships[target].add(community)
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "community_id": community,
                    "direction": _optional_string(row.get("direction")),
                    "weight": float(row["weight"]),
                }
            )

        nodes = [
            {"id": node, "community_ids": sorted(memberships.get(node, set()))}
            for node in sorted(selected_nodes)
        ]
        return {
            "run_id": run_id,
            "metric": metric,
            "community_id": community_id,
            "nodes": nodes,
            "edges": edges,
            "available_nodes": available_nodes,
            "available_edges": available_edges,
            "returned_nodes": len(nodes),
            "returned_edges": len(edges),
            "sampled": available_nodes > len(nodes) or available_edges > len(edges),
        }

    def communities(
        self,
        run_id: str,
        *,
        metric: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        key = self.artifact_key(metric)
        try:
            frame = _normalize_graph_frame(self.reader.read_csv(run_id, key))
        except ArtifactNotFoundError as exc:
            raise ArtifactUnavailableError(run_id, key) from exc

        communities = []
        for community_id, group in frame.groupby("community_number", sort=False):
            nodes = set(group["source"].astype(str)) | set(group["target"].astype(str))
            communities.append(
                {
                    "community_id": str(normalize_value(community_id)),
                    "node_count": len(nodes),
                    "edge_count": len(group),
                    "total_weight": float(group["weight"].sum()),
                }
            )
        communities.sort(
            key=lambda item: (
                -item["node_count"],
                -item["edge_count"],
                item["community_id"],
            )
        )
        total = len(communities)
        return {
            "run_id": run_id,
            "metric": metric,
            "communities": communities[offset : offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def community_detail(
        self,
        run_id: str,
        *,
        metric: str,
        community_id: str,
        max_nodes: int,
        max_edges: int,
        min_weight: float,
    ) -> dict[str, Any]:
        page = self.communities(run_id, metric=metric, limit=100000, offset=0)
        summary = next(
            (
                item
                for item in page["communities"]
                if item["community_id"] == str(community_id)
            ),
            None,
        )
        if summary is None:
            raise ArtifactUnavailableError(
                run_id, f"{self.artifact_key(metric)}:community:{community_id}"
            )
        graph = self.graph(
            run_id,
            metric=metric,
            community_id=community_id,
            min_weight=min_weight,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )
        return {
            "run_id": run_id,
            "metric": metric,
            "community": summary,
            "graph": graph,
        }

    def centrality(self, run_id: str, *, limit: int, offset: int) -> dict[str, Any]:
        frame = self.reader.read_csv(run_id, "user_centrality")
        records, total = self.reader.page(frame, limit=limit, offset=offset)
        return {
            "run_id": run_id,
            "artifact_key": "user_centrality",
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _check_limits(self, run_id: str, max_nodes: int, max_edges: int) -> None:
        if max_nodes > self.limits.max_nodes or max_edges > self.limits.max_edges:
            raise GraphRequestTooLargeError(
                run_id=run_id,
                requested_nodes=max_nodes,
                requested_edges=max_edges,
                max_nodes=self.limits.max_nodes,
                max_edges=self.limits.max_edges,
            )


def _normalize_graph_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"source", "target", "community_number", "weight"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"graph artifact schema mismatch; missing columns: {missing}")
    result = frame.copy(deep=False)
    result["weight"] = pd.to_numeric(result["weight"], errors="coerce").fillna(0.0)
    return result


def _optional_string(value: Any) -> str | None:
    normalized = normalize_value(value)
    return None if normalized is None else str(normalized)
