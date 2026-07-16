import pytest
import os
from src.graph_store.neo4j_exporter import Neo4jExporter


def test_neo4j_exporter_init():
    exporter = Neo4jExporter(
        uri="neo4j://localhost", user="test", password="pwd", database="testdb"
    )
    assert exporter.uri == "neo4j://localhost"
    assert exporter.user == "test"
    assert exporter.password == "pwd"
    assert exporter.database == "testdb"


def test_neo4j_exporter_get_query():
    exporter = Neo4jExporter()
    query = exporter.get_query("telegram")
    assert "MATCH (source:User)-[r:CREATED]->(target:Message)" in query

    with pytest.raises(ValueError):
        exporter.get_query("invalid")


def test_neo4j_exporter_query_formatting():
    # We can test that the query has the parameter placeholders
    exporter = Neo4jExporter()
    query = exporter.get_query("twitter_reply")
    assert "{year:$year, month:$month, day:1}" in query
    assert "{year:$year_next, month: $month_next, day: 1}" in query
