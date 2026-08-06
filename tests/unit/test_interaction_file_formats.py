from pathlib import Path

import pandas as pd

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


def test_csv_interactions_round_trip_into_repository(tmp_path: Path):
    path = write_interactions(_interactions(), tmp_path / "interactions.csv")
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


def test_unknown_interaction_extension_is_rejected(tmp_path: Path):
    try:
        write_interactions(_interactions(), tmp_path / "interactions.data")
    except ValueError as exc:
        assert "expected .csv or .parquet" in str(exc)
    else:
        raise AssertionError("unsupported interaction extension was accepted")
