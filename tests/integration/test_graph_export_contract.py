import pytest
import os
import time
import csv
from src.graph_store.memgraph_client import MemgraphClient
from src.graph_store.neo4j_exporter import Neo4jExporter

@pytest.fixture(scope="module")
def memgraph():
    # Assumes db-up was run before pytest
    client = MemgraphClient(uri="bolt://localhost:7687", user="", password="")
    
    # Wait for connectivity
    max_retries = 5
    for _ in range(max_retries):
        try:
            with client.get_driver() as driver:
                driver.verify_connectivity()
            break
        except Exception:
            time.sleep(1)
    else:
        pytest.skip("Could not connect to Memgraph. Is docker-compose running?")
        
    # Seed some data
    client.execute_query("MATCH (n) DETACH DELETE n;")
    client.execute_query("""
        CREATE (u:User {user_id: "1", username: "alice"})
        CREATE (m:Message {unique_id: "msg1", date: datetime("2019-11-15T12:00:00Z")})
        CREATE (u)-[:CREATED]->(m)
    """)
    yield client
    
    # Teardown
    client.execute_query("MATCH (n) DETACH DELETE n;")

def test_memgraph_export_contract(memgraph, tmp_path):
    exporter = Neo4jExporter(uri="bolt://localhost:7687", user="", password="")
    output_file = tmp_path / "export.csv"
    
    # Run the telegram query which expects month 11 year 2019
    exporter.export('telegram', year=2019, month=11, output_file=str(output_file))
    
    assert output_file.exists()
    
    with open(output_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    assert len(rows) == 1
    assert "source" in rows[0]
    assert "target" in rows[0]
    assert "relation" in rows[0]
    assert "alice" in rows[0]["source"]
    assert "CREATED" == rows[0]["relation"]
