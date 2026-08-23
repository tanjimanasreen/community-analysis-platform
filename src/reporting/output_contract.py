from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from src.ingestion.schema import (
    canonical_raw_to_derived_mapping,
    validate_canonical_raw_mapping,
)
from src.themes.theme_inputs import ThemeInputError, load_theme_inputs
from src.topics.topic_inputs import TopicInputError, load_topic_inputs

NETWORK_DATA_BASE_COLUMNS = ["unique_id", "from_id", "forwarder_id", "text"]
NETWORK_DATA_COLUMNS = [*NETWORK_DATA_BASE_COLUMNS, "created_at"]
COMMUNITY_GRAPH_COLUMNS = [
    "source",
    "target",
    "community_number",
    "direction",
    "weight",
]
COMMUNITY_NODE_INDEX_COLUMNS = ["node_id"]
COMMUNITY_SUMMARY_COLUMNS = [
    "community_id",
    "node_count",
    "edge_count",
    "total_weight",
]
COMMUNITY_INTERACTION_COLUMNS = [
    "source_community_id",
    "target_community_id",
    "user_pair_count",
    "interaction_count",
    "total_weight",
    "source_user_count",
    "target_user_count",
]
MATCHED_COMMUNITY_NODE_INDEX_COLUMNS = ["node_id"]
MATCHED_COMMUNITY_SUMMARY_COLUMNS = [
    "month",
    "total_matched",
    "total_absolute",
    "total_weighted",
]
PARTIAL_MATCHED_COMMUNITY_COLUMNS = ["month", "absolute", "weighted", "jaccard_score"]
USER_CENTRALITY_COLUMNS = ["month", "absolute", "weighted"]
COUNT_USER_MESSAGES_COLUMNS = ["month", "user", "messages"]
DAILY_MESSAGES_STAT_COLUMNS = ["month", "absolute", "weighted"]
LDA_SCORES_COLUMNS = [
    "month",
    "unigram_absolute",
    "unigram_weighted",
    "bigram_absolute",
    "bigram_weighted",
]
TRANSLATION_PROVENANCE_COLUMNS = [
    "source_hash",
    "original_text",
    "detected_language",
    "language_confidence",
    "target_language",
    "translated_text_en",
    "translation_applied",
    "provider",
    "translation_contract_version",
    "cache_hit",
    "status",
    "created_at",
]
MATCHED_LDA_COLUMNS = [
    "absolute_community",
    "absolute_unigram_topic",
    "absolute_unigram_keywords",
    "weighted_community",
    "weighted_unigram_topic",
    "weighted_unigram_keywords",
    "absolute_bigram_topic",
    "absolute_bigram_keywords",
    "weighted_bigram_topic",
    "weighted_bigram_keywords",
    "members",
]
PARTIAL_MATCHED_LDA_COLUMNS = [c for c in MATCHED_LDA_COLUMNS if c != "members"] + [
    "absolute_members",
    "weighted_members",
    "jaccard_score",
    "common_members",
    "uncommon_members",
]
THEMED_OUTPUT_COLUMNS = MATCHED_LDA_COLUMNS + [
    "all_keywords",
    "absolute_keywords",
    "weighted_keywords",
    "general_theme_gpt",
    "general_theme_names",
    "absolute_theme_gpt",
    "absolute_theme_names",
    "weighted_theme_gpt",
    "weighted_theme_names",
]

COMMUNITY_PATH_COLUMNS = [
    "path_id",
    "display_order",
    "step_index",
    "month",
    "community_key",
    "community_id",
    "member_count",
    "members",
    "previous_month",
    "previous_community_key",
    "previous_community_id",
    "jaccard_from_previous",
    "retained_count",
    "absolute_theme",
    "weighted_theme",
    "general_theme",
]
COMMUNITY_PATH_MEMBERSHIP_COLUMNS = [
    "path_id",
    "display_order",
    "step_index",
    "month",
    "community_key",
    "community_id",
    "member_count",
    "size_delta",
    "existing_count",
    "new_count",
    "lost_count",
    "reappearing_count",
    "members",
    "existing_members",
    "new_members",
    "lost_members",
    "reappearing_members",
]
THEME_GENERATION_PROVENANCE_COLUMNS = [
    "year",
    "month",
    "source_row_index",
    "keyword_kind",
    "absolute_community",
    "weighted_community",
    "provider_keywords",
    "keyword_count",
    "input_hash",
    "prompt_hash",
    "prompt_contract_version",
    "output_schema_version",
    "status",
    "failure_category",
    "failure_stage",
    "configured_provider",
    "configured_model",
    "content_filter_summary",
]
COMMUNITY_PATH_THEME_SIMILARITY_COLUMNS = [
    "path_id",
    "display_order",
    "theme_type",
    "left_step_index",
    "right_step_index",
    "left_month",
    "right_month",
    "left_community_key",
    "right_community_key",
    "left_theme",
    "right_theme",
    "cosine_similarity",
    "embedding_provider",
    "embedding_model",
    "embedding_model_revision",
]
THEME_CLUSTER_SUMMARY_COLUMNS = [
    "period",
    "canonical_theme_id",
    "canonical_theme_label",
    "monthly_cluster_ids",
    "monthly_representative_themes",
    "source_general_theme_labels",
    "community_count",
    "total_themed_community_pairs",
    "percentage",
    "prominent_keywords",
    "community_pairs",
    "mean_membership_probability",
    "source_observation_count",
    "cluster_observation_count",
    "monthly_cluster_count",
    "excluded_records_missing_general_theme",
    "excluded_records_ambiguous_general_theme_serialization",
    "monthly_noise_observation_count",
    "embedding_provider",
    "embedding_model",
    "embedding_model_revision",
    "embedding_contract_version",
    "embedding_dtype",
    "embedding_normalized",
    "hdbscan_implementation",
    "hdbscan_version",
    "clustering_min_cluster_size",
    "canonicalization_min_cluster_size",
    "clustering_metric",
    "canonicalization_representation",
    "canonicalization_grouping_method",
    "canonicalization_implementation",
    "canonicalization_metric",
    "canonicalization_linkage",
    "canonicalization_similarity_threshold",
    "canonicalization_distance_threshold",
    "monthly_cluster_contract_version",
    "canonicalization_contract_version",
    "source_artifact_sha256",
]
THEME_CLUSTER_OBSERVATION_COLUMNS = [
    "period",
    "absolute_community",
    "weighted_community",
    "pair_key",
    "source_general_theme_label",
    "general_keywords",
    "source_index",
    "hdbscan_label",
    "membership_probability",
    "is_monthly_noise",
    "monthly_cluster_id",
    "monthly_representative_theme",
    "canonical_theme_id",
    "canonical_theme_label",
    "embedding_provider",
    "embedding_model",
    "embedding_model_revision",
    "embedding_contract_version",
    "embedding_dtype",
    "embedding_normalized",
    "hdbscan_implementation",
    "hdbscan_version",
    "clustering_min_cluster_size",
    "canonicalization_min_cluster_size",
    "clustering_metric",
    "canonicalization_representation",
    "canonicalization_grouping_method",
    "canonicalization_implementation",
    "canonicalization_metric",
    "canonicalization_linkage",
    "canonicalization_similarity_threshold",
    "canonicalization_distance_threshold",
    "source_artifact_sha256",
    "monthly_cluster_contract_version",
    "canonicalization_contract_version",
]
THEME_EMBEDDING_COLUMNS = [
    "embedding_key",
    "text",
    "text_sha256",
    "profile",
    "provider",
    "model_id",
    "model_revision",
    "normalized",
    "preprocessing_version",
    "embedding_contract_version",
    "dimensions",
    "dtype",
    "embedding_sha256",
    "embedding",
]
THEME_CANONICAL_FAMILY_COLUMNS = [
    "canonical_theme_id",
    "canonical_theme_label",
    "monthly_cluster_ids",
    "monthly_representatives",
    "periods",
    "months_present",
    "stage_b_cluster_label",
    "stage_b_hdbscan_label",
    "singleton_canonical_theme",
    "embedding_provider",
    "embedding_model",
    "embedding_model_revision",
    "embedding_contract_version",
    "embedding_dtype",
    "embedding_normalized",
    "hdbscan_implementation",
    "hdbscan_version",
    "clustering_min_cluster_size",
    "canonicalization_min_cluster_size",
    "clustering_metric",
    "canonicalization_representation",
    "canonicalization_grouping_method",
    "canonicalization_implementation",
    "canonicalization_metric",
    "canonicalization_linkage",
    "canonicalization_similarity_threshold",
    "canonicalization_distance_threshold",
    "source_artifact_sha256s",
    "monthly_cluster_contract_version",
    "canonicalization_contract_version",
]

COMMUNITY_TRANSITION_COLUMNS = [
    "start_month",
    "end_month",
    "start_month_community",
    "end_month_community",
    "jaccard_score",
    "common_members",
    "uncommon_members",
    "start_month_members",
    "total_start_month_members",
    "end_month_members",
    "total_end_month_members",
    "start_month_absolute_theme",
    "end_month_absolute_theme",
    "start_month_weighted_theme",
    "end_month_weighted_theme",
    "start_month_general_theme",
    "end_month_general_theme",
]


class OutputContractError(ValueError):
    """Raised when generated artifacts do not match the Parquet output contract."""


@dataclass(frozen=True)
class ArtifactCheck:
    name: str
    path: Path
    required_columns: list[str] | None = None
    required: bool = True
    non_empty: bool = False


@dataclass(frozen=True)
class VerificationResult:
    checked: list[Path]
    skipped_optional: list[Path]

    @property
    def checked_count(self) -> int:
        return len(self.checked)


def verify_output_contract(
    config: Mapping, *, longitudinal: bool = False
) -> VerificationResult:
    """Validate generated artifacts without running any pipeline stage."""
    params = get_output_contract_params(config)
    months = get_output_contract_months(config, longitudinal=longitudinal)
    checks = get_public_artifact_checks(config, longitudinal=longitudinal)
    checked: list[Path] = []
    skipped_optional: list[Path] = []

    for check in checks:
        if not check.path.exists() and not check.required:
            skipped_optional.append(check.path)
            continue
        _validate_artifact(check)
        checked.append(check.path)

    run_dir_str = str(_get_latest_run_dir(Path(params["output_base_path"])))
    try:
        for month in months:
            load_topic_inputs(
                output_base_path=run_dir_str,
                data_type=params["data_type"],
                content_type=params["content_type"],
                month=month,
                year=params["year"],
            )

        theme_bundle = load_theme_inputs(
            output_base_path=run_dir_str,
            data_type=params["data_type"],
            content_type=params["content_type"],
            year=params["year"],
        )
    except (TopicInputError, ThemeInputError) as exc:
        raise OutputContractError(str(exc)) from exc
    missing_months = [
        month for month in months if month not in theme_bundle.monthly_data
    ]
    if missing_months:
        raise OutputContractError(
            f"Theme input manifest is missing months: {missing_months}"
        )

    for month in months:
        public_lda = (
            _base(params)
            / "LDA"
            / "matched"
            / params["content_type"]
            / f"{month}_{params['year']}.parquet"
        )
        internal_lda = (
            _base(params)
            / "_intermediate"
            / "theme_inputs"
            / params["content_type"]
            / params["year"]
            / f"{month}_{params['year']}.parquet"
        )
        _assert_same_columns(public_lda, internal_lda)
        checked.append(internal_lda)

    return VerificationResult(checked=checked, skipped_optional=skipped_optional)


def build_contract_summary(result: VerificationResult | None) -> list[str]:
    if result is None:
        return ["Contract verification was not run."]
    lines = [f"Checked artifacts: {result.checked_count}"]
    if result.skipped_optional:
        lines.append(f"Skipped optional artifacts: {len(result.skipped_optional)}")
    return lines


def get_output_contract_params(config: Mapping) -> dict[str, str]:
    """Return normalized string parameters used by artifact path builders."""
    return {
        "output_base_path": str(config.get("output_base_path", "results/")),
        "data_type": str(config.get("data_type", "twitter")),
        "content_type": str(config.get("content_type", "reply")),
        "month": str(config.get("month", "03")),
        "year": str(config.get("year", "2017")),
        "theme_output_dir": str(
            _theme_config(config).get("output_dir")
            or _get_latest_run_dir(Path(config.get("output_base_path", "results/")))
            / str(config.get("data_type", "twitter"))
            / "theme_analysis"
            / str(config.get("content_type", "reply"))
        ),
    }


def get_output_contract_months(
    config: Mapping, *, longitudinal: bool = False
) -> list[str]:
    """Return the configured month or manifest months for a longitudinal run."""
    params = get_output_contract_params(config)
    return _months(config, params["month"], longitudinal)


def get_public_artifact_checks(
    config: Mapping, *, longitudinal: bool = False
) -> list[ArtifactCheck]:
    """Return public artifact checks for a run without reading any artifacts."""
    params = get_output_contract_params(config)
    months = get_output_contract_months(config, longitudinal=longitudinal)
    theme = _theme_config(config)
    evolution_similarity_enabled = bool(
        theme.get("evolution_similarity_enabled", theme.get("render_visuals", False))
    )
    return _public_artifact_checks(
        params,
        months,
        network_data_columns=get_network_data_required_columns(config),
        evolution_similarity_enabled=evolution_similarity_enabled,
    )


def get_network_data_required_columns(
    config: Mapping | None = None,
) -> list[str]:
    """Return the normalized network schema for the configured dataset mapping."""
    if config is None:
        return list(NETWORK_DATA_COLUMNS)

    validate_canonical_raw_mapping(config)
    mapping = canonical_raw_to_derived_mapping(config)
    if mapping is not None:
        date_column = mapping.date_field
    else:
        date_column = (
            str(config.get("date_column", "created_at")).strip() or "created_at"
        )
    return [*NETWORK_DATA_BASE_COLUMNS, date_column]


def get_required_columns_by_artifact(
    config: Mapping | None = None,
) -> dict[str, list[str]]:
    """Expose generated Parquet schemas for readers and API metadata."""
    return {
        "network_data": get_network_data_required_columns(config),
        "absolute_community_graph": COMMUNITY_GRAPH_COLUMNS,
        "weighted_community_graph": COMMUNITY_GRAPH_COLUMNS,
        "community_summary": COMMUNITY_SUMMARY_COLUMNS,
        "community_node_index": COMMUNITY_NODE_INDEX_COLUMNS,
        "community_interactions": COMMUNITY_INTERACTION_COLUMNS,
        "matched_communities": MATCHED_COMMUNITY_SUMMARY_COLUMNS,
        "partial_matched_communities": PARTIAL_MATCHED_COMMUNITY_COLUMNS,
        "user_centrality": USER_CENTRALITY_COLUMNS,
        "count_user_messages": COUNT_USER_MESSAGES_COLUMNS,
        "daily_messages_stat": DAILY_MESSAGES_STAT_COLUMNS,
        "lda_scores": LDA_SCORES_COLUMNS,
        "translation_provenance": TRANSLATION_PROVENANCE_COLUMNS,
        "matched_lda": MATCHED_LDA_COLUMNS,
        "partial_matched_lda": PARTIAL_MATCHED_LDA_COLUMNS,
        "themed_output": THEMED_OUTPUT_COLUMNS,
        "theme_generation_provenance": THEME_GENERATION_PROVENANCE_COLUMNS,
        "theme_cluster_summary": THEME_CLUSTER_SUMMARY_COLUMNS,
        "theme_cluster_observation": THEME_CLUSTER_OBSERVATION_COLUMNS,
        "theme_canonical_family": THEME_CANONICAL_FAMILY_COLUMNS,
        "theme_embedding": THEME_EMBEDDING_COLUMNS,
        "community_transition": COMMUNITY_TRANSITION_COLUMNS,
        "community_path": COMMUNITY_PATH_COLUMNS,
        "community_path_membership": COMMUNITY_PATH_MEMBERSHIP_COLUMNS,
        "community_path_theme_similarity": COMMUNITY_PATH_THEME_SIMILARITY_COLUMNS,
    }


def _theme_config(config: Mapping) -> Mapping:
    theme = config.get("theme", {})
    return theme if isinstance(theme, Mapping) else {}


def _get_latest_run_dir(base_path: Path) -> Path:
    runs_dir = base_path / "runs"
    if runs_dir.exists() and runs_dir.is_dir():
        runs = [d for d in runs_dir.iterdir() if d.is_dir()]
        if runs:
            runs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return runs[0]
    return base_path


def _months(config: Mapping, configured_month: str, longitudinal: bool) -> list[str]:
    if not longitudinal:
        return [configured_month]

    base_path = Path(str(config.get("output_base_path", "results/")))
    run_dir = _get_latest_run_dir(base_path)

    theme_input_dir = (
        run_dir
        / str(config.get("data_type", "twitter"))
        / "_intermediate"
        / "theme_inputs"
        / str(config.get("content_type", "reply"))
        / str(config.get("year", "2017"))
    )
    manifest_path = theme_input_dir / "manifest.json"
    if not manifest_path.exists():
        raise OutputContractError(
            f"Longitudinal theme input manifest is missing: {manifest_path}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    months = [str(month) for month in manifest.get("months", [])]
    if len(months) < 2:
        raise OutputContractError(
            f"Longitudinal contract requires at least two months; found {months}"
        )
    return months


def _base(params: Mapping[str, str]) -> Path:
    base_path = Path(params["output_base_path"])
    run_dir = _get_latest_run_dir(base_path)
    return run_dir / params["data_type"]


def _public_artifact_checks(
    params: Mapping[str, str],
    months: Iterable[str],
    *,
    network_data_columns: list[str] | None = None,
    evolution_similarity_enabled: bool = False,
) -> list[ArtifactCheck]:
    base = _base(params)
    theme_output = Path(params["theme_output_dir"])
    resolved_network_columns = network_data_columns or NETWORK_DATA_COLUMNS
    checks: list[ArtifactCheck] = []

    for month in months:
        checks.extend(
            [
                ArtifactCheck(
                    "network_data",
                    base
                    / "network_data"
                    / params["content_type"]
                    / f"{month}{params['year']}.parquet",
                    resolved_network_columns,
                ),
                ArtifactCheck(
                    "absolute_community_graph",
                    base
                    / "communities"
                    / "graphs"
                    / "absolute"
                    / params["content_type"]
                    / f"{month}.parquet",
                    COMMUNITY_GRAPH_COLUMNS,
                ),
                ArtifactCheck(
                    "weighted_community_graph",
                    base
                    / "communities"
                    / "graphs"
                    / "weighted"
                    / params["content_type"]
                    / f"{month}.parquet",
                    COMMUNITY_GRAPH_COLUMNS,
                ),
                ArtifactCheck(
                    "community_interactions_absolute",
                    base
                    / "communities"
                    / "interactions"
                    / "absolute"
                    / params["content_type"]
                    / f"{month}.parquet",
                    COMMUNITY_INTERACTION_COLUMNS,
                    required=False,
                ),
                ArtifactCheck(
                    "community_interactions_weighted",
                    base
                    / "communities"
                    / "interactions"
                    / "weighted"
                    / params["content_type"]
                    / f"{month}.parquet",
                    COMMUNITY_INTERACTION_COLUMNS,
                    required=False,
                ),
                ArtifactCheck(
                    "matched_communities",
                    base
                    / "communities"
                    / "matched"
                    / params["content_type"]
                    / f"{month}.parquet",
                    MATCHED_COMMUNITY_SUMMARY_COLUMNS,
                ),
                ArtifactCheck(
                    "partial_matched_communities",
                    base
                    / "communities"
                    / "partially_matched"
                    / params["content_type"]
                    / f"{month}.parquet",
                    PARTIAL_MATCHED_COMMUNITY_COLUMNS,
                    required=False,
                ),
                ArtifactCheck(
                    "user_centrality",
                    base
                    / "user_centrality"
                    / params["content_type"]
                    / f"{month}.parquet",
                    USER_CENTRALITY_COLUMNS,
                ),
                ArtifactCheck(
                    "count_user_messages",
                    base
                    / "count_user_messages"
                    / params["content_type"]
                    / f"{month}.parquet",
                    COUNT_USER_MESSAGES_COLUMNS,
                ),
                ArtifactCheck(
                    "daily_messages_stat",
                    base
                    / "daily_messages_stat"
                    / params["content_type"]
                    / f"{month}.parquet",
                    DAILY_MESSAGES_STAT_COLUMNS,
                ),
                ArtifactCheck(
                    "lda_scores",
                    base
                    / "LDA"
                    / "scores"
                    / params["content_type"]
                    / f"{month}.parquet",
                    LDA_SCORES_COLUMNS,
                ),
                ArtifactCheck(
                    "matched_lda",
                    base
                    / "LDA"
                    / "matched"
                    / params["content_type"]
                    / f"{month}_{params['year']}.parquet",
                    MATCHED_LDA_COLUMNS,
                ),
                ArtifactCheck(
                    "partial_matched_lda",
                    base
                    / "LDA"
                    / "partial_matched"
                    / params["content_type"]
                    / f"{month}_{params['year']}.parquet",
                    PARTIAL_MATCHED_LDA_COLUMNS,
                    required=False,
                ),
                ArtifactCheck(
                    "themed_output",
                    theme_output / f"{month}_{params['year']}_with_themes.parquet",
                    THEMED_OUTPUT_COLUMNS,
                ),
            ]
        )

    checks.extend(
        [
            ArtifactCheck(
                "theme_generation_provenance",
                theme_output / "theme_generation_provenance.parquet",
                THEME_GENERATION_PROVENANCE_COLUMNS,
                required=False,
            ),
            ArtifactCheck(
                "community_transition",
                theme_output / "community_transition.parquet",
                COMMUNITY_TRANSITION_COLUMNS,
                non_empty=len(list(months)) > 1,
            ),
            ArtifactCheck(
                "community_path",
                theme_output / "community_paths.parquet",
                COMMUNITY_PATH_COLUMNS,
            ),
            ArtifactCheck(
                "community_path_membership",
                theme_output / "community_path_membership.parquet",
                COMMUNITY_PATH_MEMBERSHIP_COLUMNS,
            ),
            ArtifactCheck(
                "community_path_theme_similarity",
                theme_output / "community_path_theme_similarity.parquet",
                COMMUNITY_PATH_THEME_SIMILARITY_COLUMNS,
                required=evolution_similarity_enabled,
            ),
        ]
    )
    return checks


def _validate_artifact(check: ArtifactCheck) -> None:
    path_to_read = check.path
    if not path_to_read.exists():
        raise OutputContractError(
            f"Missing required artifact {check.name}: {check.path}"
        )

    if path_to_read.suffix != ".parquet":
        raise OutputContractError(
            f"Generated artifact {check.name} must be Parquet: {check.path}"
        )
    frame = pd.read_parquet(path_to_read)

    missing = [
        column for column in check.required_columns or [] if column not in frame.columns
    ]
    if missing:
        raise OutputContractError(
            f"{check.name} at {check.path} is missing columns: {missing}"
        )
    if check.non_empty and frame.empty:
        raise OutputContractError(
            f"{check.name} at {check.path} must contain at least one row"
        )


def _assert_same_columns(left: Path, right: Path) -> None:
    if not left.exists():
        raise OutputContractError(f"Missing generated matched LDA artifact: {left}")
    if not right.exists():
        raise OutputContractError(f"Missing copied theme input artifact: {right}")
    if left.suffix != ".parquet" or right.suffix != ".parquet":
        raise OutputContractError(
            "Generated matched LDA and copied theme inputs must both be Parquet: "
            f"{left} vs {right}"
        )

    left_columns = list(pd.read_parquet(left).columns)
    right_columns = list(pd.read_parquet(right).columns)

    if left_columns != right_columns:
        raise OutputContractError(
            "Copied theme input schema differs from generated LDA output: "
            f"{left} vs {right}"
        )
