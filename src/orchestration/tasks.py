from typing import Mapping, Any, Optional, Dict
from pathlib import Path
import os
import pandas as pd

from prefect import task

from src.orchestration.models import (
    ValidatedRunConfiguration, DatasetIdentity, ArtifactReference, PipelineRunContext,
    TopicInputBundle, TopicOutputBundle, ThemeInputBundle, ThemeOutputBundle
)
from src.orchestration.hashing import hash_mapping, hash_file, topic_cache_key_fn
from src.orchestration.retry_policy import ErrorCategory, PipelineError

@task(
    name="validate-run-configuration",
    retries=0,
    persist_result=True,
)
def validate_run_configuration_task(
    config: Mapping[str, Any],
) -> ValidatedRunConfiguration:
    """
    Validates configuration and returns a normalized wrapper with a digest.
    """
    from src.config.loader import validate_run_config, normalize_month

    try:
        validate_run_config(dict(config))
    except ValueError as e:
        raise PipelineError(str(e), ErrorCategory.INVALID_CONFIGURATION) from e

    # Extract output_root (the old validate expected 'output_dir', CLI uses 'output_base_path')
    # For compatibility we check both, favoring the CLI standard output_base_path.
    output_root = config.get("output_base_path") or config.get("output_dir")
    if not output_root:
        raise PipelineError("output_base_path is required in configuration", ErrorCategory.INVALID_CONFIGURATION)

    # Normalize month to standard string name (or keep as string since it goes to paths)
    # The config requires month, we can just ensure it parses
    try:
        _ = normalize_month(config.get("month", "march"))
    except ValueError as e:
        raise PipelineError(str(e), ErrorCategory.INVALID_CONFIGURATION) from e

    # Hash the serializable portions of config to create a digest
    # (Avoid hashing secrets, but in our case, we just hash the dict since we don't have secrets yet)
    # Filter out empty or None values to ensure stability.
    # Also remove passwords/secrets if they ever appear.
    clean_config = {k: v for k, v in config.items() if v is not None and "password" not in k.lower() and "secret" not in k.lower()}
    digest = hash_mapping(clean_config)

    return ValidatedRunConfiguration(
        config_digest=digest,
        output_root=output_root,
        raw_config=clean_config
    )

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
    """
    Resolves a valid dataset identity from a physical file or DVC pointer.
    Computes SHA-256 only if a trusted known_sha256 is not provided.
    """
    if not os.path.exists(path):
        raise PipelineError(f"Input dataset not found at {path}", ErrorCategory.MISSING_REQUIRED_INPUT)

    sha256 = known_sha256
    identity_source = "supplied" if sha256 else "computed"

    if not sha256 or verify_file_hash:
        computed = hash_file(path)
        if sha256 and computed != sha256:
            raise PipelineError(
                f"Dataset hash mismatch for {path}. Expected {sha256}, got {computed}",
                ErrorCategory.INVALID_CONFIGURATION
            )
        sha256 = computed
        if verify_file_hash and known_sha256:
            identity_source = "verified"

    # Simple validation for proper sha256 shape
    if not (isinstance(sha256, str) and len(sha256) == 64 and sha256.isalnum()):
        raise PipelineError(f"Malformed SHA-256 hash: {sha256}", ErrorCategory.INVALID_CONFIGURATION)

    return DatasetIdentity(
        dataset_id=dataset_id,
        path=path,
        sha256=sha256,
        platform=platform,
        identity_source=identity_source
    )

@task(
    name="run-monthly-network-community-phase",
    retries=0,
    persist_result=True,
)
def run_monthly_network_community_phase_task(
    dataset_identity: DatasetIdentity,
    config: ValidatedRunConfiguration,
    context: PipelineRunContext
) -> list[ArtifactReference]:
    """
    Wrapper around run_network_community_pipeline that avoids loading large objects into Prefect state.
    Instead, it returns ArtifactReferences for the outputs.
    """
    from src.pipelines.social_network_pipeline import run_network_community_pipeline

    # We load the dataframe inside the task, so it never crosses the orchestration boundary.
    df = pd.read_csv(dataset_identity.path)

    # Extract config values (with defaults matching thesis)
    raw = config.raw_config

    # Run the real domain function
    # Note: run_network_community_pipeline outputs multiple CSVs into the output_dir
    # To isolate, we can place them in a run-specific subfolder in output_root
    isolated_output = os.path.join(context.output_root, context.pipeline_run_id)
    os.makedirs(isolated_output, exist_ok=True)

    run_network_community_pipeline(
        df=df,
        content_type=raw.get('content_type', 'reply'),
        data_type=raw.get('data_type', 'twitter'),
        month=raw.get('month', 'march'),
        year=raw.get('year', '2017'),
        date_column=raw.get('date_column', 'created_at'),
        creator_relation=raw.get('creator_relation', 'REPLIED_TO'),
        spreader_relation=raw.get('spreader_relation', 'REPLIED_BY'),
        creator_node_column=raw.get('creator_node_column', 'target'),
        spreader_node_column=raw.get('spreader_node_column', 'target'),
        text_node_column_creator_df=raw.get('text_node_column', 'source'),
        min_total_post=raw.get('graph_thresholds', {}).get('min_total_post', raw.get('min_total_post', 10)),
        min_shared_post=raw.get('graph_thresholds', {}).get('min_shared_post', raw.get('min_shared_post', 5)),
        min_members=raw.get('graph_thresholds', {}).get('min_members', raw.get('min_members', 3)),
        output_dir=isolated_output,
    )

    # Discover artifacts produced
    artifacts = []

    # Explicit output contract
    data_type = raw.get('data_type', 'twitter')
    content_type = raw.get('content_type', 'reply')
    month = str(raw.get('month', 'march'))
    year = str(raw.get('year', '2017'))

    expected_paths = {
        "network_data": f"{data_type}/network_data/{content_type}/{month}{year}.csv",
        "user_centrality": f"{data_type}/user_centrality/{content_type}/{month}.csv",
        "count_user_messages": f"{data_type}/count_user_messages/{content_type}/{month}.csv",
        "daily_messages_stat": f"{data_type}/daily_messages_stat/{content_type}/{month}.csv",
        "communities_matched": f"{data_type}/communities/matched/{content_type}/{month}.csv",
        "topic_manifest": f"{data_type}/_intermediate/topic_inputs/{content_type}/{month}_{year}/manifest.json",
        "topic_absolute_messages": f"{data_type}/_intermediate/topic_inputs/{content_type}/{month}_{year}/absolute_community_messages.csv",
        "topic_weighted_messages": f"{data_type}/_intermediate/topic_inputs/{content_type}/{month}_{year}/weighted_community_messages.csv",
        "topic_matched": f"{data_type}/_intermediate/topic_inputs/{content_type}/{month}_{year}/matched_communities.csv",
    }

    optional_paths = {
        "communities_absolute": f"{data_type}/communities/graphs/absolute/{content_type}/{month}.csv",
        "communities_weighted": f"{data_type}/communities/graphs/weighted/{content_type}/{month}.csv",
        "communities_partially_matched": f"{data_type}/communities/partially_matched/{content_type}/{month}.csv",
        "topic_partial_matched": f"{data_type}/_intermediate/topic_inputs/{content_type}/{month}_{year}/partial_matched_communities.csv",
    }

    for key, rel_path in expected_paths.items():
        filepath = os.path.join(isolated_output, rel_path)
        if not os.path.exists(filepath):
            raise PipelineError(f"Expected artifact not found: {filepath}", ErrorCategory.MISSING_REQUIRED_INPUT)
        artifacts.append(
            ArtifactReference(
                path=filepath,
                sha256=hash_file(filepath),
                media_type="application/json" if filepath.endswith('.json') else "text/csv",
                byte_size=os.path.getsize(filepath),
                asset_key=key
            )
        )

    for key, rel_path in optional_paths.items():
        filepath = os.path.join(isolated_output, rel_path)
        if os.path.exists(filepath):
            artifacts.append(
                ArtifactReference(
                    path=filepath,
                    sha256=hash_file(filepath),
                    media_type="application/json" if filepath.endswith('.json') else "text/csv",
                    byte_size=os.path.getsize(filepath),
                    asset_key=key
                )
            )

    return artifacts


@task(
    name="run-monthly-topic-phase",
    retries=0,
    persist_result=True,
    cache_key_fn=None,  # Deferred as per Plan 020
)
def run_monthly_topic_phase_task(
    input_bundle: TopicInputBundle,
    config: ValidatedRunConfiguration,
    context: PipelineRunContext
) -> TopicOutputBundle:
    """
    Wrapper around run_topic_phase.
    Loads input CSVs from the provided ArtifactReference bundle, executes the local LDA process, 
    and returns explicit ArtifactReferences to the isolated output paths.
    """
    from src.pipelines.social_network_pipeline import run_topic_phase

    # Extract configs
    raw = config.raw_config
    data_type = raw.get('data_type', 'twitter')
    content_type = raw.get('content_type', 'reply')
    month = str(raw.get('month', 'march'))
    year = str(raw.get('year', '2017'))

    isolated_output = os.path.join(context.output_root, context.pipeline_run_id)
    os.makedirs(isolated_output, exist_ok=True)

    # Load dataframes inside task execution
    if not os.path.exists(input_bundle.absolute_community_messages.path):
        raise PipelineError(f"Missing absolute community messages at {input_bundle.absolute_community_messages.path}", ErrorCategory.MISSING_REQUIRED_INPUT)
    abs_df = pd.read_csv(input_bundle.absolute_community_messages.path)

    if not os.path.exists(input_bundle.weighted_community_messages.path):
        raise PipelineError(f"Missing weighted community messages at {input_bundle.weighted_community_messages.path}", ErrorCategory.MISSING_REQUIRED_INPUT)
    per_df = pd.read_csv(input_bundle.weighted_community_messages.path)

    if not os.path.exists(input_bundle.matched_communities.path):
        raise PipelineError(f"Missing matched communities at {input_bundle.matched_communities.path}", ErrorCategory.MISSING_REQUIRED_INPUT)
    matched_df = pd.read_csv(input_bundle.matched_communities.path)

    partial_df = pd.DataFrame()
    if input_bundle.partial_matched_communities and os.path.exists(input_bundle.partial_matched_communities.path):
        partial_df = pd.read_csv(input_bundle.partial_matched_communities.path)

    # Run domain logic
    run_topic_phase(
        abs_community_messages=abs_df,
        per_community_messages=per_df,
        matched_df=matched_df,
        partial_matched=partial_df,
        month=month,
        year=year,
        data_type=data_type,
        content_type=content_type,
        output_dir=isolated_output
    )

    # Discover and build output references
    scores_path = os.path.join(isolated_output, data_type, "LDA", "scores", content_type, f"{month}.csv")
    if not os.path.exists(scores_path):
        raise PipelineError(f"Expected topic artifact not found: {scores_path}", ErrorCategory.MISSING_REQUIRED_INPUT)
        
    lda_scores = ArtifactReference(
        path=scores_path,
        sha256=hash_file(scores_path),
        media_type="text/csv",
        byte_size=os.path.getsize(scores_path),
        asset_key="lda_scores"
    )

    matched_topics = None
    matched_path = os.path.join(isolated_output, data_type, "LDA", "matched", content_type, f"{month}_{year}.csv")
    if os.path.exists(matched_path):
        matched_topics = ArtifactReference(
            path=matched_path,
            sha256=hash_file(matched_path),
            media_type="text/csv",
            byte_size=os.path.getsize(matched_path),
            asset_key="matched_communities_topics"
        )

    partial_matched_topics = None
    partial_path = os.path.join(isolated_output, data_type, "LDA", "partial_matched", content_type, f"{month}_{year}.csv")
    if os.path.exists(partial_path):
        partial_matched_topics = ArtifactReference(
            path=partial_path,
            sha256=hash_file(partial_path),
            media_type="text/csv",
            byte_size=os.path.getsize(partial_path),
            asset_key="partial_matched_communities_topics"
        )

    # Theme input artifacts
    theme_inputs = []
    manifest_path = os.path.join(isolated_output, data_type, "_intermediate", "theme_inputs", content_type, f"{month}_{year}", "manifest.json")
    if os.path.exists(manifest_path):
        theme_inputs.append(ArtifactReference(
            path=manifest_path,
            sha256=hash_file(manifest_path),
            media_type="application/json",
            byte_size=os.path.getsize(manifest_path),
            asset_key="theme_manifest"
        ))
        
    return TopicOutputBundle(
        lda_scores=lda_scores,
        matched_communities_topics=matched_topics,
        partial_matched_communities_topics=partial_matched_topics,
        theme_inputs=tuple(theme_inputs)
    )

@task(
    name="run-monthly-themes-phase",
    retries=0,
    persist_result=True,
    cache_key_fn=None,  # No cache yet to avoid overlapping with CachedProvider
)
def run_monthly_themes_task(
    input_bundle: ThemeInputBundle,
    config: ValidatedRunConfiguration,
    context: PipelineRunContext
) -> ThemeOutputBundle:
    """
    Wrapper around run_theme_pipeline_from_monthly_data.
    Loads topic output CSVs, executes theme provider + visualizations,
    and returns explicitly typed ArtifactReferences for the outputs.
    """
    from src.pipelines.theme_pipeline import run_theme_pipeline_from_monthly_data

    raw = config.raw_config
    content_type = raw.get('content_type', 'reply')
    # Use the first month from the inputs to determine the target year?
    # Actually the config defines the target year for the whole run.
    year = str(raw.get('year', '2017'))
    
    isolated_output = os.path.join(context.output_root, context.pipeline_run_id)
    os.makedirs(isolated_output, exist_ok=True)

    # 1. Validate inputs and load DataFrames
    monthly_data_dict = {}
    for month, artifact_ref in input_bundle.monthly_topic_outputs.items():
        if not os.path.exists(artifact_ref.path):
            raise PipelineError(
                f"Missing required theme input for {month} at {artifact_ref.path}", 
                ErrorCategory.MISSING_REQUIRED_INPUT
            )
        monthly_data_dict[month] = pd.read_csv(artifact_ref.path)

    if not monthly_data_dict:
        raise PipelineError("No monthly topic outputs provided to theme phase.", ErrorCategory.MISSING_REQUIRED_INPUT)

    # 2. Run domain logic
    # Provider is None by default; it will be constructed locally using config inside the domain function.
    run_theme_pipeline_from_monthly_data(
        monthly_data_dict=monthly_data_dict,
        year=year,
        content_type=content_type,
        output_dir=isolated_output,
        config=raw,
        provider=None,
        render_visuals=raw.get('render_visuals', True),
        similarity_model_name=raw.get('similarity_model_name', 'paraphrase-MiniLM-L6-v2')
    )

    # 3. Discover outputs and build references
    themes_artifacts = []
    for month in monthly_data_dict.keys():
        theme_path = os.path.join(isolated_output, f"{month}_{year}_with_themes.csv")
        if not os.path.exists(theme_path):
            raise PipelineError(f"Expected theme artifact not found: {theme_path}", ErrorCategory.MISSING_REQUIRED_INPUT)
        
        themes_artifacts.append(ArtifactReference(
            path=theme_path,
            sha256=hash_file(theme_path),
            media_type="text/csv",
            byte_size=os.path.getsize(theme_path),
            asset_key=f"themes_{month}"
        ))

    transition_path = os.path.join(isolated_output, "community_transition.csv")
    transition_artifact = None
    if os.path.exists(transition_path):
        transition_artifact = ArtifactReference(
            path=transition_path,
            sha256=hash_file(transition_path),
            media_type="text/csv",
            byte_size=os.path.getsize(transition_path),
            asset_key="community_transitions"
        )

    visualizations = []
    for vis_dir_name in ["sankey", "membership_changes", "theme_similarity"]:
        vis_dir = os.path.join(isolated_output, vis_dir_name)
        if os.path.exists(vis_dir) and os.path.isdir(vis_dir):
            for file in os.listdir(vis_dir):
                if file.startswith('.'):
                    continue
                file_path = os.path.join(vis_dir, file)
                if not os.path.isfile(file_path):
                    continue
                media_type = "image/png" if file.endswith(".png") else "text/html" if file.endswith(".html") else "application/octet-stream"
                visualizations.append(ArtifactReference(
                    path=file_path,
                    sha256=hash_file(file_path),
                    media_type=media_type,
                    byte_size=os.path.getsize(file_path),
                    asset_key=f"visualization_{vis_dir_name}_{file}"
                ))

    provider_run_summary_path = os.path.join(isolated_output, "provider_run_summary.json")
    import json
    with open(provider_run_summary_path, "w") as f:
        json.dump({
            "configured_primary_provider": raw.get("theme_provider", "openai"),
            "configured_primary_model": raw.get("theme_model", "gpt-4o"),
            "configured_fallback_chain": raw.get("fallback_chain", []),
            "prompt_version": raw.get("prompt_version", "v1")
        }, f)
        
    provider_run_summary = ArtifactReference(
        path=provider_run_summary_path,
        sha256=hash_file(provider_run_summary_path),
        media_type="application/json",
        byte_size=os.path.getsize(provider_run_summary_path),
        asset_key="provider_run_summary"
    )

    return ThemeOutputBundle(
        themes=tuple(themes_artifacts),
        community_transitions=transition_artifact,
        visualizations=tuple(visualizations),
        provider_run_summary=provider_run_summary
    )
