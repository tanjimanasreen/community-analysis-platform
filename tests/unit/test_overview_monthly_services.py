from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from src.api.errors import ArtifactNotFoundError, InvalidFilterError
from src.api.schemas.networks import CentralityLeadersResponse, NetworkResponse
from src.api.services.network_service import GraphLimits, NetworkService
from src.api.services.overview_service import OverviewService
from src.artifacts.models import (
    ArtifactCategory,
    ArtifactRecord,
    RunManifest,
    RunStatus,
)


def _record(key: str, *, rows: int, path: str | None = None) -> ArtifactRecord:
    return ArtifactRecord(
        key=key,
        path=path or f"data/{key}.parquet",
        category=ArtifactCategory.DATA,
        media_type="application/vnd.apache.parquet",
        schema_version="1",
        sha256="0" * 64,
        rows=rows,
        byte_size=1,
        stage="network_community",
    )


def _edge(source: str, target: str, community: int, weight: float) -> dict:
    return {
        "source": source,
        "target": target,
        "community_number": community,
        "direction": "out",
        "weight": weight,
    }


class _Catalog:
    def __init__(self, manifest: RunManifest) -> None:
        self.manifest = manifest

    def get_manifest(self, run_id: str) -> RunManifest:
        assert run_id == self.manifest.run_id
        return self.manifest


class _Reader:
    def __init__(
        self,
        manifest: RunManifest,
        config: dict,
        frames: dict[str, pd.DataFrame],
    ) -> None:
        self.catalog = _Catalog(manifest)
        self.config = config
        self.frames = frames

    def read_safe_config(self, run_id: str) -> dict:
        assert run_id == self.catalog.manifest.run_id
        return self.config

    def get_record(self, run_id: str, key: str) -> ArtifactRecord:
        assert run_id == self.catalog.manifest.run_id
        for record in self.catalog.manifest.artifacts:
            if record.key == key:
                return record
        raise ArtifactNotFoundError(run_id, key)

    def find_records(self, run_id: str, *, key_prefix: str) -> list[ArtifactRecord]:
        assert run_id == self.catalog.manifest.run_id
        return [
            record
            for record in self.catalog.manifest.artifacts
            if record.key.startswith(key_prefix)
        ]

    def read_parquet_record(
        self,
        run_id: str,
        record: ArtifactRecord,
        *,
        columns: list[str] | None = None,
        filters: list[tuple[str, str, object]] | None = None,
    ) -> pd.DataFrame:
        assert run_id == self.catalog.manifest.run_id
        frame = self.frames[record.key].copy()
        if filters:
            for column, operator, value in filters:
                if operator == ">=":
                    frame = frame.loc[frame[column] >= value]
                elif operator == "==":
                    frame = frame.loc[frame[column] == value]
                else:  # pragma: no cover - test fake protects the supported contract
                    raise AssertionError(operator)
        if columns is not None:
            frame = frame.loc[:, columns]
        return frame

    def parquet_row_count(self, run_id: str, record: ArtifactRecord) -> int:
        assert run_id == self.catalog.manifest.run_id
        return int(record.rows or 0)


class _Evolution:
    def persistent_communities(self, run_id: str) -> dict[str, int]:
        assert run_id == "monthly-run"
        return {"total": 6}


def _monthly_reader() -> _Reader:
    records = (
        _record("network_data_03", rows=4),
        _record("network_data_04", rows=2),
        _record("count_user_messages_03", rows=1),
        _record("count_user_messages_04", rows=1),
        _record("communities_matched_03", rows=1),
        _record("communities_matched_04", rows=1),
        _record("communities_absolute_03", rows=3),
        _record("communities_absolute_04", rows=1),
        _record("communities_weighted_03", rows=3),
        _record("communities_weighted_04", rows=1),
        _record("community_graph_sample_absolute_03", rows=3),
        _record("community_graph_sample_absolute_04", rows=1),
        _record("community_graph_sample_weighted_03", rows=3),
        _record("community_graph_sample_weighted_04", rows=1),
        _record("community_summary_absolute_03", rows=2),
        _record("community_summary_absolute_04", rows=1),
        _record("community_summary_weighted_03", rows=2),
        _record("community_summary_weighted_04", rows=1),
        _record("community_node_index_absolute_03", rows=5),
        _record("community_node_index_absolute_04", rows=2),
        _record("community_node_index_weighted_03", rows=5),
        _record("community_node_index_weighted_04", rows=2),
        _record("user_centrality_03", rows=1),
        _record("user_centrality_04", rows=1),
    )
    manifest = RunManifest(
        run_id="monthly-run",
        status=RunStatus.COMPLETED,
        dataset={
            "platform": "twitter",
            "content_type": "retweet_quote",
            "date_start": None,
            "date_end": None,
        },
        code={},
        pipeline={"completed_at": "2026-07-24T14:12:20+00:00"},
        artifacts=records,
    )
    config = {
        "year": 2017,
        "longitudinal_datasets": [
            {"month": "03", "input_path": "data/raw/2017/march.csv"},
            {"month": "04", "input_path": "data/raw/2017/april.csv"},
        ],
        "graph_thresholds": {"min_total_post": 10, "min_shared_post": 5},
        "louvain": {"resolution": 1, "seed": 123},
        "lda": {"num_topics": 15, "passes": 80},
        "theme_provider": {
            "primary": "openai:gpt-5-nano",
            "cache_path": ".cache/theme_cache.sqlite3",
        },
    }
    frames = {
        "count_user_messages_03": pd.DataFrame(
            [
                {
                    "month": "03",
                    "user": "{'absolute': 5, 'weighted': 4}",
                    "messages": "{'absolute': 20, 'weighted': 18}",
                }
            ]
        ),
        "count_user_messages_04": pd.DataFrame(
            [
                {
                    "month": "04",
                    "user": "{'absolute': 10, 'weighted': 9}",
                    "messages": "{'absolute': 40, 'weighted': 35}",
                }
            ]
        ),
        "communities_matched_03": pd.DataFrame(
            [
                {
                    "month": "03",
                    "total_matched": 2,
                    "total_absolute": 3,
                    "total_weighted": 4,
                }
            ]
        ),
        "communities_matched_04": pd.DataFrame(
            [
                {
                    "month": "04",
                    "total_matched": 5,
                    "total_absolute": 6,
                    "total_weighted": 7,
                }
            ]
        ),
        "communities_absolute_03": pd.DataFrame(
            [
                _edge("m1", "m2", 1, 4.0),
                _edge("m2", "m3", 1, 3.0),
                _edge("m4", "m5", 2, 2.0),
            ]
        ),
        "communities_absolute_04": pd.DataFrame([_edge("a1", "a2", 9, 12.0)]),
        "communities_weighted_03": pd.DataFrame(
            [
                _edge("m1", "m2", 1, 5.0),
                _edge("m2", "m3", 1, 4.0),
                _edge("m4", "m5", 2, 3.0),
            ]
        ),
        "communities_weighted_04": pd.DataFrame([_edge("a1", "a2", 9, 13.0)]),
        "community_graph_sample_absolute_03": pd.DataFrame(
            [
                _edge("m1", "m2", 1, 4.0),
                _edge("m2", "m3", 1, 3.0),
                _edge("m4", "m5", 2, 2.0),
            ]
        ),
        "community_graph_sample_absolute_04": pd.DataFrame(
            [_edge("a1", "a2", 9, 12.0)]
        ),
        "community_graph_sample_weighted_03": pd.DataFrame(
            [
                _edge("m1", "m2", 1, 5.0),
                _edge("m2", "m3", 1, 4.0),
                _edge("m4", "m5", 2, 3.0),
            ]
        ),
        "community_graph_sample_weighted_04": pd.DataFrame(
            [_edge("a1", "a2", 9, 13.0)]
        ),
        "community_summary_absolute_03": pd.DataFrame(
            [
                {
                    "community_id": 1,
                    "node_count": 3,
                    "edge_count": 2,
                    "total_weight": 7.0,
                },
                {
                    "community_id": 2,
                    "node_count": 2,
                    "edge_count": 1,
                    "total_weight": 2.0,
                },
            ]
        ),
        "community_summary_absolute_04": pd.DataFrame(
            [
                {
                    "community_id": 9,
                    "node_count": 2,
                    "edge_count": 1,
                    "total_weight": 12.0,
                }
            ]
        ),
        "community_summary_weighted_03": pd.DataFrame(
            [
                {
                    "community_id": 1,
                    "node_count": 3,
                    "edge_count": 2,
                    "total_weight": 9.0,
                },
                {
                    "community_id": 2,
                    "node_count": 2,
                    "edge_count": 1,
                    "total_weight": 3.0,
                },
            ]
        ),
        "community_summary_weighted_04": pd.DataFrame(
            [
                {
                    "community_id": 9,
                    "node_count": 2,
                    "edge_count": 1,
                    "total_weight": 13.0,
                }
            ]
        ),
        "community_node_index_absolute_03": pd.DataFrame(
            {"node_id": ["m1", "m2", "m3", "m4", "m5"]}
        ),
        "community_node_index_absolute_04": pd.DataFrame({"node_id": ["a1", "a2"]}),
        "community_node_index_weighted_03": pd.DataFrame(
            {"node_id": ["m1", "m2", "m3", "m4", "m5"]}
        ),
        "community_node_index_weighted_04": pd.DataFrame({"node_id": ["a1", "a2"]}),
        "user_centrality_03": pd.DataFrame(
            [
                {
                    "month": "03",
                    "absolute": str(
                        {
                            "max_in_degree_user": "m2",
                            "max_in_degree_val": 0.5,
                            "max_out_degree_user": "m1",
                            "max_out_degree_val": 0.4,
                            "avg_in_degree_val": 0.2,
                            "avg_out_degree_val": 0.2,
                        }
                    ),
                    "weighted": str(
                        {
                            "max_in_degree_user": "m5",
                            "max_in_degree_val": 0.6,
                            "max_out_degree_user": "m4",
                            "max_out_degree_val": 0.7,
                            "avg_in_degree_val": 0.25,
                            "avg_out_degree_val": 0.25,
                        }
                    ),
                }
            ]
        ),
        "user_centrality_04": pd.DataFrame(
            [
                {
                    "month": "04",
                    "absolute": str(
                        {
                            "max_in_degree_user": "a2",
                            "max_in_degree_val": 1.0,
                            "max_out_degree_user": "a1",
                            "max_out_degree_val": 1.0,
                            "avg_in_degree_val": 1.0,
                            "avg_out_degree_val": 1.0,
                        }
                    ),
                    "weighted": str(
                        {
                            "max_in_degree_user": "missing",
                            "max_in_degree_val": 1.0,
                            "max_out_degree_user": "a1",
                            "max_out_degree_val": 1.0,
                            "avg_in_degree_val": 1.0,
                            "avg_out_degree_val": 1.0,
                        }
                    ),
                }
            ]
        ),
        "network_data_03": pd.DataFrame(index=range(4)),
        "network_data_04": pd.DataFrame(index=range(2)),
    }
    return _Reader(manifest, config, frames)


def test_overview_service_separates_monthly_and_run_level_values() -> None:
    reader = _monthly_reader()
    service = OverviewService(reader, SimpleNamespace(), _Evolution())

    result = service.overview("monthly-run")

    assert result["available_periods"] == ["2017-03", "2017-04"]
    assert result["date_start"] == "2017-03-01"
    assert result["date_end"] == "2017-04-30"
    assert result["periods"][0] == {
        "period": "2017-03",
        "if_users": 5,
        "wif_users": 4,
        "if_messages": 20,
        "wif_messages": 18,
        "interaction_records": 4,
        "if_community_count": 3,
        "wif_community_count": 4,
        "matched_community_count": 2,
        "matched_percentage": 50.0,
    }
    assert result["periods"][1]["if_users"] == 10
    assert result["periods"][1]["matched_percentage"] == 71.43
    assert result["run_summary"] == {
        "interaction_records": 6,
        "persistent_community_count": 6,
        "month_count": 2,
    }
    assert result["total_users"] == 10
    assert result["total_messages"] == 40
    assert result["total_interactions"] == 6
    assert "cache_path" not in str(result["config_metadata"])


def test_network_service_selects_only_the_requested_month() -> None:
    service = NetworkService(
        _monthly_reader(), GraphLimits(max_nodes=100, max_edges=100)
    )

    march = service.graph(
        "monthly-run",
        metric="if",
        period="2017-03",
        community_id=None,
        min_weight=0,
        max_nodes=100,
        max_edges=100,
    )
    april = service.graph(
        "monthly-run",
        metric="wif",
        period="2017-04",
        community_id=None,
        min_weight=0,
        max_nodes=100,
        max_edges=100,
    )

    assert march["period"] == "2017-03"
    assert march["returned_edges"] == 3
    assert april["period"] == "2017-04"
    assert april["returned_edges"] == 1
    assert april["edges"][0]["weight"] == 13.0
    assert {node["id"] for node in april["nodes"]} == {"a1", "a2"}

    with pytest.raises(InvalidFilterError, match="Available periods: 2017-03, 2017-04"):
        service.graph(
            "monthly-run",
            metric="if",
            period="2017-05",
            community_id=None,
            min_weight=0,
            max_nodes=100,
            max_edges=100,
        )


def test_network_service_builds_complete_community_structure_map() -> None:
    service = NetworkService(
        _monthly_reader(), GraphLimits(max_nodes=100, max_edges=100)
    )

    result = service.graph(
        "monthly-run",
        metric="if",
        period="2017-03",
        community_id=None,
        min_weight=0,
        max_nodes=100,
        max_edges=100,
        view="communities",
        sampling=None,
    )

    assert result["view"] == "communities"
    assert result["sampled"] is False
    assert result["returned_nodes"] == 2
    assert result["returned_edges"] == 0
    assert result["coverage"] == {
        "is_complete": True,
        "scope": "prominent_community_interaction_network",
        "completeness_reason": "cross_community_artifact_unavailable",
        "available_users": 5,
        "represented_users": 5,
        "available_edges": 0,
        "represented_edges": 0,
        "available_communities": 2,
        "represented_communities": 2,
        "available_weight": 0.0,
        "represented_weight": 0.0,
        "weight_coverage_ratio": None,
        "cross_community_edges_available": False,
        "cross_community_edges_reason": "cross_community_artifact_unavailable",
    }
    assert result["nodes"][0]["community_id"] == "1"
    assert result["nodes"][0]["member_count"] == 3
    assert result["nodes"][0]["internal_edge_count"] == 2
    NetworkResponse(**result)


def test_community_summary_preserves_optional_layout_coordinates() -> None:
    reader = _monthly_reader()
    reader.frames["community_summary_absolute_03"] = reader.frames[
        "community_summary_absolute_03"
    ].assign(x=[125.0, -75.0], y=[50.0, 25.0])
    service = NetworkService(reader, GraphLimits(max_nodes=100, max_edges=100))

    result = service.graph(
        "monthly-run",
        metric="if",
        period="2017-03",
        community_id=None,
        min_weight=0,
        max_nodes=100,
        max_edges=100,
        view="communities",
        sampling=None,
    )

    by_id = {node["community_id"]: node for node in result["nodes"]}
    assert by_id["1"]["x"] == 125.0
    assert by_id["1"]["y"] == 50.0
    assert by_id["2"]["x"] == -75.0
    assert by_id["2"]["y"] == 25.0


def test_community_aware_user_sampling_is_deterministic_and_balanced() -> None:
    service = NetworkService(
        _monthly_reader(), GraphLimits(max_nodes=100, max_edges=100)
    )
    request = {
        "metric": "if",
        "period": "2017-03",
        "community_id": None,
        "min_weight": 0,
        "max_nodes": 4,
        "max_edges": 3,
        "view": "users",
        "sampling": "community_balanced",
    }

    first = service.graph("monthly-run", **request)
    second = service.graph("monthly-run", **request)

    assert first == second
    assert first["sampling_strategy"] == "community_balanced"
    assert first["returned_nodes"] <= 4
    assert first["returned_edges"] <= 3
    assert first["coverage"]["represented_communities"] == 2
    assert first["coverage"]["available_communities"] == 2
    assert first["coverage"]["weight_coverage_ratio"] == pytest.approx(6 / 9)


def test_strongest_edge_sampling_preserves_the_highest_weight_edge() -> None:
    service = NetworkService(
        _monthly_reader(), GraphLimits(max_nodes=100, max_edges=100)
    )

    result = service.graph(
        "monthly-run",
        metric="wif",
        period="2017-03",
        community_id=None,
        min_weight=0,
        max_nodes=2,
        max_edges=1,
        view="users",
        sampling="strongest_edges",
    )

    assert result["edges"] == [
        {
            "source": "m1",
            "target": "m2",
            "community_id": "1",
            "direction": "out",
            "weight": 5.0,
            "edge_count": 1,
        }
    ]


def test_centrality_leaders_use_existing_artifacts_and_membership() -> None:
    service = NetworkService(
        _monthly_reader(), GraphLimits(max_nodes=100, max_edges=100)
    )

    if_result = service.centrality_leaders("monthly-run", metric="if")
    wif_result = service.centrality_leaders(
        "monthly-run", metric="wif", period="2017-04"
    )

    assert [item["period"] for item in if_result["periods"]] == [
        "2017-03",
        "2017-04",
    ]
    assert if_result["periods"][0]["spreader"] == {
        "user_id": "m2",
        "display_user_id": "m2",
        "centrality": 0.5,
        "community_id": "1",
        "community_assignment_status": "available",
    }
    assert if_result["periods"][0]["influencer"]["community_id"] == "1"
    assert wif_result["periods"][0]["spreader"]["community_id"] is None
    assert (
        wif_result["periods"][0]["spreader"]["community_assignment_status"]
        == "unavailable"
    )
    assert wif_result["periods"][0]["influencer"]["community_id"] == "9"
    CentralityLeadersResponse(**if_result)
    CentralityLeadersResponse(**wif_result)


def test_network_view_rejects_invalid_filter_combinations() -> None:
    service = NetworkService(
        _monthly_reader(), GraphLimits(max_nodes=100, max_edges=100)
    )

    with pytest.raises(InvalidFilterError, match="sampling"):
        service.graph(
            "monthly-run",
            metric="if",
            period="2017-03",
            community_id=None,
            min_weight=0,
            max_nodes=10,
            max_edges=10,
            view="communities",
            sampling="community_balanced",
        )

    with pytest.raises(InvalidFilterError, match="community_id"):
        service.graph(
            "monthly-run",
            metric="if",
            period="2017-03",
            community_id="1",
            min_weight=0,
            max_nodes=10,
            max_edges=10,
            view="communities",
            sampling=None,
        )
