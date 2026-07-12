import hashlib
import json
from typing import Any, Mapping, Sequence
from src.orchestration.models import TopicInputBundle, ValidatedRunConfiguration

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

def topic_cache_key_fn(context: Any, parameters: dict[str, Any]) -> str:
    """
    Prefect cache key function for topic modeling.
    Extracts the hashes of the input CSVs, preprocessing config, and LDA parameters.
    """
    input_bundle: TopicInputBundle | None = parameters.get("input_bundle")
    config: ValidatedRunConfiguration | None = parameters.get("config")
    
    if not input_bundle or not config:
        return "" 

    hashes = [
        input_bundle.absolute_community_messages.sha256,
        input_bundle.weighted_community_messages.sha256,
        input_bundle.matched_communities.sha256,
    ]
    if input_bundle.partial_matched_communities:
        hashes.append(input_bundle.partial_matched_communities.sha256)
        
    config_subset = {
        "preprocessing": config.raw_config.get("preprocessing", {}),
        "lda": config.raw_config.get("lda", {}),
        "matching": config.raw_config.get("matching", {})
    }
    
    return build_stage_cache_key(
        stage="topic_model",
        semantic_version="1.0.0",
        input_hashes=hashes,
        config_subset=config_subset
    )

