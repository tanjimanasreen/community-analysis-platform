import hashlib
import json
import logging
import os
import time

import pandas as pd

from src.providers.cached import CachedProvider
from src.providers import factory
from src.themes.theme_generation import generate_llm_themes

# Future imports from Milestone 4, 5, 6 will go here:
# from src.themes.community_transition import calculate_jaccard_transitions
# from src.themes.sankey_paths import generate_sankey
# from src.themes.heatmaps import ...

from src.themes.data_loader import load_prepare_data
from src.themes.community_transition import get_community_transition
from src.themes.sankey_paths import get_path_info
from src.visualization.community_transition import draw_community_transition_diagram
from src.visualization.membership_changes import draw_members_transition_diagram
from src.themes.theme_similarity import build_similarity_embedder, extract_themes
from src.themes.community_paths import (
    build_community_path_artifact,
    build_membership_mobility_artifact,
    build_path_theme_similarity_artifact,
    paths_as_lists,
)
from src.themes.theme_clustering import (
    DEFAULT_CLUSTERING_MODEL,
    build_clustered_theme_artifacts,
    build_clustering_embedder,
)
from src.themes.embedding_store import (
    EMBEDDING_ARTIFACT_CONTRACT_VERSION,
    EMBEDDING_DTYPE,
    EmbeddingContract,
    RecordingEmbeddingModel,
)
from src.visualization.theme_similarity import draw_theme_similarity_heatmap

logger = logging.getLogger(__name__)


def process_single_file_themes(
    df: pd.DataFrame, provider, *, max_workers: int = 6
) -> pd.DataFrame:
    frame = df.copy()
    if "absolute_community" not in frame.columns:
        frame["absolute_community"] = -1
    if "weighted_community" not in frame.columns:
        frame["weighted_community"] = -1

    return generate_llm_themes(provider, frame, max_workers=max_workers)


def run_theme_pipeline(
    input_dir: str,
    year: str,
    content_type: str,
    output_dir: str,
    config: dict | None = None,
    provider=None,
    render_visuals: bool = True,
    similarity_model_name: str = "paraphrase-MiniLM-L6-v2",
    max_theme_workers: int = 6,
    clustering_embedder=None,
):
    """
    Runs the full theme intelligence pipeline on the LDA outputs directory.
    Provider is resolved from config via the provider factory unless explicitly
    passed (e.g. in tests via provider=MockProvider(...)).
    """
    os.makedirs(output_dir, exist_ok=True)

    # Milestone 1: Data Loading
    logger.info("theme_inputs_loading input_dir=%s year=%s", input_dir, year)
    monthly_data_dict = load_prepare_data(input_dir, year)
    return run_theme_pipeline_from_monthly_data(
        monthly_data_dict=monthly_data_dict,
        year=year,
        content_type=content_type,
        output_dir=output_dir,
        config=config,
        provider=provider,
        render_visuals=render_visuals,
        similarity_model_name=similarity_model_name,
        max_theme_workers=max_theme_workers,
        clustering_embedder=clustering_embedder,
    )


def run_theme_pipeline_from_bundle(
    bundle,
    year: str,
    content_type: str,
    output_dir: str,
    config: dict | None = None,
    provider=None,
    render_visuals: bool = True,
    similarity_model_name: str = "paraphrase-MiniLM-L6-v2",
    max_theme_workers: int = 6,
    clustering_embedder=None,
):
    return run_theme_pipeline_from_monthly_data(
        monthly_data_dict=bundle.monthly_data,
        year=year,
        content_type=content_type,
        output_dir=output_dir,
        config=config,
        provider=provider,
        render_visuals=render_visuals,
        similarity_model_name=similarity_model_name,
        max_theme_workers=max_theme_workers,
        clustering_embedder=clustering_embedder,
    )


def run_theme_pipeline_from_monthly_data(
    monthly_data_dict: dict[str, pd.DataFrame],
    year: str,
    content_type: str,
    output_dir: str,
    config: dict | None = None,
    provider=None,
    render_visuals: bool = True,
    similarity_model_name: str = "paraphrase-MiniLM-L6-v2",
    max_theme_workers: int = 6,
    clustering_embedder=None,
):
    os.makedirs(output_dir, exist_ok=True)
    if not monthly_data_dict:
        logger.warning(
            "No monthly matched LDA files found; emitting empty transition output"
        )

    tracking_settings = (config or {}).get("tracking", {})
    if isinstance(tracking_settings, dict) and tracking_settings.get("enabled", False):
        from src.themes.benchmark.dataset import register_theme_prompt_to_mlflow

        register_theme_prompt_to_mlflow()

    logger.info(
        "theme_pipeline_started months=%d content_type=%s render_visuals=%s",
        len(monthly_data_dict),
        content_type,
        render_visuals,
    )
    if provider is not None:
        # Test injection — wrap in CachedProvider if not already wrapped
        if not isinstance(provider, CachedProvider):
            from src.providers.cache_backends import InMemoryThemeResponseCache

            provider = CachedProvider(provider, cache=InMemoryThemeResponseCache())
    else:
        # Production path — build provider from config (reads providers.yml via factory)
        provider = factory.build_theme_provider(config or {})

    themed_monthly_dict = {}
    for month, df in monthly_data_dict.items():
        month_started = time.perf_counter()
        logger.info("theme_month_started month=%s rows=%d", month, len(df))
        themed_df = process_single_file_themes(
            df, provider, max_workers=max_theme_workers
        )
        themed_monthly_dict[month] = themed_df
        # Save themed output
        output_path = os.path.join(output_dir, f"{month}_{year}_with_themes.parquet")
        themed_df.to_parquet(output_path, index=False)
        logger.info(
            "theme_month_completed month=%s rows=%d path=%s elapsed_seconds=%.2f",
            month,
            len(themed_df),
            output_path,
            time.perf_counter() - month_started,
        )

    theme_settings = (config or {}).get("theme", {})
    if not isinstance(theme_settings, dict):
        theme_settings = {}

    if bool(theme_settings.get("clustering_enabled", False)) and themed_monthly_dict:
        clustering_model = str(
            theme_settings.get("clustering_model", DEFAULT_CLUSTERING_MODEL)
        )
        min_cluster_size = int(theme_settings.get("clustering_min_cluster_size", 2))
        canonical_min_cluster_size = int(
            theme_settings.get("canonicalization_min_cluster_size", min_cluster_size)
        )
        clustering_metric = str(theme_settings.get("clustering_metric", "euclidean"))
        clustering_provider = (
            str(theme_settings.get("clustering_provider", "tei")).strip().lower()
        )
        raw_embedder = clustering_embedder or build_clustering_embedder(config or {})
        owns_embedder = clustering_embedder is None
        if clustering_provider == "tei":
            from src.config.settings import get_clustering_tei_client_settings

            clustering_client_settings = get_clustering_tei_client_settings()
            clustering_revision = str(
                theme_settings.get(
                    "clustering_model_revision", clustering_client_settings.revision
                )
            ).strip()
        else:
            clustering_revision = str(
                theme_settings.get("clustering_model_revision", "deterministic-mock-v1")
            ).strip()
        embedding_contract = EmbeddingContract(
            profile="theme_clustering",
            provider=clustering_provider,
            model_id=clustering_model,
            model_revision=clustering_revision,
            normalized=False,
            dimensions=384 if clustering_provider == "tei" else 17,
        )
        embedder = RecordingEmbeddingModel(raw_embedder, embedding_contract)
        try:
            source_hashes = {}
            for month in themed_monthly_dict:
                path = os.path.join(output_dir, f"{month}_{year}_with_themes.parquet")
                source_hashes[_period_for_month(month, year)] = _sha256_file(path)
            logger.info(
                "theme_clustering_started months=%d model=%s min_cluster_size=%d",
                len(themed_monthly_dict),
                clustering_model,
                min_cluster_size,
            )
            summaries, observations, families = build_clustered_theme_artifacts(
                themed_monthly_dict,
                year=year,
                embedder=embedder,
                clustering_model=clustering_model,
                min_cluster_size=min_cluster_size,
                canonicalization_min_cluster_size=canonical_min_cluster_size,
                metric=clustering_metric,
                source_artifact_hashes=source_hashes,
                embedding_provider=clustering_provider,
                embedding_model_revision=clustering_revision,
                embedding_contract_version=EMBEDDING_ARTIFACT_CONTRACT_VERSION,
                embedding_dtype=EMBEDDING_DTYPE,
            )
            cluster_root = os.path.join(output_dir, "theme_clusters")
            summary_root = os.path.join(cluster_root, "monthly")
            evidence_root = os.path.join(cluster_root, "evidence")
            os.makedirs(summary_root, exist_ok=True)
            os.makedirs(evidence_root, exist_ok=True)
            for period, frame in summaries.items():
                frame.to_parquet(
                    os.path.join(summary_root, f"{period}.parquet"), index=False
                )
            for period, frame in observations.items():
                frame.to_parquet(
                    os.path.join(evidence_root, f"{period}.parquet"), index=False
                )
            families.to_parquet(
                os.path.join(cluster_root, "canonical_families.parquet"), index=False
            )
            embedding_path = embedder.write_parquet(
                os.path.join(
                    cluster_root, "embeddings", "clustering_general_themes.parquet"
                )
            )
            logger.info(
                "theme_clustering_completed monthly_cluster_rows=%d "
                "observation_rows=%d canonical_families=%d",
                sum(len(frame) for frame in summaries.values()),
                sum(len(frame) for frame in observations.values()),
                len(families),
            )
            logger.info(
                "theme_embedding_artifact_saved rows=%d path=%s",
                embedder.record_count,
                embedding_path,
            )
        finally:
            if owns_embedder:
                embedder.close()

    threshold_key = (
        "reply_transition_threshold"
        if content_type == "reply"
        else "transition_threshold"
    )
    transition_threshold = theme_settings.get(threshold_key)
    logger.info(
        "community_transition_started threshold=%s",
        "default" if transition_threshold is None else transition_threshold,
    )
    matched_df = get_community_transition(
        themed_monthly_dict,
        content_type,
        threshold=(
            float(transition_threshold) if transition_threshold is not None else None
        ),
    )
    transitions_path = os.path.join(output_dir, "community_transition.parquet")
    matched_df.to_parquet(transitions_path, index=False)
    logger.info(
        "community_transition_completed rows=%d path=%s",
        len(matched_df),
        transitions_path,
    )

    # Persist the thesis longitudinal read model independently from report rendering.
    # Path discovery delegates to the existing Sankey DFS implementation so the
    # accepted transition graph and path semantics are unchanged.
    path_frame = build_community_path_artifact(matched_df)
    paths_path = os.path.join(output_dir, "community_paths.parquet")
    path_frame.to_parquet(paths_path, index=False)
    membership_frame = build_membership_mobility_artifact(path_frame)
    membership_path = os.path.join(output_dir, "community_path_membership.parquet")
    membership_frame.to_parquet(membership_path, index=False)
    paths_detected = paths_as_lists(path_frame)
    logger.info(
        "community_paths_completed paths=%d path_rows=%d membership_rows=%d",
        path_frame["path_id"].nunique() if not path_frame.empty else 0,
        len(path_frame),
        len(membership_frame),
    )

    evolution_similarity_enabled = bool(
        theme_settings.get("evolution_similarity_enabled", render_visuals)
    )
    if evolution_similarity_enabled:
        similarity_dir = os.path.join(output_dir, "theme_similarity")
        (
            raw_similarity_embedder,
            similarity_model_id,
            similarity_revision,
            similarity_dimensions,
        ) = build_similarity_embedder(config or {}, similarity_model_name)
        from src.config.settings import get_similarity_settings

        similarity_provider = (
            str(
                theme_settings.get(
                    "similarity_provider", get_similarity_settings().provider
                )
            )
            .strip()
            .lower()
        )
        similarity_embedder = RecordingEmbeddingModel(
            raw_similarity_embedder,
            EmbeddingContract(
                profile="theme_similarity",
                provider=similarity_provider,
                model_id=similarity_model_id,
                model_revision=similarity_revision,
                normalized=similarity_provider == "tei",
                dimensions=similarity_dimensions,
            ),
        )
        try:
            similarity_frame = build_path_theme_similarity_artifact(
                path_frame,
                model=similarity_embedder,
                model_name=similarity_model_name,
                embedding_provider=similarity_provider,
                embedding_model=similarity_model_id,
                embedding_model_revision=similarity_revision,
            )
            similarity_data_path = os.path.join(
                output_dir, "community_path_theme_similarity.parquet"
            )
            similarity_frame.to_parquet(similarity_data_path, index=False)

            if render_visuals:
                for file_name, start_column, end_column in (
                    (
                        "absolute_theme",
                        "start_month_absolute_theme",
                        "end_month_absolute_theme",
                    ),
                    (
                        "weighted_theme",
                        "start_month_weighted_theme",
                        "end_month_weighted_theme",
                    ),
                    (
                        "general_theme",
                        "start_month_general_theme",
                        "end_month_general_theme",
                    ),
                ):
                    community_themes = extract_themes(
                        matched_df, paths_detected, start_column, end_column
                    )
                    draw_theme_similarity_heatmap(
                        community_themes,
                        similarity_dir,
                        file_name,
                        model_name=similarity_model_name,
                        model=similarity_embedder,
                    )

            similarity_embedding_path = similarity_embedder.write_parquet(
                os.path.join(
                    similarity_dir,
                    "embeddings",
                    "similarity_themes.parquet",
                )
            )
            logger.info(
                "theme_similarity_artifacts_saved rows=%d embeddings=%d path=%s",
                len(similarity_frame),
                similarity_embedder.record_count,
                similarity_embedding_path,
            )
        finally:
            similarity_embedder.close()
    else:
        logger.info("theme_similarity_skipped evolution_similarity_enabled=false")

    if render_visuals:
        logger.info("theme_visualizations_started")
        source_ind, target_ind, score, all_community = get_path_info(matched_df)
        sankey_dir = os.path.join(output_dir, "sankey")
        draw_community_transition_diagram(
            sankey_dir, source_ind, target_ind, score, all_community, matched_df
        )
        members_dir = os.path.join(output_dir, "membership_changes")
        draw_members_transition_diagram(members_dir, paths_detected, matched_df)
        logger.info("theme_visualizations_completed")
    else:
        logger.info("theme_visualizations_skipped render_visuals=false")

    # Save run metrics
    if provider is not None and hasattr(provider, "run_metrics"):
        metrics_path = os.path.join(output_dir, "run_metrics.json")
        with open(metrics_path, "w", encoding="utf-8") as handle:
            json.dump(provider.run_metrics, handle, indent=2, ensure_ascii=False)
        logger.info("provider_run_metrics_saved path=%s", metrics_path)

    logger.info("theme_pipeline_completed")
    return matched_df


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _period_for_month(month: str, year: str | int) -> str:
    names = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    text = str(month).strip().lower()
    number = int(text) if text.isdigit() else names.get(text)
    if number is None or not 1 <= number <= 12:
        raise ValueError(f"unsupported theme month value: {month!r}")
    return f"{int(year):04d}-{number:02d}"
