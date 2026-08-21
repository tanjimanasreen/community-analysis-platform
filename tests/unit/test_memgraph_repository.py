import csv

import pytest

from src.graph_store.memgraph_repository import MemgraphRepository


class FakeClient:
    def __init__(self, fail_existing_index=False):
        self.calls = []
        self.fail_existing_index = fail_existing_index

    def execute_query(self, query, parameters=None):
        self.calls.append((query, parameters))
        if self.fail_existing_index and query.startswith("CREATE INDEX"):
            raise RuntimeError("Index already exists")
        return [], None, []


def test_create_indexes_uses_current_thesis_labels():
    client = FakeClient()
    repo = MemgraphRepository(client=client)

    repo.create_indexes()

    queries = [query for query, _params in client.calls]
    assert "CREATE INDEX ON :User(user_id)" in queries
    assert "CREATE INDEX ON :Forward_Message(unique_id)" in queries
    assert "CREATE INDEX ON :Twitter_User(user_id)" in queries
    assert "CREATE INDEX ON :Retweet_Quote(unique_id)" in queries


def test_create_indexes_ignores_existing_index_errors():
    client = FakeClient(fail_existing_index=True)
    repo = MemgraphRepository(client=client)

    repo.create_indexes()

    assert len(client.calls) > 0


def test_import_interactions_skips_self_edges_and_preserves_metrics(tmp_path):
    csv_path = tmp_path / "interactions.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source",
                "target",
                "total_post",
                "shared_post",
                "weighted_post",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "source": "u1",
                "target": "u2",
                "total_post": "4",
                "shared_post": "2",
                "weighted_post": "0.5",
            }
        )
        writer.writerow(
            {
                "source": "u1",
                "target": "u1",
                "total_post": "4",
                "shared_post": "1",
                "weighted_post": "0.25",
            }
        )

    client = FakeClient()
    repo = MemgraphRepository(client=client)
    repo.import_interactions(
        csv_path,
        {
            "data_type": "twitter",
            "content_type": "reply",
            "month": "3",
            "year": "2017",
        },
    )

    assert len(client.calls) == 1
    query, params = client.calls[0]
    assert "UNWIND $rows AS row" in query
    assert list(params) == ["rows"]
    assert len(params["rows"]) == 1

    row = params["rows"][0]
    assert row == {
        "source": "u1",
        "target": "u2",
        "shared_post": 2,
        "total_post": 4,
        "weighted_post": 0.5,
        "data_type": "twitter",
        "content_type": "reply",
        "month": 3,
        "year": 2017,
    }
    assert all(
        batch_row["source"] != batch_row["target"] for batch_row in params["rows"]
    )


def test_import_interactions_respects_configured_batch_boundaries(tmp_path):
    csv_path = tmp_path / "interactions.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source",
                "target",
                "total_post",
                "shared_post",
                "weighted_post",
            ],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "source": "u1",
                    "target": "u2",
                    "total_post": "4",
                    "shared_post": "2",
                    "weighted_post": "0.5",
                },
                {
                    "source": "u2",
                    "target": "u3",
                    "total_post": "5",
                    "shared_post": "1",
                    "weighted_post": "0.2",
                },
                {
                    "source": "u3",
                    "target": "u4",
                    "total_post": "8",
                    "shared_post": "6",
                    "weighted_post": "0.75",
                },
            ]
        )

    client = FakeClient()
    repo = MemgraphRepository(client=client, interaction_batch_size=2)
    repo.import_interactions(
        csv_path,
        {
            "data_type": "twitter",
            "content_type": "reply",
            "month": "3",
            "year": "2017",
        },
    )

    assert len(client.calls) == 2
    assert all("UNWIND $rows AS row" in query for query, _params in client.calls)

    first_rows = client.calls[0][1]["rows"]
    second_rows = client.calls[1][1]["rows"]
    assert [len(first_rows), len(second_rows)] == [2, 1]
    assert [(row["source"], row["target"]) for row in first_rows + second_rows] == [
        ("u1", "u2"),
        ("u2", "u3"),
        ("u3", "u4"),
    ]
    assert [row["weighted_post"] for row in first_rows + second_rows] == [
        0.5,
        0.2,
        0.75,
    ]


def test_export_interactions_rejects_generated_csv(tmp_path):
    repo = MemgraphRepository(client=FakeClient())

    with pytest.raises(ValueError, match=r"expected \.parquet"):
        repo.export_interactions(
            {
                "data_type": "twitter",
                "content_type": "reply",
                "month": "3",
                "year": "2017",
            },
            tmp_path / "interactions.csv",
        )


def test_import_raw_data_uses_legacy_csv_contract(tmp_path):
    csv_path = tmp_path / "raw.csv"
    csv_path.write_text(
        "source,target,relation\n"
        "\"{'user_id': 'u1', 'username': 'alice'}\","
        "\"{'unique_id': 'm1', 'text': 'hello'}\",CREATED\n",
        encoding="utf-8",
    )

    client = FakeClient()
    repo = MemgraphRepository(client=client)
    repo.import_raw_data(csv_path, "telegram")

    assert len(client.calls) == 1
    query, params = client.calls[0]
    assert "UNWIND $rows AS row" in query
    assert "MERGE (s:User {user_id: row.source_pk})" in query
    assert "MERGE (t:Message {unique_id: row.target_pk})" in query
    assert "MERGE (s)-[r:CREATED]->(t)" in query
    assert params["platform"] == "telegram"
    assert len(params["rows"]) == 1

    row = params["rows"][0]
    assert row["source_pk"] == "u1"
    assert row["target_pk"] == "m1"
    assert row["source_props"] == {"user_id": "u1", "username": "alice"}
    assert row["target_props"] == {"unique_id": "m1", "text": "hello"}


def test_import_raw_data_requires_legacy_csv_columns(tmp_path):
    csv_path = tmp_path / "raw.csv"
    csv_path.write_text("source,target\n{},{}\n", encoding="utf-8")

    repo = MemgraphRepository(client=FakeClient())

    try:
        repo.import_raw_data(csv_path, "telegram")
    except ValueError as exc:
        assert "relation" in str(exc)
    else:
        raise AssertionError("Expected missing relation column to fail")
