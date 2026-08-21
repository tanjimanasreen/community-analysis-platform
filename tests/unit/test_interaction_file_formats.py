from pathlib import Path

import pandas as pd

from src.cli import _csv_has_relation_column
from src.graph_store.memgraph_repository import MemgraphRepository
from src.pipelines.ingestion_pipeline import write_interactions


class FakeClient:
    def __init__(self):
        self.calls = []

    def execute_query(self, query, params=None):
        self.calls.append((query, params))
        return [], None, []


def _interactions():
    return pd.DataFrame(
        [
            {
                "source": "a",
                "target": "b",
                "total_post": 10,
                "shared_post": 5,
                "weighted_post": 0.5,
                "data_type": "twitter",
                "content_type": "reply",
                "month": 3,
                "year": 2017,
            }
        ]
    )


def test_parquet_interactions_round_trip_into_repository(tmp_path: Path):
    path = write_interactions(_interactions(), tmp_path / "interactions.parquet")
    client = FakeClient()
    repository = MemgraphRepository(client=client)

    repository.import_interactions(
        path,
        {
            "data_type": "twitter",
            "content_type": "reply",
            "month": 3,
            "year": 2017,
        },
    )

    assert len(client.calls) == 1
    assert client.calls[0][1]["rows"][0]["weighted_post"] == 0.5


def test_parquet_interactions_are_not_parsed_as_raw_relationship_csv(tmp_path: Path):
    path = tmp_path / "interactions.parquet"
    path.write_bytes(b"PAR1")

    assert _csv_has_relation_column(path) is False


def test_unknown_interaction_extension_is_rejected(tmp_path: Path):
    try:
        write_interactions(_interactions(), tmp_path / "interactions.data")
    except ValueError as exc:
        assert "expected .parquet" in str(exc)
    else:
        raise AssertionError("unsupported interaction extension was accepted")
