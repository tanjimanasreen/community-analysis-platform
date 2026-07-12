from typing import Mapping, Any, Optional, Dict
from pathlib import Path
import os
import pandas as pd

from prefect import task

from src.orchestration.models import ValidatedRunConfiguration, DatasetIdentity, ArtifactReference, PipelineRunContext
from src.orchestration.hashing import hash_mapping, hash_file
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
    from src.config.loader import load_config

    # We call load_config which handles fallback and typing (or just raises errors on missing file)
    # However load_config takes a file path. If config is a dict, we just use it directly,
    # or validate required keys.
    if "output_dir" not in config:
        raise PipelineError("output_dir is required in configuration", ErrorCategory.INVALID_CONFIGURATION)

    output_root = config["output_dir"]

    # Hash the serializable portions of config to create a digest
    # (Avoid hashing secrets, but in our case, we just hash the dict since we don't have secrets yet)
    # Filter out empty or None values to ensure stability
    clean_config = {k: v for k, v in config.items() if v is not None}
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
        text_node_column_creator_df=raw.get('text_node_column_creator_df', 'source'),
        min_total_post=raw.get('min_total_post', 10),
        min_shared_post=raw.get('min_shared_post', 5),
        min_members=raw.get('min_members', 3),
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
