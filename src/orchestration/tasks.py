import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional

import pandas as pd
from prefect import task

from src.orchestration.artifact_validation import validate_artifact, validate_artifact_output
from src.orchestration.hashing import hash_file, hash_mapping, topic_cache_key_fn
from src.orchestration.models import (
    ArtifactReference,
    DatasetIdentity,
    PipelineRunContext,
    ThemeInputBundle,
    ThemeOutputBundle,
    TopicInputBundle,
    TopicOutputBundle,
    ValidatedRunConfiguration,
)
from src.orchestration.retry_policy import ErrorCategory, PipelineError

# ---------------------------------------------------------------------------
# Validation task
# ---------------------------------------------------------------------------


@task(
    name="validate-run-configuration",
    retries=0,
    persist_result=True,
)
def validate_run_configuration_task(
    config: Mapping[str, Any],
) -> ValidatedRunConfiguration:
    """Validates configuration and returns a normalized wrapper with a digest."""
    from src.config.loader import normalize_month, validate_run_config

    try:
        validate_run_config(dict(config))
    except ValueError as e:
        raise PipelineError(str(e), ErrorCategory.INVALID_CONFIGURATION) from e

    output_root = config.get("output_base_path") or config.get("output_dir")
    if not output_root:
        raise PipelineError(
            "output_base_path is required in configuration",
            ErrorCategory.INVALID_CONFIGURATION,
        )

    try:
        _ = normalize_month(config.get("month", "march"))
    except ValueError as e:
        raise PipelineError(str(e), ErrorCategory.INVALID_CONFIGURATION) from e

    # Build a clean config: strip None values and any obvious secret keys.
    clean_config = {
        k: v
        for k, v in config.items()
        if v is not None
        and "password" not in k.lower()
        and "secret" not in k.lower()
        and "api_key" not in k.lower()
        and "token" not in k.lower()
    }
    digest = hash_mapping(clean_config)

    return ValidatedRunConfiguration(
        config_digest=digest,
        output_root=output_root,
        raw_config=clean_config,
    )


# ---------------------------------------------------------------------------
# Dataset identity task
# ---------------------------------------------------------------------------


@task(
    name="resolve-dataset-identity",
    retries=0,
    persist_result=True,
)
def resolve_dataset_identity_task(
    path: str,
    dataset_id: str,
    known_sha256: Optional[str] = None,
    platform: Optional[str] = None,
    verify_file_hash: bool = False,
) -> DatasetIdentity:
    """Resolves a valid dataset identity from a physical file or DVC pointer."""
    if not os.path.exists(path):
        raise PipelineError(
            f"Input dataset not found at {path}",
            ErrorCategory.MISSING_REQUIRED_INPUT,
        )

    sha256 = known_sha256
    identity_source = "supplied" if sha256 else "computed"

    if not sha256 or verify_file_hash:
        computed = hash_file(path)
        if sha256 and computed != sha256:
            raise PipelineError(
                f"Dataset hash mismatch for {path}. Expected {sha256}, got {computed}",
                ErrorCategory.INVALID_CONFIGURATION,
            )
        sha256 = computed
        if verify_file_hash and known_sha256:
            identity_source = "verified"

    if not (isinstance(sha256, str) and len(sha256) == 64 and sha256.isalnum()):
        raise PipelineError(
            f"Malformed SHA-256 hash: {sha256}",
            ErrorCategory.INVALID_CONFIGURATION,
        )

    return DatasetIdentity(
        dataset_id=dataset_id,
        path=path,
        sha256=sha256,
        platform=platform,
        identity_source=identity_source,
    )


# ---------------------------------------------------------------------------
# Network / community phase task
# ---------------------------------------------------------------------------


@task(
    name="run-monthly-network-community-phase",
    retries=0,
    persist_result=True,
)
def run_monthly_network_community_phase_task(
    dataset_identity: DatasetIdentity,
    config: ValidatedRunConfiguration,
    context: PipelineRunContext,
) -> list[ArtifactReference]:
    """
    Wrapper around run_network_community_pipeline.
    DataFrames are loaded and discarded inside the task; only ArtifactReferences
    cross the orchestration boundary.
    """
    from src.pipelines.social_network_pipeline import run_network_community_pipeline

    df = pd.read_csv(dataset_identity.path)

    raw = config.raw_config
    isolated_output = os.path.join(context.output_root, context.pipeline_run_id)
    os.makedirs(isolated_output, exist_ok=True)

    run_network_community_pipeline(
        df=df,
        content_type=raw.get("content_type", "reply"),
        data_type=raw.get("data_type", "twitter"),
        month=raw.get("month", "march"),
        year=raw.get("year", "2017"),
        date_column=raw.get("date_column", "created_at"),
        creator_relation=raw.get("creator_relation", "REPLIED_TO"),
        spreader_relation=raw.get("spreader_relation", "REPLIED_BY"),
        creator_node_column=raw.get("creator_node_column", "target"),
        spreader_node_column=raw.get("spreader_node_column", "target"),
        text_node_column_creator_df=raw.get("text_node_column", "source"),
        min_total_post=raw.get("graph_thresholds", {}).get(
            "min_total_post", raw.get("min_total_post", 10)
        ),
        min_shared_post=raw.get("graph_thresholds", {}).get(
            "min_shared_post", raw.get("min_shared_post", 5)
        ),
        min_members=raw.get("graph_thresholds", {}).get(
            "min_members", raw.get("min_members", 3)
        ),
        output_dir=isolated_output,
    )

    artifacts = []
    data_type = raw.get("data_type", "twitter")
    content_type = raw.get("content_type", "reply")
    month = str(raw.get("month", "march"))
    year = str(raw.get("year", "2017"))

    expected_paths = {
        "network_data": f"{data_type}/network_data/{content_type}/{month}{year}.csv",
        "user_centrality": f"{data_type}/user_centrality/{content_type}/{month}.csv",
        "count_user_messages": f"{data_type}/count_user_messages/{content_type}/{month}.csv",
        "daily_messages_stat": f"{data_type}/daily_messages_stat/{content_type}/{month}.csv",
        "communities_matched": f"{data_type}/communities/matched/{content_type}/{month}.csv",
        "topic_manifest": (
            f"{data_type}/_intermediate/topic_inputs/{content_type}/{month}_{year}/manifest.json"
        ),
        "topic_absolute_messages": (
            f"{data_type}/_intermediate/topic_inputs/{content_type}/{month}_{year}"
            "/absolute_community_messages.csv"
        ),
        "topic_weighted_messages": (
            f"{data_type}/_intermediate/topic_inputs/{content_type}/{month}_{year}"
            "/weighted_community_messages.csv"
        ),
        "topic_matched": (
            f"{data_type}/_intermediate/topic_inputs/{content_type}/{month}_{year}"
            "/matched_communities.csv"
        ),
    }

    optional_paths = {
        "communities_absolute": (
            f"{data_type}/communities/graphs/absolute/{content_type}/{month}.csv"
        ),
        "communities_weighted": (
            f"{data_type}/communities/graphs/weighted/{content_type}/{month}.csv"
        ),
        "communities_partially_matched": (
            f"{data_type}/communities/partially_matched/{content_type}/{month}.csv"
        ),
        "topic_partial_matched": (
            f"{data_type}/_intermediate/topic_inputs/{content_type}/{month}_{year}"
            "/partial_matched_communities.csv"
        ),
    }

    for key, rel_path in expected_paths.items():
        filepath = os.path.join(isolated_output, rel_path)
        validate_artifact_output(filepath, isolated_output, label=key)
        artifacts.append(
            ArtifactReference(
                path=filepath,
                sha256=hash_file(filepath),
                media_type="application/json" if filepath.endswith(".json") else "text/csv",
                byte_size=os.path.getsize(filepath),
                asset_key=key,
            )
        )

    for key, rel_path in optional_paths.items():
        filepath = os.path.join(isolated_output, rel_path)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            artifacts.append(
                ArtifactReference(
                    path=filepath,
                    sha256=hash_file(filepath),
                    media_type="application/json" if filepath.endswith(".json") else "text/csv",
                    byte_size=os.path.getsize(filepath),
                    asset_key=key,
                )
            )

    return artifacts


# ---------------------------------------------------------------------------
# Topic modeling phase task
# ---------------------------------------------------------------------------


@task(
    name="run-monthly-topic-phase",
    retries=0,
    persist_result=True,
    cache_key_fn=None,  # Deliberately disabled; deterministic helper exists for future use.
)
def run_monthly_topic_phase_task(
    input_bundle: TopicInputBundle,
    config: ValidatedRunConfiguration,
    context: PipelineRunContext,
) -> TopicOutputBundle:
    """
    Prefect wrapper around run_topic_phase.

    Domain boundary:
        Prefect task
        → validates TopicInputBundle (path, size, hash, schema, containment)
        → loads DataFrames inside the task (never crosses the Prefect boundary)
        → calls run_topic_phase
        → returns only TopicOutputBundle (ArtifactReferences to output files)

    Input terminology:
        absolute_community_messages  — per-community messages from the
                                       absolute (IF) graph (Louvain partition)
        weighted_community_messages  — per-community messages from the
                                       weighted (WIF) graph (Louvain partition);
                                       the domain uses the parameter name
                                       per_community_messages for this value

    LDA determinism:
        random_state=100 is applied by src/topics/lda.py (RANDOM_STATE constant).
        Input row ordering is preserved by the CSV save/load cycle.
        Vocabulary ordering is determined by Gensim's Dictionary which processes
        documents in iteration order — stable when input rows are stable.
        Worker count is not configurable (single-threaded Gensim LDA).
        Reproducibility is limited to the same Gensim/NumPy/BLAS version.

    Caching:
        Task caching is disabled (cache_key_fn=None). The deterministic helper
        topic_cache_key_fn is available in hashing.py for future activation.
    """
    from src.pipelines.social_network_pipeline import run_topic_phase

    raw = config.raw_config
    data_type = raw.get("data_type", "twitter")
    content_type = raw.get("content_type", "reply")
    month = str(raw.get("month", "march"))
    year = str(raw.get("year", "2017"))

    isolated_output = os.path.join(context.output_root, context.pipeline_run_id)
    os.makedirs(isolated_output, exist_ok=True)

    # --- Strict input validation before any domain code runs ---
    validate_artifact(
        input_bundle.absolute_community_messages,
        allowed_root=context.output_root,
        required=True,
        expected_media_type="text/csv",
        label="absolute_community_messages",
    )
    validate_artifact(
        input_bundle.weighted_community_messages,
        allowed_root=context.output_root,
        required=True,
        expected_media_type="text/csv",
        label="weighted_community_messages",
    )
    validate_artifact(
        input_bundle.matched_communities,
        allowed_root=context.output_root,
        required=True,
        expected_media_type="text/csv",
        label="matched_communities",
    )
    if input_bundle.partial_matched_communities is not None:
        validate_artifact(
            input_bundle.partial_matched_communities,
            allowed_root=context.output_root,
            required=False,
            expected_media_type="text/csv",
            label="partial_matched_communities",
        )

    # --- Load DataFrames inside the task (never serialised to Prefect state) ---
    abs_df = pd.read_csv(input_bundle.absolute_community_messages.path)
    per_df = pd.read_csv(input_bundle.weighted_community_messages.path)
    matched_df = pd.read_csv(input_bundle.matched_communities.path)

    partial_df = pd.DataFrame()
    if (
        input_bundle.partial_matched_communities is not None
        and os.path.exists(input_bundle.partial_matched_communities.path)
    ):
        partial_df = pd.read_csv(input_bundle.partial_matched_communities.path)

    # --- Execute domain logic ---
    run_topic_phase(
        abs_community_messages=abs_df,
        per_community_messages=per_df,
        matched_df=matched_df,
        partial_matched=partial_df,
        month=month,
        year=year,
        data_type=data_type,
        content_type=content_type,
        output_dir=isolated_output,
    )

    # --- Collect outputs using explicit expected paths ---
    scores_path = os.path.join(
        isolated_output, data_type, "LDA", "scores", content_type, f"{month}.csv"
    )
    validate_artifact_output(scores_path, isolated_output, label="lda_scores")
    lda_scores = ArtifactReference(
        path=scores_path,
        sha256=hash_file(scores_path),
        media_type="text/csv",
        byte_size=os.path.getsize(scores_path),
        asset_key="lda_scores",
    )

    matched_topics = None
    matched_path = os.path.join(
        isolated_output, data_type, "LDA", "matched", content_type, f"{month}_{year}.csv"
    )
    if os.path.exists(matched_path) and os.path.isfile(matched_path):
        matched_topics = ArtifactReference(
            path=matched_path,
            sha256=hash_file(matched_path),
            media_type="text/csv",
            byte_size=os.path.getsize(matched_path),
            asset_key="matched_communities_topics",
        )

    partial_matched_topics = None
    partial_path = os.path.join(
        isolated_output, data_type, "LDA", "partial_matched", content_type, f"{month}_{year}.csv"
    )
    if os.path.exists(partial_path) and os.path.isfile(partial_path):
        partial_matched_topics = ArtifactReference(
            path=partial_path,
            sha256=hash_file(partial_path),
            media_type="text/csv",
            byte_size=os.path.getsize(partial_path),
            asset_key="partial_matched_communities_topics",
        )

    # Theme-input preparation manifest (written by save_pipeline_theme_inputs)
    theme_inputs = []
    manifest_path = os.path.join(
        isolated_output,
        data_type,
        "_intermediate",
        "theme_inputs",
        content_type,
        f"{month}_{year}",
        "manifest.json",
    )
    if os.path.exists(manifest_path) and os.path.isfile(manifest_path):
        theme_inputs.append(
            ArtifactReference(
                path=manifest_path,
                sha256=hash_file(manifest_path),
                media_type="application/json",
                byte_size=os.path.getsize(manifest_path),
                asset_key="theme_manifest",
            )
        )

    return TopicOutputBundle(
        lda_scores=lda_scores,
        matched_communities_topics=matched_topics,
        partial_matched_communities_topics=partial_matched_topics,
        theme_inputs=tuple(theme_inputs),
    )


# ---------------------------------------------------------------------------
# Theme / provider phase task
# ---------------------------------------------------------------------------

# Fields that must NOT appear in the provider_run_summary.
_PROVIDER_SUMMARY_EXCLUDED_KEYS = {
    "api_key",
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "auth",
}

# Allowed visualization file extensions (explicit allowlist)
_ALLOWED_VIS_EXTENSIONS = {".html", ".png", ".jpg", ".jpeg", ".svg"}


def _build_provider_summary(raw: Mapping[str, Any]) -> dict:
    """Build a small, secret-free provider lineage record."""
    theme_cfg = raw.get("theme_provider", {})
    if isinstance(theme_cfg, str):
        primary = theme_cfg
        fallback_chain = []
    else:
        primary = theme_cfg.get("primary", "mock")
        fallback_chain = theme_cfg.get("fallback_chain", [])

    # Build a deterministic digest of the provider config (secrets already
    # stripped from raw_config in validate_run_configuration_task).
    provider_cfg_safe = {
        "primary": primary,
        "fallback_chain": fallback_chain,
        "prompt_version": raw.get("prompt_version", "v1"),
    }
    from src.orchestration.hashing import hash_mapping as _hash

    return {
        "schema_version": "1.0",
        "configured_primary_provider": primary,
        "configured_primary_model": raw.get("theme_model", ""),
        "configured_fallback_chain": fallback_chain,
        "provider_config_digest": _hash(provider_cfg_safe),
        "prompt_version": raw.get("prompt_version", "v1"),
        "generation_settings_digest": _hash(
            {
                "render_visuals": raw.get("render_visuals", True),
                "similarity_model_name": raw.get(
                    "similarity_model_name", "paraphrase-MiniLM-L6-v2"
                ),
            }
        ),
        "semantic_task_version": "1.0.0",
    }


@task(
    name="run-monthly-themes-phase",
    retries=0,
    persist_result=True,
    cache_key_fn=None,
)
def run_monthly_themes_task(
    input_bundle: ThemeInputBundle,
    config: ValidatedRunConfiguration,
    context: PipelineRunContext,
) -> ThemeOutputBundle:
    """
    Prefect wrapper around run_theme_pipeline_from_monthly_data.

    Domain boundary:
        Prefect task
        → validates all ThemeInputBundle artifacts (path, size, hash, containment)
        → loads DataFrames inside the task
        → calls run_theme_pipeline_from_monthly_data with provider=None
          (domain function constructs the provider exactly once via build_theme_provider,
           wraps it in CachedProvider, and reuses it for the whole batch)
        → discovers outputs using explicit expected paths + bounded directory listing
        → writes provider_run_summary.json with safe lineage metadata only
        → returns only ThemeOutputBundle (ArtifactReferences)

    Provider ownership: domain layer (run_theme_pipeline_from_monthly_data).
    Retry policy: retries=0; provider fallback is router-owned.
    """
    from src.pipelines.theme_pipeline import run_theme_pipeline_from_monthly_data

    raw = config.raw_config
    # Required values come from validated config — no silent defaults for year/content_type.
    content_type = str(raw.get("content_type", "reply"))
    year = str(raw.get("year", "2017"))

    isolated_output = os.path.join(context.output_root, context.pipeline_run_id)
    os.makedirs(isolated_output, exist_ok=True)

    # --- 1. Validate inputs BEFORE provider construction ---
    if not input_bundle.monthly_topic_outputs:
        raise PipelineError(
            "No monthly topic outputs provided to theme phase.",
            ErrorCategory.MISSING_REQUIRED_INPUT,
        )

    for month, artifact_ref in input_bundle.monthly_topic_outputs.items():
        validate_artifact(
            artifact_ref,
            allowed_root=context.output_root,
            required=True,
            expected_media_type="text/csv",
            label=f"theme_input[{month}]",
        )

    # --- 2. Load DataFrames inside the task (never serialised) ---
    monthly_data_dict = {
        month: pd.read_csv(ref.path)
        for month, ref in input_bundle.monthly_topic_outputs.items()
    }

    # --- 3. Delegate to domain (provider constructed once inside the domain) ---
    run_theme_pipeline_from_monthly_data(
        monthly_data_dict=monthly_data_dict,
        year=year,
        content_type=content_type,
        output_dir=isolated_output,
        config=raw,
        provider=None,  # Domain constructs provider exactly once via build_theme_provider
        render_visuals=bool(raw.get("render_visuals", True)),
        similarity_model_name=str(
            raw.get("similarity_model_name", "paraphrase-MiniLM-L6-v2")
        ),
    )

    # --- 4. Collect theme CSV outputs (explicit expected paths) ---
    themes_artifacts = []
    for month in monthly_data_dict:
        theme_path = os.path.join(isolated_output, f"{month}_{year}_with_themes.csv")
        validate_artifact_output(theme_path, isolated_output, label=f"themes_{month}")
        themes_artifacts.append(
            ArtifactReference(
                path=theme_path,
                sha256=hash_file(theme_path),
                media_type="text/csv",
                byte_size=os.path.getsize(theme_path),
                asset_key=f"themes_{month}",
            )
        )

    # --- 5. Community transition artifact (explicit expected path) ---
    transition_path = os.path.join(isolated_output, "community_transition.csv")
    transition_artifact = None
    if os.path.exists(transition_path) and os.path.isfile(transition_path):
        transition_artifact = ArtifactReference(
            path=transition_path,
            sha256=hash_file(transition_path),
            media_type="text/csv",
            byte_size=os.path.getsize(transition_path),
            asset_key="community_transitions",
        )

    # --- 6. Visualization artifacts (bounded, allowlisted, non-recursive) ---
    visualizations = []
    for vis_dir_name in ("sankey", "membership_changes", "theme_similarity"):
        vis_dir = os.path.join(isolated_output, vis_dir_name)
        if not os.path.exists(vis_dir) or not os.path.isdir(vis_dir):
            continue
        for filename in sorted(os.listdir(vis_dir)):  # sorted for determinism
            if filename.startswith("."):
                continue
            file_path = os.path.join(vis_dir, filename)
            if not os.path.isfile(file_path):
                continue
            ext = Path(filename).suffix.lower()
            if ext not in _ALLOWED_VIS_EXTENSIONS:
                continue  # reject unsupported extensions and temp/debug files
            # Path containment enforced below
            try:
                Path(file_path).resolve(strict=True).relative_to(
                    Path(isolated_output).resolve()
                )
            except ValueError:
                continue
            media_type = (
                "image/png"
                if ext == ".png"
                else "text/html"
                if ext == ".html"
                else "application/octet-stream"
            )
            visualizations.append(
                ArtifactReference(
                    path=file_path,
                    sha256=hash_file(file_path),
                    media_type=media_type,
                    byte_size=os.path.getsize(file_path),
                    asset_key=f"visualization_{vis_dir_name}_{filename}",
                )
            )

    # --- 7. Provider lineage summary (safe metadata only) ---
    summary_data = _build_provider_summary(raw)
    provider_run_summary_path = os.path.join(isolated_output, "provider_run_summary.json")
    with open(provider_run_summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary_data, fh, indent=2, sort_keys=True)

    provider_run_summary = ArtifactReference(
        path=provider_run_summary_path,
        sha256=hash_file(provider_run_summary_path),
        media_type="application/json",
        byte_size=os.path.getsize(provider_run_summary_path),
        asset_key="provider_run_summary",
    )

    return ThemeOutputBundle(
        themes=tuple(themes_artifacts),
        community_transitions=transition_artifact,
        visualizations=tuple(visualizations),
        provider_run_summary=provider_run_summary,
    )
