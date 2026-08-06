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
from src.themes.sankey_paths import get_path_info, find_all_sankey_paths
from src.visualization.community_transition import draw_community_transition_diagram
from src.visualization.membership_changes import draw_members_transition_diagram
from src.themes.theme_similarity import extract_themes
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

    if render_visuals:
        logger.info("theme_visualizations_started")
        source_ind, target_ind, score, all_community = get_path_info(matched_df)
        sankey_dir = os.path.join(output_dir, "sankey")
        draw_community_transition_diagram(
            sankey_dir, source_ind, target_ind, score, all_community, matched_df
        )

        paths_detected = find_all_sankey_paths(source_ind, target_ind, all_community)
        members_dir = os.path.join(output_dir, "membership_changes")
        draw_members_transition_diagram(members_dir, paths_detected, matched_df)

        similarity_dir = os.path.join(output_dir, "theme_similarity")
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
            )
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
