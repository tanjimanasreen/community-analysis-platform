import hashlib
import json
from typing import Any, Mapping, Sequence

def get_canonical_json(data: Any) -> bytes:
    """Return canonical JSON bytes for deterministic hashing."""
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')

def hash_mapping(mapping: Mapping[str, Any]) -> str:
    """Generate a stable SHA-256 digest from a dictionary/mapping."""
    return hashlib.sha256(get_canonical_json(mapping)).hexdigest()

def hash_file(filepath: str) -> str:
    """Compute SHA-256 for a file without loading the entire file into memory."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def build_stage_cache_key(
    *,
    stage: str,
    semantic_version: str,
    input_hashes: Sequence[str],
    config_subset: Mapping[str, Any],
) -> str:
    """
    Build a deterministic cache key for a pipeline stage.
    """
    components = {
        "stage": stage,
        "semantic_version": semantic_version,
        "input_hashes": sorted(list(input_hashes)),
        "config_subset": config_subset
    }
    return hash_mapping(components)
