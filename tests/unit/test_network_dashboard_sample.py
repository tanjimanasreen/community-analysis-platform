from types import SimpleNamespace

import pandas as pd

from src.api.errors import ArtifactNotFoundError
from src.api.services.network_service import GraphLimits, NetworkService


class _Reader:
    def __init__(self):
        self.records = {
            "community_graph_sample_absolute_march": pd.DataFrame(
                [
                    {
                        "source": "u1",
                        "target": "u2",
                        "community_number": "1",
                        "direction": "Directed",
                        "weight": 10.0,
                    },
                    {
                        "source": "u3",
                        "target": "u4",
                        "community_number": "2",
                        "direction": "Directed",
                        "weight": 9.0,
                    },
                ]
            ),
            "community_summary_absolute_march": pd.DataFrame(
                [
                    {
                        "community_id": "1",
                        "node_count": 50,
                        "edge_count": 1000,
                        "total_weight": 5000.0,
                        "x": None,
                        "y": None,
                    },
                    {
                        "community_id": "2",
                        "node_count": 25,
                        "edge_count": 500,
                        "total_weight": 2000.0,
                        "x": None,
                        "y": None,
                    },
                ]
            ),
            "communities_absolute_march": pd.DataFrame(
                [
                    {
                        "source": "full",
                        "target": "graph",
                        "community_number": "1",
                        "direction": "Directed",
                        "weight": 1.0,
                    }
                ]
            ),
        }
        self.read_keys = []

    def get_record(self, run_id, key):
        if key not in self.records:
            raise ArtifactNotFoundError(run_id, key)
        return SimpleNamespace(key=key)

    def find_records(self, run_id, *, key_prefix):
        return [
            SimpleNamespace(key=key)
            for key in self.records
            if key.startswith(key_prefix)
        ]

    def read_parquet_record(self, run_id, record, *, columns=None, filters=None):
        self.read_keys.append(record.key)
        frame = self.records[record.key]
        return frame.loc[:, columns].copy() if columns else frame.copy()


def test_global_graph_uses_bounded_sample_and_exact_summary_totals():
    reader = _Reader()
    service = NetworkService(reader, GraphLimits(max_nodes=100, max_edges=100))

    result = service.graph(
        "run-1",
        metric="if",
        community_id=None,
        min_weight=0,
        max_nodes=10,
        max_edges=10,
    )

    assert result["available_nodes"] == 75
    assert result["available_edges"] == 1500
    assert result["returned_edges"] == 2
    assert result["sampled"] is True
    assert "community_graph_sample_absolute_march" in reader.read_keys
    assert "communities_absolute_march" not in reader.read_keys


def test_filtered_graph_falls_back_to_authoritative_full_artifact():
    reader = _Reader()
    service = NetworkService(reader, GraphLimits(max_nodes=100, max_edges=100))

    service.graph(
        "run-1",
        metric="if",
        community_id=None,
        min_weight=0.5,
        max_nodes=10,
        max_edges=10,
    )

    assert "communities_absolute_march" in reader.read_keys


def test_community_detail_requests_push_down_numeric_community_filter():
    reader = _Reader()
    observed_filters = []
    original = reader.read_parquet_record

    def read_with_filter_spy(run_id, record, *, columns=None, filters=None):
        observed_filters.append(filters)
        return original(run_id, record, columns=columns, filters=filters)

    reader.read_parquet_record = read_with_filter_spy
    service = NetworkService(reader, GraphLimits(max_nodes=100, max_edges=100))

    service.graph(
        "run-1",
        metric="if",
        community_id="1",
        min_weight=0,
        max_nodes=10,
        max_edges=10,
    )

    assert [("community_number", "==", 1)] in observed_filters


def test_longitudinal_global_graph_uses_samples_and_exact_node_indexes():
    reader = _Reader()
    reader.records.update(
        {
            "community_graph_sample_absolute_april": pd.DataFrame(
                [
                    {
                        "source": "u2",
                        "target": "u5",
                        "community_number": "3",
                        "direction": "Directed",
                        "weight": 8.0,
                    }
                ]
            ),
            "community_summary_absolute_april": pd.DataFrame(
                [
                    {
                        "community_id": "3",
                        "node_count": 2,
                        "edge_count": 300,
                        "total_weight": 900.0,
                        "x": None,
                        "y": None,
                    }
                ]
            ),
            "community_node_index_absolute_march": pd.DataFrame(
                {"node_id": ["u1", "u2", "u3", "u4"]}
            ),
            "community_node_index_absolute_april": pd.DataFrame(
                {"node_id": ["u2", "u5"]}
            ),
        }
    )
    service = NetworkService(reader, GraphLimits(max_nodes=100, max_edges=100))

    result = service.graph(
        "run-1",
        metric="if",
        community_id=None,
        min_weight=0,
        max_nodes=10,
        max_edges=10,
    )

    assert result["available_nodes"] == 5
    assert result["available_edges"] == 1800
    assert result["returned_edges"] == 3
    assert "communities_absolute_march" not in reader.read_keys
