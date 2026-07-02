import csv

import pandas as pd

from src.graph_store.base import GraphRepository
from src.pipelines.ingestion_pipeline import (
    build_interaction_dataframe,
    build_snapshot_meta,
    run_ingestion_pipeline,
)


class FakeRepository:
    def __init__(self):
        self.import_calls = []

    def clear(self):
        pass

    def create_indexes(self):
        pass

    def import_raw_data(self, data_path, platform):
        pass

    def import_interactions(self, csv_path, snapshot_meta):
        self.import_calls.append((csv_path, snapshot_meta))

    def export_interactions(self, snapshot_meta, out_path):
        pass

    def get_user_interactions(self, snapshot_meta):
        return []

    def get_distinct_users(self):
        return []

    def close(self):
        pass


def test_fake_repository_satisfies_graph_repository_protocol():
    assert isinstance(FakeRepository(), GraphRepository)


def test_build_interaction_dataframe_from_legacy_reply_csv_contract():
    raw = pd.DataFrame(
        [
            {
                "source": "{'unique_id': 'm1', 'text': 'one'}",
                "target": "{'user_id': 'u1', 'username': 'alice'}",
                "relation": "REPLIED_TO",
            },
            {
                "source": "{'unique_id': 'm1', 'text': 'one'}",
                "target": "{'user_id': 'u2', 'username': 'bob'}",
                "relation": "REPLIED_BY",
            },
            {
                "source": "{'unique_id': 'm2', 'text': 'two'}",
                "target": "{'user_id': 'u1', 'username': 'alice'}",
                "relation": "REPLIED_TO",
            },
            {
                "source": "{'unique_id': 'm2', 'text': 'two'}",
                "target": "{'user_id': 'u1', 'username': 'alice'}",
                "relation": "REPLIED_BY",
            },
        ]
    )
    config = {
        "data_type": "twitter",
        "content_type": "reply",
        "month": "03",
        "year": "2017",
    }

    users, network, interactions = build_interaction_dataframe(raw, config)

    assert set(users["user_id"]) == {"u1", "u2"}
    assert list(network["from_id"]) == ["u1", "u1"]
    assert list(network["forwarder_id"]) == ["u2", "u1"]
    assert len(interactions) == 1
    edge = interactions.iloc[0]
    assert edge["source"] == "u1"
    assert edge["target"] == "u2"
    assert edge["total_post"] == 2
    assert edge["shared_post"] == 1
    assert edge["weighted_post"] == 0.5
    assert edge["month"] == 3
    assert edge["year"] == 2017


def test_run_ingestion_pipeline_writes_and_imports_interaction_csv(tmp_path):
    raw_path = tmp_path / "raw.csv"
    out_path = tmp_path / "derived.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "target", "relation"])
        writer.writeheader()
        writer.writerow(
            {
                "source": "{'unique_id': 'm1', 'text': 'one'}",
                "target": "{'user_id': 'u1', 'username': 'alice'}",
                "relation": "REPLIED_TO",
            }
        )
        writer.writerow(
            {
                "source": "{'unique_id': 'm1', 'text': 'one'}",
                "target": "{'user_id': 'u2', 'username': 'bob'}",
                "relation": "REPLIED_BY",
            }
        )

    config = {
        "data_type": "twitter",
        "content_type": "reply",
        "month": "march",
        "year": "2017",
        "input_path": str(raw_path),
        "output_base_path": str(tmp_path),
    }
    repo = FakeRepository()

    result = run_ingestion_pipeline(
        config,
        repository=repo,
        output_csv_path=out_path,
        import_to_repository=True,
    )

    assert result.output_path == out_path
    assert out_path.exists()
    assert repo.import_calls == [(out_path, build_snapshot_meta(config))]
    derived = pd.read_csv(out_path)
    assert list(derived.columns) == [
        "source",
        "target",
        "total_post",
        "shared_post",
        "weighted_post",
        "data_type",
        "content_type",
        "month",
        "year",
    ]
    assert derived.loc[0, "source"] == "u1"
    assert derived.loc[0, "target"] == "u2"
