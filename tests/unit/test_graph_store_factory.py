import pytest

from src.graph_store import factory


class FakeMemgraphRepository:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_memgraph_is_resolved_from_runtime_database_config(monkeypatch):
    monkeypatch.setattr(factory, "MemgraphRepository", FakeMemgraphRepository)

    repository = factory.create_graph_repository(
        {
            "engine": "memgraph",
            "uri": "bolt://graph.example:7687",
            "user": "graph-user",
            "password": "graph-password",
        }
    )

    assert isinstance(repository, FakeMemgraphRepository)
    assert repository.kwargs == {
        "uri": "bolt://graph.example:7687",
        "user": "graph-user",
        "password": "graph-password",
    }


def test_unimplemented_graph_backend_fails_instead_of_using_memgraph(monkeypatch):
    def fail_if_constructed(**_kwargs):
        raise AssertionError("MemgraphRepository must not be used for another engine")

    monkeypatch.setattr(factory, "MemgraphRepository", fail_if_constructed)

    with pytest.raises(
        ValueError,
        match="Graph database backend 'neo4j' is not currently implemented.*memgraph",
    ):
        factory.create_graph_repository(
            {
                "engine": "neo4j",
                "uri": "bolt://legacy.example:7687",
                "user": "neo4j",
                "password": "secret",
            }
        )


def test_memgraph_repository_connectivity_stays_behind_repository_boundary():
    from src.graph_store.memgraph_repository import MemgraphRepository

    class FakeClient:
        def __init__(self):
            self.calls = []

        def execute_query(self, query, parameters=None):
            self.calls.append((query, parameters))
            return []

    client = FakeClient()
    repository = MemgraphRepository(client=client)

    repository.check_connectivity()

    assert client.calls == [("RETURN 1 AS ok", None)]
