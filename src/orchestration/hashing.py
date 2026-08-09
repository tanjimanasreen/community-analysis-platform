import hashlib
import json
from typing import Any, Mapping, Sequence

from src.orchestration.models import (
    DatasetIdentity,
    ThemeInputBundle,
    TopicInputBundle,
    ValidatedRunConfiguration,
)


def get_canonical_json(data: Any) -> bytes:
    """Return canonical JSON bytes for deterministic hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hash_mapping(mapping: Mapping[str, Any]) -> str:
    """Generate a stable SHA-256 digest from a dictionary/mapping."""
    return hashlib.sha256(get_canonical_json(mapping)).hexdigest()


def hash_file(filepath: str) -> str:
    """Compute SHA-256 for a file without loading the entire file into memory."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
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
    """Build a deterministic cache key for a pipeline stage."""
    components = {
        "stage": stage,
        "semantic_version": semantic_version,
        "input_hashes": sorted(list(input_hashes)),
        "config_subset": config_subset,
    }
    return hash_mapping(components)


def topic_cache_key_fn(context: Any, parameters: dict[str, Any]) -> str:
    """
    Prefect cache key function for topic modeling.

    Includes:
        - topic input artifact SHA-256 hashes
        - preprocessing configuration
        - LDA configuration (num_topics, passes, iterations, random_state, alpha, eta)
        - matching thresholds
        - semantic implementation version

    Explicitly excludes:
        - theme provider settings
        - theme prompt version
        - visualization settings
        - documentation-only metadata
        - unrelated network configuration
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

    p_ctx = parameters.get("context")
    if p_ctx and getattr(p_ctx, "pipeline_run_id", None):
        hashes.append(str(p_ctx.pipeline_run_id))

    raw = config.raw_config
    config_subset = {
        "preprocessing": raw.get("preprocessing", {}),
        "lda": raw.get("lda", {}),
        "matching": raw.get("matching", {}),
    }

    return build_stage_cache_key(
        stage="topic_model",
        semantic_version="1.1.0",
        input_hashes=hashes,
        config_subset=config_subset,
    )


def network_cache_key_fn(context: Any, parameters: dict[str, Any]) -> str:
    """
    Prefect cache key function for network and community detection.
    """
    dataset_identity: DatasetIdentity | None = parameters.get("dataset_identity")
    config: ValidatedRunConfiguration | None = parameters.get("config")

    if not dataset_identity or not config:
        return ""

    hashes = [dataset_identity.sha256]
    p_ctx = parameters.get("context")
    if p_ctx and getattr(p_ctx, "pipeline_run_id", None):
        hashes.append(str(p_ctx.pipeline_run_id))

    raw = config.raw_config
    config_subset = {
        "content_type": raw.get("content_type"),
        "data_type": raw.get("data_type"),
        "month": raw.get("month"),
        "year": raw.get("year"),
        "creator_relation": raw.get("creator_relation"),
        "spreader_relation": raw.get("spreader_relation"),
        "creator_node_column": raw.get("creator_node_column"),
        "spreader_node_column": raw.get("spreader_node_column"),
        "text_node_column": raw.get("text_node_column"),
        "date_column": raw.get("date_column"),
        "graph_thresholds": raw.get("graph_thresholds", {}),
        "louvain": raw.get("louvain", {}),
        "dashboard": {
            "graph_sample_max_edges": raw.get("dashboard", {}).get(
                "graph_sample_max_edges"
            )
        },
        "min_total_post": raw.get("min_total_post"),
        "min_shared_post": raw.get("min_shared_post"),
        "min_members": raw.get("min_members"),
    }

    return build_stage_cache_key(
        stage="network_community",
        semantic_version="1.1.0",
        input_hashes=hashes,
        config_subset=config_subset,
    )


def theme_cache_key_fn(context: Any, parameters: dict[str, Any]) -> str:
    """
    Prefect cache key function for theme generation and visualization.
    """
    input_bundle: ThemeInputBundle | None = parameters.get("input_bundle")
    config: ValidatedRunConfiguration | None = parameters.get("config")

    if not input_bundle or not config:
        return ""

    hashes = [ref.sha256 for ref in input_bundle.monthly_topic_outputs.values()]
    p_ctx = parameters.get("context")
    if p_ctx and getattr(p_ctx, "pipeline_run_id", None):
        hashes.append(str(p_ctx.pipeline_run_id))

    raw = config.raw_config
    theme = raw.get("theme", {})
    config_subset = {
        "content_type": raw.get("content_type"),
        "data_type": raw.get("data_type"),
        "year": raw.get("year"),
        "theme_provider": raw.get("theme_provider", {}),
        "prompt_version": raw.get("prompt_version"),
        "render_visuals": theme.get("render_visuals", raw.get("render_visuals")),
        "similarity_model": theme.get(
            "similarity_model", raw.get("similarity_model_name")
        ),
        "clustering_enabled": theme.get("clustering_enabled", False),
        "clustering_provider": theme.get("clustering_provider", "tei"),
        "clustering_model": theme.get(
            "clustering_model", "sentence-transformers/all-MiniLM-L6-v2"
        ),
        "clustering_min_cluster_size": theme.get("clustering_min_cluster_size", 2),
        "canonicalization_min_cluster_size": theme.get(
            "canonicalization_min_cluster_size", 2
        ),
        "clustering_metric": theme.get("clustering_metric", "euclidean"),
        "transition_threshold": theme.get("transition_threshold"),
        "reply_transition_threshold": theme.get("reply_transition_threshold"),
        "max_workers": theme.get("max_workers"),
    }

    return build_stage_cache_key(
        stage="theme_generation",
        semantic_version="1.2.0",
        input_hashes=hashes,
        config_subset=config_subset,
    )
