from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd

from src.api.errors import (
    ArtifactNotFoundError,
    ArtifactUnavailableError,
    GraphRequestTooLargeError,
    InvalidFilterError,
)
from src.api.services.artifact_reader import ArtifactReader, normalize_value
from src.api.services.periods import (
    default_year,
    discover_periods,
    record_period,
    select_period_record,
)


@dataclass(frozen=True)
class GraphLimits:
    max_nodes: int = 1000
    max_edges: int = 5000


_GRAPH_COLUMNS = ["source", "target", "community_number", "direction", "weight"]
_MEMBERSHIP_COLUMNS = ["source", "target", "community_number"]
_SUMMARY_REQUIRED_COLUMNS = [
    "community_id",
    "node_count",
    "edge_count",
    "total_weight",
]
_SUMMARY_LAYOUT_COLUMNS = ["x", "y"]
_NODE_INDEX_COLUMNS = ["node_id", "x", "y"]
_INTERACTION_COLUMNS = [
    "source_community_id",
    "target_community_id",
    "user_pair_count",
    "interaction_count",
    "total_weight",
    "source_user_count",
    "target_user_count",
]
_CENTRALITY_COLUMNS = ["month", "absolute", "weighted"]
_NETWORK_VIEWS = {"users", "communities"}
_SAMPLING_STRATEGIES = {"community_balanced", "strongest_edges", "full_graph"}


class NetworkService:
    def __init__(self, reader: ArtifactReader, limits: GraphLimits):
        self.reader = reader
        self.limits = limits

    @staticmethod
    def artifact_key(metric: str) -> str:
        return "communities_absolute" if metric == "if" else "communities_weighted"

    @staticmethod
    def summary_key(metric: str) -> str:
        return (
            "community_summary_absolute"
            if metric == "if"
            else "community_summary_weighted"
        )

    @staticmethod
    def sample_key(metric: str) -> str:
        return (
            "community_graph_sample_absolute"
            if metric == "if"
            else "community_graph_sample_weighted"
        )

    @staticmethod
    def node_index_key(metric: str) -> str:
        return (
            "community_node_index_absolute"
            if metric == "if"
            else "community_node_index_weighted"
        )

    @staticmethod
    def interaction_key(metric: str) -> str:
        return (
            "community_interactions_absolute"
            if metric == "if"
            else "community_interactions_weighted"
        )

    def _records_for_key(self, run_id: str, key: str, *, period: str | None = None):
        try:
            records = [self.reader.get_record(run_id, key)]
        except ArtifactNotFoundError:
            records = self.reader.find_records(run_id, key_prefix=f"{key}_")
            if not records:
                raise ArtifactUnavailableError(run_id, key)
            records = sorted(records, key=lambda record: record.key)
        if period is None:
            return records

        manifest = self.reader.catalog.get_manifest(run_id)
        config = self.reader.read_safe_config(run_id)
        available_periods = discover_periods(manifest, config)
        if period not in available_periods:
            availability = ", ".join(available_periods) or "none"
            raise InvalidFilterError(
                f"Period {period} is not available for this run. "
                f"Available periods: {availability}.",
                run_id=run_id,
            )
        fallback_year = default_year(config, manifest)
        if len(records) == 1 and records[0].key == key:
            candidate = record_period(records[0], fallback_year=fallback_year)
            if candidate == period:
                return records
            if (
                candidate is None
                and len(available_periods) == 1
                and available_periods[0] == period
            ):
                return records
        return [
            select_period_record(
                records,
                period=period,
                fallback_year=fallback_year,
                run_id=run_id,
                artifact_key=key,
            )
        ]

    def _read_graph_frame(
        self,
        run_id: str,
        metric: str,
        *,
        min_weight: float = 0.0,
        community_id: str | None = None,
        period: str | None = None,
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        key = self.artifact_key(metric)
        filters: list[tuple[str, str, Any]] = []
        if min_weight > 0:
            filters.append(("weight", ">=", float(min_weight)))
        if community_id is not None:
            normalized_community: str | int = str(community_id)
            if str(community_id).lstrip("-").isdigit():
                normalized_community = int(community_id)
            filters.append(("community_number", "==", normalized_community))
        parquet_filters = filters or None
        selected_columns = columns or _GRAPH_COLUMNS
        frames = []
        for record in self._records_for_key(run_id, key, period=period):
            try:
                frame = self.reader.read_parquet_record(
                    run_id,
                    record,
                    columns=selected_columns,
                    filters=parquet_filters,
                )
            except (TypeError, ValueError):
                # Compatibility path for older graph artifacts whose weight or
                # community columns used a non-numeric logical type.
                frame = self.reader.read_parquet_record(
                    run_id, record, columns=selected_columns
                )
            frames.append(frame)
        return pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]

    def _read_graph_sample_frame(
        self, run_id: str, metric: str, *, period: str | None = None
    ) -> (
        tuple[pd.DataFrame, int, int, pd.DataFrame, dict[str, tuple[float, float]]]
        | None
    ):
        """Read additive dashboard edges plus exact summary/index totals."""
        try:
            sample_records = self._records_for_key(
                run_id, self.sample_key(metric), period=period
            )
            summary_records = self._records_for_key(
                run_id, self.summary_key(metric), period=period
            )
        except ArtifactUnavailableError:
            return None
        if not sample_records or not summary_records:
            return None

        sample_frames = [
            self.reader.read_parquet_record(run_id, record, columns=_GRAPH_COLUMNS)
            for record in sample_records
        ]
        summary_frames = [
            self.reader.read_parquet_record(run_id, record)
            for record in summary_records
        ]
        frame = (
            pd.concat(sample_frames, ignore_index=True)
            if len(sample_frames) > 1
            else sample_frames[0]
        )
        summary = (
            pd.concat(summary_frames, ignore_index=True)
            if len(summary_frames) > 1
            else summary_frames[0]
        )
        available_edges = int(
            pd.to_numeric(summary["edge_count"], errors="coerce").fillna(0).sum()
        )

        try:
            node_records = self._records_for_key(
                run_id, self.node_index_key(metric), period=period
            )
        except ArtifactUnavailableError:
            node_records = []
        node_layouts: dict[str, tuple[float, float]] = {}
        if node_records:
            node_ids: set[str] = set()
            for record in node_records:
                try:
                    node_frame = self.reader.read_parquet_record(
                        run_id, record, columns=_NODE_INDEX_COLUMNS
                    )
                except (ValueError, TypeError, KeyError):
                    # Fallback for old artifacts without x and y columns
                    node_frame = self.reader.read_parquet_record(
                        run_id, record, columns=["node_id"]
                    )
                for row in node_frame.to_dict(orient="records"):
                    if pd.isna(row.get("node_id")):
                        continue
                    node_id = _identifier_string(row["node_id"])
                    node_ids.add(node_id)
                    if (
                        "x" in row
                        and "y" in row
                        and not pd.isna(row["x"])
                        and not pd.isna(row["y"])
                    ):
                        node_layouts[node_id] = (float(row["x"]), float(row["y"]))
            available_nodes = len(node_ids)
            # Store the node layouts in the summary dict or as an extra return value.
            # To avoid changing the return type signature radically everywhere, we can just return it in the tuple.
            # Wait, the return type of _read_graph_sample_frame is tuple[pd.DataFrame, int, int, pd.DataFrame] | None.
            # I can't easily change it without updating other callers. But wait, `_read_graph_sample_frame` is only called once.
            # Let's just return a 5-tuple and update the caller.

        elif len(summary_records) == 1:
            # Louvain communities are disjoint within one monthly partition.
            available_nodes = int(
                pd.to_numeric(summary["node_count"], errors="coerce").fillna(0).sum()
            )
        else:
            # Older longitudinal bundles do not contain enough information for
            # an exact cross-month unique-node count; use the authoritative path.
            return None
        return frame, available_nodes, available_edges, summary, node_layouts

    def _read_summary_frame(
        self, run_id: str, metric: str, *, period: str | None = None
    ) -> pd.DataFrame | None:
        key = self.summary_key(metric)
        try:
            records = self._records_for_key(run_id, key, period=period)
        except ArtifactUnavailableError:
            return None
        frames = [self.reader.read_parquet_record(run_id, record) for record in records]
        return pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]

    def _read_community_interaction_frame(
        self, run_id: str, metric: str, *, period: str | None = None
    ) -> pd.DataFrame | None:
        key = self.interaction_key(metric)
        try:
            records = self._records_for_key(run_id, key, period=period)
        except ArtifactUnavailableError:
            return None
        frames = [
            self.reader.read_parquet_record(
                run_id, record, columns=_INTERACTION_COLUMNS
            )
            for record in records
        ]
        frame = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        return _normalize_community_interaction_frame(frame)

    def graph(
        self,
        run_id: str,
        *,
        metric: str,
        community_id: str | None,
        min_weight: float,
        max_nodes: int,
        max_edges: int,
        period: str | None = None,
        view: str = "users",
        sampling: str | None = None,
    ) -> dict[str, Any]:
        self._check_limits(run_id, max_nodes, max_edges)
        if view not in _NETWORK_VIEWS:
            raise InvalidFilterError(
                f"Unknown network view {view!r}. Expected users or communities.",
                run_id=run_id,
            )
        if sampling is not None and sampling not in _SAMPLING_STRATEGIES:
            raise InvalidFilterError(
                "Unknown sampling strategy. Expected community_balanced or "
                "strongest_edges.",
                run_id=run_id,
            )
        if view == "communities":
            if sampling is not None:
                raise InvalidFilterError(
                    "sampling can only be used with the users network view.",
                    run_id=run_id,
                )
            if community_id is not None:
                raise InvalidFilterError(
                    "community_id can only be used with the users network view.",
                    run_id=run_id,
                )
            return self._community_map(
                run_id,
                metric=metric,
                period=period,
                max_nodes=max_nodes,
                max_edges=max_edges,
                min_weight=min_weight,
            )
        return self._user_graph(
            run_id,
            metric=metric,
            community_id=community_id,
            min_weight=min_weight,
            max_nodes=max_nodes,
            max_edges=max_edges,
            period=period,
            sampling=sampling or "strongest_edges",
        )

    def _community_map(
        self,
        run_id: str,
        *,
        metric: str,
        period: str | None,
        max_nodes: int,
        max_edges: int,
        min_weight: float,
    ) -> dict[str, Any]:
        if period is None:
            manifest = self.reader.catalog.get_manifest(run_id)
            periods = discover_periods(manifest, self.reader.read_safe_config(run_id))
            if len(periods) > 1:
                raise InvalidFilterError(
                    "A period is required for the communities network view because "
                    "community IDs are month-local.",
                    run_id=run_id,
                )
            period = periods[0] if periods else None

        summary = self._read_summary_frame(run_id, metric, period=period)
        if summary is None:
            summary = _summary_from_graph_frame(
                self._read_graph_frame(run_id, metric, period=period)
            )
        normalized = _normalize_summary_frame(summary).sort_values(
            ["node_count", "edge_count", "community_id"],
            ascending=[False, False, True],
            kind="stable",
        )
        selected = normalized.head(max_nodes).copy()
        selected_ids = set(selected["community_id"].astype(str))

        interactions = self._read_community_interaction_frame(
            run_id, metric, period=period
        )
        cross_available = interactions is not None
        if interactions is None:
            interactions = pd.DataFrame(columns=_INTERACTION_COLUMNS)
        available_interactions = interactions.copy()
        if float(min_weight) > 0 and not available_interactions.empty:
            available_interactions = available_interactions.loc[
                available_interactions["total_weight"] >= float(min_weight)
            ]
        available_interactions = available_interactions.sort_values(
            ["total_weight", "source_community_id", "target_community_id"],
            ascending=[False, True, True],
            kind="stable",
        )
        selected_interactions = available_interactions.loc[
            available_interactions["source_community_id"].isin(selected_ids)
            & available_interactions["target_community_id"].isin(selected_ids)
        ].head(max_edges)

        inbound: defaultdict[str, float] = defaultdict(float)
        outbound: defaultdict[str, float] = defaultdict(float)
        neighbors: defaultdict[str, set[str]] = defaultdict(set)
        for row in available_interactions.itertuples(index=False):
            source = str(row.source_community_id)
            target = str(row.target_community_id)
            weight = float(row.total_weight)
            outbound[source] += weight
            inbound[target] += weight
            neighbors[source].add(target)
            neighbors[target].add(source)

        nodes = [
            {
                "id": str(row.community_id),
                "community_ids": [str(row.community_id)],
                "node_type": "community",
                "community_id": str(row.community_id),
                "member_count": int(row.node_count),
                "internal_edge_count": int(row.edge_count),
                "internal_weight": float(row.total_weight),
                "x": float(row.x) if hasattr(row, "x") and pd.notna(row.x) else None,
                "y": float(row.y) if hasattr(row, "y") and pd.notna(row.y) else None,
                "inbound_cross_community_weight": (
                    float(inbound[str(row.community_id)]) if cross_available else None
                ),
                "outbound_cross_community_weight": (
                    float(outbound[str(row.community_id)]) if cross_available else None
                ),
                "cross_community_neighbor_count": (
                    len(neighbors[str(row.community_id)]) if cross_available else None
                ),
            }
            for row in selected.itertuples(index=False)
        ]
        edges = [
            {
                "source": str(row.source_community_id),
                "target": str(row.target_community_id),
                "community_id": None,
                "direction": "Directed",
                "weight": float(row.total_weight),
                "edge_count": int(row.user_pair_count),
                "user_pair_count": int(row.user_pair_count),
                "interaction_count": int(row.interaction_count),
                "source_user_count": int(row.source_user_count),
                "target_user_count": int(row.target_user_count),
            }
            for row in selected_interactions.itertuples(index=False)
        ]

        available_communities = len(normalized)
        represented_communities = len(selected)
        available_users = int(normalized["node_count"].sum())
        represented_users = int(selected["node_count"].sum())
        available_edges = len(available_interactions) if cross_available else 0
        represented_edges = len(edges)
        available_weight = (
            float(available_interactions["total_weight"].sum())
            if cross_available and not available_interactions.empty
            else 0.0
        )
        represented_weight = sum(edge["weight"] for edge in edges)
        nodes_complete = represented_communities == available_communities
        edges_complete = represented_edges == available_edges
        is_complete = nodes_complete and (not cross_available or edges_complete)
        if not cross_available:
            reason = "cross_community_artifact_unavailable"
        elif not nodes_complete:
            reason = "community_node_limit"
        elif not edges_complete:
            reason = "community_edge_limit"
        else:
            reason = None

        coverage = _coverage(
            is_complete=is_complete,
            scope="prominent_community_interaction_network",
            completeness_reason=reason,
            available_users=available_users,
            represented_users=represented_users,
            available_edges=available_edges,
            represented_edges=represented_edges,
            available_communities=available_communities,
            represented_communities=represented_communities,
            available_weight=available_weight,
            represented_weight=represented_weight,
            cross_community_edges_available=cross_available,
            cross_community_edges_reason=(None if cross_available else reason),
        )
        return {
            "run_id": run_id,
            "metric": metric,
            "period": period,
            "community_id": None,
            "view": "communities",
            "sampling_strategy": None,
            "nodes": nodes,
            "edges": edges,
            "available_nodes": available_communities,
            "available_edges": available_edges,
            "returned_nodes": len(nodes),
            "returned_edges": len(edges),
            "sampled": not is_complete,
            "coverage": coverage,
            "sampling": None,
        }

    def _user_graph(
        self,
        run_id: str,
        *,
        metric: str,
        community_id: str | None,
        min_weight: float,
        max_nodes: int,
        max_edges: int,
        period: str | None,
        sampling: str,
    ) -> dict[str, Any]:
        sample = None
        node_layouts: dict[str, tuple[float, float]] = {}
        if community_id is None and float(min_weight) <= 0:
            sample = self._read_graph_sample_frame(run_id, metric, period=period)

        if sample is not None:
            sample_frame, available_nodes, available_edges, summary, node_layouts = (
                sample
            )
            frame = _normalize_graph_frame(sample_frame)
        else:
            frame = _normalize_graph_frame(
                self._read_graph_frame(
                    run_id,
                    metric,
                    min_weight=min_weight,
                    community_id=community_id,
                    period=period,
                )
            )
            if community_id is not None:
                frame = frame.loc[
                    frame["community_number"].astype(str) == str(community_id)
                ]
            frame = frame.loc[frame["weight"] >= float(min_weight)]
            available_edges = len(frame)
            available_nodes = len(
                {_identifier_string(value) for value in frame["source"]}
                | {_identifier_string(value) for value in frame["target"]}
            )
            summary = self._read_summary_frame(run_id, metric, period=period)
            if community_id is not None and summary is not None:
                summary = summary.loc[
                    summary["community_id"].astype(str) == str(community_id)
                ]

            # Read node index separately for layouts when not using the sample
            try:
                node_records = self._records_for_key(
                    run_id, self.node_index_key(metric), period=period
                )
                for record in node_records:
                    try:
                        node_frame = self.reader.read_parquet_record(
                            run_id, record, columns=_NODE_INDEX_COLUMNS
                        )
                        for row in node_frame.to_dict(orient="records"):
                            if (
                                "x" in row
                                and "y" in row
                                and not pd.isna(row["x"])
                                and not pd.isna(row["y"])
                            ):
                                node_id = _identifier_string(row["node_id"])
                                node_layouts[node_id] = (
                                    float(row["x"]),
                                    float(row["y"]),
                                )
                    except (ValueError, TypeError):
                        pass
            except ArtifactUnavailableError:
                pass

        summary = _normalize_summary_frame(summary) if summary is not None else None
        available_communities = (
            len(summary)
            if summary is not None
            else frame["community_number"].astype(str).nunique()
        )
        available_weight = (
            float(summary["total_weight"].sum())
            if summary is not None
            else float(frame["weight"].sum())
        )
        source_sample_truncated = len(frame) < available_edges

        if sampling == "community_balanced":
            selected_rows, selected_nodes = _community_balanced_selection(
                frame,
                max_nodes=max_nodes,
                max_edges=max_edges,
                summary=summary,
            )
        elif sampling == "full_graph":
            selected_rows = frame.to_dict(orient="records")
            selected_nodes = {
                _identifier_string(row["source"]) for row in selected_rows
            } | {_identifier_string(row["target"]) for row in selected_rows}
        else:
            selected_rows, selected_nodes = _strongest_edge_selection(
                frame, max_nodes=max_nodes, max_edges=max_edges
            )

        memberships: dict[str, set[str]] = defaultdict(set)
        for row in frame.itertuples(index=False):
            community = _optional_string(row.community_number)
            if community is None:
                continue
            source = _identifier_string(row.source)
            target = _identifier_string(row.target)
            if source in selected_nodes:
                memberships[source].add(community)
            if target in selected_nodes:
                memberships[target].add(community)

        edges = []
        represented_weight = 0.0
        for row in selected_rows:
            community = _optional_string(row.get("community_number"))
            source = _identifier_string(row["source"])
            target = _identifier_string(row["target"])
            weight = float(row["weight"])
            represented_weight += weight
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "community_id": community,
                    "direction": _optional_string(row.get("direction")),
                    "weight": weight,
                    "edge_count": 1,
                }
            )

        nodes = [
            {
                "id": node,
                "community_ids": sorted(memberships.get(node, set())),
                "node_type": "user",
                "community_id": (
                    sorted(memberships[node])[0] if memberships.get(node) else None
                ),
                "member_count": None,
                "internal_edge_count": None,
                "internal_weight": None,
                "inbound_cross_community_weight": None,
                "outbound_cross_community_weight": None,
                "x": node_layouts.get(node)[0] if node in node_layouts else None,
                "y": node_layouts.get(node)[1] if node in node_layouts else None,
            }
            for node in sorted(selected_nodes)
        ]
        represented_communities = len(
            {community for values in memberships.values() for community in values}
        )
        sampled = available_nodes > len(nodes) or available_edges > len(edges)
        reason = None
        if source_sample_truncated:
            reason = "source_graph_sample_truncated"
        elif sampled:
            reason = "api_node_or_edge_limit"
        coverage = _coverage(
            is_complete=not sampled,
            scope=(
                f"community_{community_id}"
                if community_id is not None
                else "prominent_community_user_graph"
            ),
            completeness_reason=reason,
            available_users=available_nodes,
            represented_users=len(nodes),
            available_edges=available_edges,
            represented_edges=len(edges),
            available_communities=available_communities,
            represented_communities=represented_communities,
            available_weight=available_weight,
            represented_weight=represented_weight,
            cross_community_edges_available=False,
        )
        return {
            "run_id": run_id,
            "metric": metric,
            "period": period,
            "community_id": community_id,
            "view": "users",
            "sampling_strategy": sampling,
            "nodes": nodes,
            "edges": edges,
            "available_nodes": available_nodes,
            "available_edges": available_edges,
            "returned_nodes": len(nodes),
            "returned_edges": len(edges),
            "sampled": sampled,
            "coverage": coverage,
            "sampling": {
                "strategy": sampling,
                "deterministic": True,
                "max_nodes": max_nodes,
                "max_edges": max_edges,
            },
        }

    def communities(
        self,
        run_id: str,
        *,
        metric: str,
        limit: int,
        offset: int,
        period: str | None = None,
    ) -> dict[str, Any]:
        summary = self._read_summary_frame(run_id, metric, period=period)
        if summary is not None:
            communities = [
                {
                    "community_id": str(normalize_value(row["community_id"])),
                    "node_count": int(row["node_count"]),
                    "edge_count": int(row["edge_count"]),
                    "total_weight": float(row["total_weight"]),
                }
                for row in summary.to_dict(orient="records")
            ]
        else:
            frame = _normalize_graph_frame(
                self._read_graph_frame(run_id, metric, period=period)
            )
            communities = []
            for community_id, group in frame.groupby("community_number", sort=False):
                nodes = {_identifier_string(value) for value in group["source"]} | {
                    _identifier_string(value) for value in group["target"]
                }
                communities.append(
                    {
                        "community_id": str(normalize_value(community_id)),
                        "node_count": len(nodes),
                        "edge_count": len(group),
                        "total_weight": float(group["weight"].sum()),
                    }
                )
        interaction_stats = _community_interaction_stats(
            self._read_community_interaction_frame(run_id, metric, period=period)
        )
        for item in communities:
            stats = interaction_stats.get(item["community_id"])
            item["inbound_cross_community_weight"] = (
                stats["inbound"] if stats is not None else None
            )
            item["outbound_cross_community_weight"] = (
                stats["outbound"] if stats is not None else None
            )
            item["cross_community_neighbor_count"] = (
                stats["neighbor_count"] if stats is not None else None
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
            "period": period,
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
        period: str | None = None,
    ) -> dict[str, Any]:
        summary_frame = self._read_summary_frame(run_id, metric, period=period)
        summary = None
        if summary_frame is not None:
            matches = summary_frame.loc[
                summary_frame["community_id"].astype(str) == str(community_id)
            ]
            if not matches.empty:
                row = matches.iloc[0]
                summary = {
                    "community_id": str(normalize_value(row["community_id"])),
                    "node_count": int(row["node_count"]),
                    "edge_count": int(row["edge_count"]),
                    "total_weight": float(row["total_weight"]),
                }
                interaction_stats = _community_interaction_stats(
                    self._read_community_interaction_frame(
                        run_id, metric, period=period
                    )
                ).get(summary["community_id"])
                summary["inbound_cross_community_weight"] = (
                    interaction_stats["inbound"]
                    if interaction_stats is not None
                    else None
                )
                summary["outbound_cross_community_weight"] = (
                    interaction_stats["outbound"]
                    if interaction_stats is not None
                    else None
                )
                summary["cross_community_neighbor_count"] = (
                    interaction_stats["neighbor_count"]
                    if interaction_stats is not None
                    else None
                )
        else:
            page = self.communities(
                run_id,
                metric=metric,
                limit=2**31 - 1,
                offset=0,
                period=period,
            )
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
            period=period,
            view="users",
            sampling="community_balanced",
        )
        return {
            "run_id": run_id,
            "metric": metric,
            "period": period,
            "community": summary,
            "graph": graph,
        }

    def centrality(self, run_id: str, *, limit: int, offset: int) -> dict[str, Any]:
        key = "user_centrality"
        frame, total = self.reader.read_parquet_records_page(
            run_id,
            self._records_for_key(run_id, key),
            limit=limit,
            offset=offset,
        )
        records, _ = self.reader.page(frame, limit=limit, offset=0)
        return {
            "run_id": run_id,
            "artifact_key": key,
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def centrality_leaders(
        self,
        run_id: str,
        *,
        metric: str,
        period: str | None = None,
    ) -> dict[str, Any]:
        records = self._records_for_key(run_id, "user_centrality")
        manifest = self.reader.catalog.get_manifest(run_id)
        config = self.reader.read_safe_config(run_id)
        fallback_year = default_year(config, manifest)
        available_periods = discover_periods(manifest, config)
        if period is not None and period not in available_periods:
            availability = ", ".join(available_periods) or "none"
            raise InvalidFilterError(
                f"Period {period} is not available for this run. "
                f"Available periods: {availability}.",
                run_id=run_id,
            )

        field = "absolute" if metric == "if" else "weighted"
        period_results: dict[str, dict[str, Any]] = {}
        membership_cache: dict[str, dict[str, str | None]] = {}

        for record in sorted(
            records,
            key=lambda item: (
                record_period(item, fallback_year=fallback_year) or item.key
            ),
        ):
            frame = self.reader.read_parquet_record(
                run_id, record, columns=_CENTRALITY_COLUMNS
            )
            if frame.empty:
                continue
            record_snapshot = record_period(record, fallback_year=fallback_year)
            for row in frame.to_dict(orient="records"):
                resolved_period = record_snapshot
                if resolved_period is None:
                    month = _month_number(row.get("month"))
                    if month is not None and fallback_year is not None:
                        resolved_period = f"{fallback_year:04d}-{month:02d}"
                if resolved_period is None or (
                    period is not None and resolved_period != period
                ):
                    continue

                payload = normalize_value(row.get(field))
                if not isinstance(payload, Mapping):
                    payload = {}
                if resolved_period not in membership_cache:
                    membership_cache[resolved_period] = self._community_memberships(
                        run_id, metric=metric, period=resolved_period
                    )
                memberships = membership_cache[resolved_period]
                period_results[resolved_period] = {
                    "period": resolved_period,
                    "spreader": _centrality_actor(
                        payload,
                        user_key="max_in_degree_user",
                        value_key="max_in_degree_val",
                        memberships=memberships,
                    ),
                    "influencer": _centrality_actor(
                        payload,
                        user_key="max_out_degree_user",
                        value_key="max_out_degree_val",
                        memberships=memberships,
                    ),
                    "average_in_degree_centrality": _optional_float(
                        payload.get("avg_in_degree_val")
                    ),
                    "average_out_degree_centrality": _optional_float(
                        payload.get("avg_out_degree_val")
                    ),
                }

        return {
            "run_id": run_id,
            "metric": metric,
            "periods": [period_results[key] for key in sorted(period_results)],
            "methodology_note": (
                "Degree centrality is normalized structural reach based on distinct "
                "directed connections; it is not a message count or total edge weight."
            ),
        }

    def _community_memberships(
        self, run_id: str, *, metric: str, period: str
    ) -> dict[str, str | None]:
        try:
            frame = self._read_graph_frame(
                run_id,
                metric,
                period=period,
                columns=_MEMBERSHIP_COLUMNS,
            )
        except ArtifactUnavailableError:
            return {}
        assignments: dict[str, set[str]] = defaultdict(set)
        for row in frame.itertuples(index=False):
            community = _optional_string(row.community_number)
            if community is None:
                continue
            assignments[_identifier_string(row.source)].add(community)
            assignments[_identifier_string(row.target)].add(community)
        return {
            user_id: next(iter(communities)) if len(communities) == 1 else None
            for user_id, communities in assignments.items()
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


def _summary_from_graph_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = _normalize_graph_frame(frame)
    rows: list[dict[str, Any]] = []
    for community_id, group in normalized.groupby("community_number", sort=False):
        nodes = {_identifier_string(value) for value in group["source"]} | {
            _identifier_string(value) for value in group["target"]
        }
        rows.append(
            {
                "community_id": _identifier_string(community_id),
                "node_count": len(nodes),
                "edge_count": len(group),
                "total_weight": float(group["weight"].sum()),
            }
        )
    return pd.DataFrame(rows, columns=_SUMMARY_REQUIRED_COLUMNS)


def _normalize_summary_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(_SUMMARY_REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(
            f"community summary artifact schema mismatch; missing columns: {missing}"
        )
    selected_columns = _SUMMARY_REQUIRED_COLUMNS + [
        column for column in _SUMMARY_LAYOUT_COLUMNS if column in frame.columns
    ]
    result = frame[selected_columns].copy()
    result["community_id"] = result["community_id"].map(_identifier_string)
    result["node_count"] = (
        pd.to_numeric(result["node_count"], errors="coerce").fillna(0).astype(int)
    )
    result["edge_count"] = (
        pd.to_numeric(result["edge_count"], errors="coerce").fillna(0).astype(int)
    )
    result["total_weight"] = pd.to_numeric(
        result["total_weight"], errors="coerce"
    ).fillna(0.0)
    return result


def _community_interaction_stats(
    frame: pd.DataFrame | None,
) -> dict[str, dict[str, float | int]]:
    if frame is None:
        return {}
    inbound: defaultdict[str, float] = defaultdict(float)
    outbound: defaultdict[str, float] = defaultdict(float)
    neighbors: defaultdict[str, set[str]] = defaultdict(set)
    for row in frame.itertuples(index=False):
        source = str(row.source_community_id)
        target = str(row.target_community_id)
        weight = float(row.total_weight)
        outbound[source] += weight
        inbound[target] += weight
        neighbors[source].add(target)
        neighbors[target].add(source)
    community_ids = set(inbound) | set(outbound) | set(neighbors)
    return {
        community_id: {
            "inbound": float(inbound[community_id]),
            "outbound": float(outbound[community_id]),
            "neighbor_count": len(neighbors[community_id]),
        }
        for community_id in community_ids
    }


def _normalize_community_interaction_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in ("source_community_id", "target_community_id"):
        result[column] = result[column].map(_identifier_string)
    for column in (
        "user_pair_count",
        "interaction_count",
        "source_user_count",
        "target_user_count",
    ):
        result[column] = (
            pd.to_numeric(result[column], errors="coerce").fillna(0).astype(int)
        )
    result["total_weight"] = pd.to_numeric(
        result["total_weight"], errors="coerce"
    ).fillna(0.0)
    return result[_INTERACTION_COLUMNS]


def _strongest_edge_selection(
    frame: pd.DataFrame, *, max_nodes: int, max_edges: int
) -> tuple[list[dict[str, Any]], set[str]]:
    ordered = frame.assign(
        _source=frame["source"].map(_identifier_string),
        _target=frame["target"].map(_identifier_string),
        _community=frame["community_number"].map(_identifier_string),
    ).sort_values(
        ["weight", "_community", "_source", "_target"],
        ascending=[False, True, True, True],
        kind="stable",
    )
    selected_rows: list[dict[str, Any]] = []
    selected_nodes: set[str] = set()
    for row in ordered.itertuples(index=False):
        if len(selected_rows) >= max_edges:
            break
        source = _identifier_string(row.source)
        target = _identifier_string(row.target)
        proposed = selected_nodes | {source, target}
        if len(proposed) > max_nodes:
            continue
        selected_nodes = proposed
        selected_rows.append(
            {
                "source": row.source,
                "target": row.target,
                "community_number": row.community_number,
                "direction": getattr(row, "direction", None),
                "weight": row.weight,
            }
        )
    return selected_rows, selected_nodes


def _community_balanced_selection(
    frame: pd.DataFrame,
    *,
    max_nodes: int,
    max_edges: int,
    summary: pd.DataFrame | None,
) -> tuple[list[dict[str, Any]], set[str]]:
    if frame.empty:
        return [], set()
    community_nodes: dict[str, set[str]] = defaultdict(set)
    node_degree: dict[tuple[str, str], int] = defaultdict(int)
    node_weight: dict[tuple[str, str], float] = defaultdict(float)
    for row in frame.itertuples(index=False):
        community = _identifier_string(row.community_number)
        source = _identifier_string(row.source)
        target = _identifier_string(row.target)
        weight = float(row.weight)
        community_nodes[community].update((source, target))
        node_degree[(community, source)] += 1
        node_degree[(community, target)] += 1
        node_weight[(community, source)] += weight
        node_weight[(community, target)] += weight

    summary_sizes = (
        {
            str(row.community_id): int(row.node_count)
            for row in summary.itertuples(index=False)
        }
        if summary is not None
        else {}
    )
    communities = sorted(
        community_nodes,
        key=lambda community: (
            -math.sqrt(
                max(
                    1,
                    summary_sizes.get(community, len(community_nodes[community])),
                )
            ),
            community,
        ),
    )
    minimum = 2
    if max_nodes < len(communities) * minimum:
        represented_count = max(1, max_nodes // minimum)
        communities = communities[:represented_count]

    quotas = {
        community: min(minimum, len(community_nodes[community]))
        for community in communities
    }
    remaining = max_nodes - sum(quotas.values())
    while remaining > 0:
        candidates = [
            community
            for community in communities
            if quotas[community] < len(community_nodes[community])
        ]
        if not candidates:
            break
        chosen = min(
            candidates,
            key=lambda community: (
                -math.sqrt(
                    max(
                        1,
                        summary_sizes.get(community, len(community_nodes[community])),
                    )
                )
                / (quotas[community] + 1),
                community,
            ),
        )
        quotas[chosen] += 1
        remaining -= 1

    selected_nodes: set[str] = set()
    for community in communities:
        ranked = sorted(
            community_nodes[community],
            key=lambda node: (
                -node_degree[(community, node)],
                -node_weight[(community, node)],
                node,
            ),
        )
        selected_nodes.update(ranked[: quotas[community]])

    candidate = frame.loc[
        frame["source"].map(_identifier_string).isin(selected_nodes)
        & frame["target"].map(_identifier_string).isin(selected_nodes)
    ].copy()
    if candidate.empty:
        return [], selected_nodes
    candidate["_source"] = candidate["source"].map(_identifier_string)
    candidate["_target"] = candidate["target"].map(_identifier_string)
    candidate["_community"] = candidate["community_number"].map(_identifier_string)
    candidate = candidate.sort_values(
        ["weight", "_community", "_source", "_target"],
        ascending=[False, True, True, True],
        kind="stable",
    ).head(max_edges)
    rows = [
        {
            "source": row.source,
            "target": row.target,
            "community_number": row.community_number,
            "direction": getattr(row, "direction", None),
            "weight": row.weight,
        }
        for row in candidate.itertuples(index=False)
    ]
    return rows, selected_nodes


def _coverage(
    *,
    is_complete: bool,
    scope: str,
    completeness_reason: str | None,
    available_users: int,
    represented_users: int,
    available_edges: int,
    represented_edges: int,
    available_communities: int,
    represented_communities: int,
    available_weight: float,
    represented_weight: float,
    cross_community_edges_available: bool,
    cross_community_edges_reason: str | None = None,
) -> dict[str, Any]:
    ratio = represented_weight / available_weight if available_weight > 0 else None
    return {
        "is_complete": is_complete,
        "scope": scope,
        "completeness_reason": completeness_reason,
        "available_users": int(available_users),
        "represented_users": int(represented_users),
        "available_edges": int(available_edges),
        "represented_edges": int(represented_edges),
        "available_communities": int(available_communities),
        "represented_communities": int(represented_communities),
        "available_weight": float(available_weight),
        "represented_weight": float(represented_weight),
        "weight_coverage_ratio": round(ratio, 6) if ratio is not None else None,
        "cross_community_edges_available": cross_community_edges_available,
        "cross_community_edges_reason": cross_community_edges_reason,
    }


def _centrality_actor(
    payload: Mapping[str, Any],
    *,
    user_key: str,
    value_key: str,
    memberships: Mapping[str, str | None],
) -> dict[str, Any] | None:
    user = payload.get(user_key)
    value = _optional_float(payload.get(value_key))
    if user is None or value is None:
        return None
    user_id = _identifier_string(user)
    community_id = memberships.get(user_id)
    return {
        "user_id": user_id,
        "display_user_id": _mask_identifier(user_id),
        "centrality": value,
        "community_id": community_id,
        "community_assignment_status": (
            "available" if community_id is not None else "unavailable"
        ),
    }


def _mask_identifier(value: str) -> str:
    if len(value) <= 6:
        return value
    return f"{value[:2]}{'•' * min(6, len(value) - 4)}{value[-2:]}"


def _month_number(value: Any) -> int | None:
    text = str(normalize_value(value) or "").strip()
    if text.isdigit() and 1 <= int(text) <= 12:
        return int(text)
    return None


def _optional_float(value: Any) -> float | None:
    normalized = normalize_value(value)
    if normalized is None:
        return None
    try:
        numeric = float(normalized)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _identifier_string(value: Any) -> str:
    """Return stable JSON-facing identifiers without changing string identity."""
    normalized = normalize_value(value)
    if isinstance(normalized, float) and normalized.is_integer():
        return str(int(normalized))
    return str(normalized)


def _optional_string(value: Any) -> str | None:
    normalized = normalize_value(value)
    return None if normalized is None else _identifier_string(normalized)
