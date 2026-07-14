import os
from src.orchestration.hashing import hash_mapping, hash_file, build_stage_cache_key

def test_hash_mapping_order_independence():
    dict1 = {"a": 1, "b": 2}
    dict2 = {"b": 2, "a": 1}
    assert hash_mapping(dict1) == hash_mapping(dict2)

def test_hash_mapping_relevance():
    dict1 = {"a": 1, "b": 2}
    dict2 = {"a": 1, "b": 3}
    assert hash_mapping(dict1) != hash_mapping(dict2)

def test_hash_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello", encoding="utf-8")
    h1 = hash_file(str(f))
    f.write_text("hello world", encoding="utf-8")
    h2 = hash_file(str(f))
    assert h1 != h2

def test_build_stage_cache_key():
    key1 = build_stage_cache_key(
        stage="test",
        semantic_version="v1",
        input_hashes=["hashB", "hashA"],
        config_subset={"param": 1}
    )
    key2 = build_stage_cache_key(
        stage="test",
        semantic_version="v1",
        input_hashes=["hashA", "hashB"], # different order
        config_subset={"param": 1}
    )
    key3 = build_stage_cache_key(
        stage="test",
        semantic_version="v2",
        input_hashes=["hashA", "hashB"],
        config_subset={"param": 1}
    )
    assert key1 == key2
    assert key1 != key3
