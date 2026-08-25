from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.orchestration.models import (
    DatasetIdentity,
    ThemeInputBundle,
    TopicInputBundle,
    ValidatedRunConfiguration,
)
from src.themes.benchmark.contracts import (
    OUTPUT_SCHEMA_VERSION,
    THEME_PROMPT_CONTRACT_VERSION,
)

NETWORK_STAGE_CACHE_VERSION = "2.0.0"
TOPIC_STAGE_CACHE_VERSION = "3.0.0"
THEME_STAGE_CACHE_VERSION = "3.0.0"

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Stage dependency scopes are deliberately conservative. Shared analytical files
# are symbol-scoped where practical so an unrelated function in the monolithic
# social-network pipeline does not force every stage to miss its cache.
_STAGE_CODE_PATHS: Mapping[str, tuple[str, ...]] = {
    "network_community": (
        "pyproject.toml",
        "uv.lock",
        "src/orchestration/hashing.py",
        "src/orchestration/stage_cache.py",
        "src/ingestion",
        "src/network",
        "src/communities",
        "src/reporting/output_contract.py",
    ),
    "topic_model": (
        "pyproject.toml",
        "uv.lock",
        "src/orchestration/hashing.py",
        "src/orchestration/stage_cache.py",
        "src/topics",
        "src/text",
        "src/reporting/output_contract.py",
    ),
    "theme_generation": (
        "pyproject.toml",
        "uv.lock",
        "src/orchestration/hashing.py",
        "src/orchestration/stage_cache.py",
        "src/themes",
        "src/providers",
        "src/visualization",
        "src/reporting/output_contract.py",
    ),
}

_STAGE_CODE_SYMBOLS: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    "network_community": {
        "src/orchestration/tasks.py": ("run_monthly_network_community_phase_task",),
        "src/pipelines/social_network_pipeline.py": (
            "save_parquet_to_directory",
            "_dashboard_graph_sample",
            "_community_summary",
            "_community_node_index",
            "run_network_phase",
            "run_community_phase",
            "save_pipeline_topic_inputs",
            "run_network_community_pipeline",
        ),
    },
    "topic_model": {
        "src/orchestration/tasks.py": (
            "_topic_output_artifacts",
            "_topic_output_bundle_from_artifacts",
            "run_monthly_topic_phase_task",
        ),
        "src/pipelines/social_network_pipeline.py": (
            "save_parquet_to_directory",
            "run_topic_phase",
            "save_pipeline_theme_inputs",
        ),
    },
    "theme_generation": {
        "src/orchestration/tasks.py": (
            "_theme_output_artifacts",
            "_theme_output_bundle_from_artifacts",
            "run_monthly_themes_task",
        ),
        "src/pipelines/theme_pipeline.py": (
            "process_single_file_themes",
            "run_theme_pipeline",
            "run_theme_pipeline_from_bundle",
            "run_theme_pipeline_from_monthly_data",
            "_sha256_file",
            "_period_for_month",
        ),
    },
}


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


def _iter_dependency_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise ValueError(f"stage code dependency does not exist: {path}")
    return sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file()
        and "__pycache__" not in candidate.parts
        and candidate.suffix not in {".pyc", ".pyo"}
    )


def hash_code_dependencies(
    relative_paths: Sequence[str], *, project_root: str | Path | None = None
) -> str:
    """Hash the exact bytes and relative names of stage code/resource paths."""
    root = Path(project_root or _PROJECT_ROOT).resolve()
    hasher = hashlib.sha256()
    for relative in sorted(relative_paths):
        dependency = (root / relative).resolve()
        try:
            dependency.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"stage dependency escapes project root: {relative}"
            ) from exc
        for file_path in _iter_dependency_files(dependency):
            rel = file_path.relative_to(root).as_posix()
            hasher.update(rel.encode("utf-8"))
            hasher.update(b"\0")
            with file_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    hasher.update(chunk)
            hasher.update(b"\0")
    return hasher.hexdigest()


def _hash_python_symbols(
    relative_path: str,
    symbols: Sequence[str],
    *,
    project_root: str | Path | None = None,
) -> str:
    """Hash selected top-level Python definitions without importing the module."""
    root = Path(project_root or _PROJECT_ROOT).resolve()
    source_path = (root / relative_path).resolve()
    try:
        source_path.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"stage symbol dependency escapes project root: {relative_path}"
        ) from exc
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    requested = set(symbols)
    found: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in requested:
                segment = ast.get_source_segment(source, node)
                if segment is None:
                    raise ValueError(
                        f"could not resolve source for {relative_path}::{node.name}"
                    )
                found[node.name] = segment

    missing = requested.difference(found)
    if missing:
        raise ValueError(
            f"missing stage code symbol(s) in {relative_path}: {sorted(missing)}"
        )

    return hash_mapping(
        {
            "path": relative_path,
            "symbols": {name: found[name] for name in sorted(found)},
        }
    )


def build_stage_code_fingerprint(
    stage: str, *, project_root: str | Path | None = None
) -> str:
    """Return a deterministic fingerprint for code/resources affecting a stage."""
    if stage not in _STAGE_CODE_PATHS:
        raise ValueError(f"unknown analytical stage for code fingerprint: {stage}")

    components: dict[str, Any] = {
        "paths": hash_code_dependencies(
            _STAGE_CODE_PATHS[stage], project_root=project_root
        ),
        "python_runtime": {
            "implementation": sys.implementation.name,
            "version": list(sys.version_info[:3]),
        },
        "symbols": {},
    }
    for relative_path, symbols in sorted(_STAGE_CODE_SYMBOLS.get(stage, {}).items()):
        components["symbols"][relative_path] = _hash_python_symbols(
            relative_path,
            symbols,
            project_root=project_root,
        )
    return hash_mapping(components)


def build_stage_cache_key(
    *,
    stage: str,
    semantic_version: str,
    input_hashes: Sequence[str],
    config_subset: Mapping[str, Any],
    code_fingerprint: str | None = None,
) -> str:
    """Build a deterministic content/config/code identity for a pipeline stage."""
    components = {
        "stage": stage,
        "semantic_version": semantic_version,
        "input_hashes": sorted(list(input_hashes)),
        "config_subset": config_subset,
        "code_fingerprint": code_fingerprint or "",
    }
    return hash_mapping(components)


def network_stage_cache_key(
    dataset_identity: DatasetIdentity, config: ValidatedRunConfiguration
) -> str:
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
        semantic_version=NETWORK_STAGE_CACHE_VERSION,
        input_hashes=[f"dataset:{dataset_identity.sha256}"],
        config_subset=config_subset,
        code_fingerprint=build_stage_code_fingerprint("network_community"),
    )


def _translation_cache_identity(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {"enabled": False}
    enabled = bool(raw.get("enabled", False))
    identity: dict[str, Any] = {"enabled": enabled}
    if enabled:
        identity.update(
            {
                "provider": str(raw.get("provider", "azure")).strip().lower(),
                "target_language": str(raw.get("target_language", "en"))
                .strip()
                .lower(),
                "contract_version": str(raw.get("contract_version", "v1")).strip(),
            }
        )
    return identity


def topic_stage_cache_key(
    input_bundle: TopicInputBundle, config: ValidatedRunConfiguration
) -> str:
    hashes = [
        "absolute_community_messages:"
        f"{input_bundle.absolute_community_messages.sha256}",
        "weighted_community_messages:"
        f"{input_bundle.weighted_community_messages.sha256}",
        f"matched_communities:{input_bundle.matched_communities.sha256}",
    ]
    if input_bundle.partial_matched_communities:
        hashes.append(
            "partial_matched_communities:"
            f"{input_bundle.partial_matched_communities.sha256}"
        )

    raw = config.raw_config
    config_subset = {
        "data_type": raw.get("data_type"),
        "content_type": raw.get("content_type"),
        "month": raw.get("month"),
        "year": raw.get("year"),
        "preprocessing": raw.get("preprocessing", {}),
        "translation": _translation_cache_identity(raw.get("translation", {})),
        "lda": raw.get("lda", {}),
        "matching": raw.get("matching", {}),
    }
    return build_stage_cache_key(
        stage="topic_model",
        semantic_version=TOPIC_STAGE_CACHE_VERSION,
        input_hashes=hashes,
        config_subset=config_subset,
        code_fingerprint=build_stage_code_fingerprint("topic_model"),
    )


_OPERATIONAL_PROVIDER_CONFIG_KEYS = {
    "rate_limit_rpm",
    "timeout_seconds",
    "max_retries",
    "content_filter_retry_delay_seconds",
    "log_content_filter_annotations",
    "models",
}


def _theme_provider_cache_config(raw: Mapping[str, Any]) -> dict[str, Any]:
    theme_provider = raw.get("theme_provider", {})
    if not isinstance(theme_provider, Mapping):
        theme_provider = {"primary": theme_provider}
    primary = str(theme_provider.get("primary", "mock"))
    fallback_enabled = bool(theme_provider.get("fallback", False))
    configured_chain = theme_provider.get("fallback_chain", [])
    if isinstance(configured_chain, str):
        configured_chain = [configured_chain]
    fallback_chain = list(configured_chain) if fallback_enabled else []
    provider_ids = [primary, *[str(item) for item in fallback_chain]]
    registry = raw.get("providers", {})
    if not isinstance(registry, Mapping):
        registry = {}

    selected_registry: dict[str, Any] = {}
    for provider_id in provider_ids:
        prefix = provider_id.split(":", 1)[0]
        provider_config = registry.get(prefix, {})
        if isinstance(provider_config, Mapping):
            selected_registry[prefix] = {
                key: value
                for key, value in provider_config.items()
                if key not in _OPERATIONAL_PROVIDER_CONFIG_KEYS
            }

    return {
        "primary": primary,
        "fallback": fallback_enabled,
        "fallback_chain": fallback_chain,
        "provider_generation_settings": selected_registry,
    }


def theme_stage_cache_key(
    input_bundle: ThemeInputBundle, config: ValidatedRunConfiguration
) -> str:
    from src.themes.theme_clustering import (
        CANONICALIZATION_CONTRACT_VERSION,
        CANONICALIZATION_GROUPING_METHOD,
        CANONICALIZATION_LINKAGE,
        CANONICALIZATION_METRIC,
        CANONICALIZATION_REPRESENTATION,
        CANONICALIZATION_SIMILARITY_THRESHOLD,
        MONTHLY_CLUSTER_ALLOW_SINGLE_CLUSTER,
        MONTHLY_CLUSTER_CONTRACT_VERSION,
        MONTHLY_CLUSTER_SELECTION_METHOD,
        MONTHLY_CLUSTERING_INPUT_NORMALIZED,
    )

    hashes = [
        f"period:{period}:{ref.sha256}"
        for period, ref in input_bundle.monthly_topic_outputs.items()
    ]
    raw = config.raw_config
    theme = raw.get("theme", {})
    config_subset = {
        "content_type": raw.get("content_type"),
        "data_type": raw.get("data_type"),
        "year": raw.get("year"),
        "theme_provider": _theme_provider_cache_config(raw),
        "prompt_contract_version": THEME_PROMPT_CONTRACT_VERSION,
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "render_visuals": theme.get("render_visuals", raw.get("render_visuals")),
        "evolution_similarity_enabled": theme.get(
            "evolution_similarity_enabled",
            theme.get("render_visuals", raw.get("render_visuals")),
        ),
        "similarity_model": theme.get(
            "similarity_model", raw.get("similarity_model_name")
        ),
        "similarity_model_revision": theme.get("similarity_model_revision"),
        "clustering_enabled": theme.get("clustering_enabled", False),
        "clustering_provider": theme.get("clustering_provider", "tei"),
        "clustering_model": theme.get(
            "clustering_model", "sentence-transformers/all-MiniLM-L6-v2"
        ),
        "clustering_model_revision": theme.get("clustering_model_revision"),
        "clustering_min_cluster_size": theme.get("clustering_min_cluster_size", 2),
        "clustering_input_normalized": MONTHLY_CLUSTERING_INPUT_NORMALIZED,
        "hdbscan_min_samples": int(theme.get("clustering_min_cluster_size", 2)) + 1,
        "hdbscan_cluster_selection_method": MONTHLY_CLUSTER_SELECTION_METHOD,
        "hdbscan_allow_single_cluster": MONTHLY_CLUSTER_ALLOW_SINGLE_CLUSTER,
        "canonicalization_min_cluster_size": theme.get(
            "canonicalization_min_cluster_size", 2
        ),
        "monthly_cluster_contract_version": MONTHLY_CLUSTER_CONTRACT_VERSION,
        "canonicalization_contract_version": CANONICALIZATION_CONTRACT_VERSION,
        "canonicalization_representation": CANONICALIZATION_REPRESENTATION,
        "canonicalization_grouping_method": CANONICALIZATION_GROUPING_METHOD,
        "canonicalization_metric": CANONICALIZATION_METRIC,
        "canonicalization_linkage": CANONICALIZATION_LINKAGE,
        "canonicalization_similarity_threshold": (
            CANONICALIZATION_SIMILARITY_THRESHOLD
        ),
        "clustering_metric": theme.get("clustering_metric", "euclidean"),
        "transition_threshold": theme.get("transition_threshold"),
        "reply_transition_threshold": theme.get("reply_transition_threshold"),
        "max_workers": theme.get("max_workers"),
    }
    return build_stage_cache_key(
        stage="theme_generation",
        semantic_version=THEME_STAGE_CACHE_VERSION,
        input_hashes=hashes,
        config_subset=config_subset,
        code_fingerprint=build_stage_code_fingerprint("theme_generation"),
    )


def topic_cache_key_fn(context: Any, parameters: dict[str, Any]) -> str:
    """Compatibility wrapper exposing the pure topic computation key."""
    input_bundle: TopicInputBundle | None = parameters.get("input_bundle")
    config: ValidatedRunConfiguration | None = parameters.get("config")
    if not input_bundle or not config:
        return ""
    return topic_stage_cache_key(input_bundle, config)


def network_cache_key_fn(context: Any, parameters: dict[str, Any]) -> str:
    """Compatibility wrapper exposing the pure network/community computation key."""
    dataset_identity: DatasetIdentity | None = parameters.get("dataset_identity")
    config: ValidatedRunConfiguration | None = parameters.get("config")
    if not dataset_identity or not config:
        return ""
    return network_stage_cache_key(dataset_identity, config)


def theme_cache_key_fn(context: Any, parameters: dict[str, Any]) -> str:
    """Compatibility wrapper exposing the pure theme/evolution computation key."""
    input_bundle: ThemeInputBundle | None = parameters.get("input_bundle")
    config: ValidatedRunConfiguration | None = parameters.get("config")
    if not input_bundle or not config:
        return ""
    return theme_stage_cache_key(input_bundle, config)
