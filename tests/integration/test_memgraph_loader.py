import pytest
import os
from unittest.mock import MagicMock
from src.ingestion.memgraph_loader import generate_cypher, MemgraphLoader, clean_dict_string

def test_clean_dict_string():
    raw = "{'date': neo4j.time.DateTime(2019, 11, 1, 10, 0, 0, tzinfo=<UTC>), 'text': 'hi'}"
    cleaned = clean_dict_string(raw)
    assert "neo4j_time_" in cleaned
    assert "neo4j.time.DateTime" not in cleaned

def test_generate_cypher_telegram():
    source = {'user_id': 'user1', 'username': 'alice'}
    target = {'unique_id': 'msg1', 'text': 'hello'}
    relation = 'CREATED'
    
    query, params = generate_cypher(source, target, relation, 'telegram')
    
    assert query is not None
    assert "MERGE (s:User {user_id: $source_pk})" in query
    assert "MERGE (t:Message {unique_id: $target_pk})" in query
    assert "MERGE (s)-[r:CREATED]->(t)" in query
    
    assert params['source_pk'] == 'user1'
    assert params['target_pk'] == 'msg1'
    assert params['platform'] == 'telegram'

def test_generate_cypher_fallback_pk():
    source = {'id': 'user1', 'username': 'alice'} # id instead of user_id
    target = {'id': 'msg1', 'text': 'hello'}      # id instead of unique_id
    relation = 'CREATED'
    
    query, params = generate_cypher(source, target, relation, 'telegram')
    
    assert query is not None
    assert params['source_pk'] == 'user1'
    assert params['target_pk'] == 'msg1'

def test_memgraph_loader_with_mock(tmp_path):
    # Create dummy CSV
    csv_file = tmp_path / "dummy.csv"
    with open(csv_file, "w") as f:
        f.write("source,target,relation\n")
        f.write("\"{'user_id': 'u1'}\",\"{'unique_id': 'm1'}\",CREATED\n")
        f.write("\"{'user_id': 'u2'}\",\"{'unique_id': 'm2'}\",INVALID_REL\n") # Should fail mapping

    mock_client = MagicMock()
    loader = MemgraphLoader(client=mock_client)
    
    success, error = loader.load_csv(str(csv_file), 'telegram')
    
    assert success == 1
    assert error == 1
    assert mock_client.execute_query.call_count == 1
