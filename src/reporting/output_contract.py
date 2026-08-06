from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from src.themes.theme_inputs import ThemeInputError, load_theme_inputs
from src.topics.topic_inputs import TopicInputError, load_topic_inputs

NETWORK_DATA_COLUMNS = ["unique_id", "from_id", "forwarder_id", "text", "created_at"]
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
    """Raised when generated artifacts do not match the frozen contract."""


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
        path_to_check = check.path
        if not path_to_check.exists():
            alt = path_to_check.with_suffix(
                ".parquet" if path_to_check.suffix == ".csv" else ".csv"
            )
            if alt.exists():
                path_to_check = alt
        if not path_to_check.exists() and not check.required:
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
            / f"{month}_{params['year']}.csv"
        )
        internal_lda = (
            _base(params)
            / "_intermediate"
            / "theme_inputs"
            / params["content_type"]
            / params["year"]
            / f"{month}_{params['year']}.csv"
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
    return _public_artifact_checks(params, months)


def get_required_columns_by_artifact() -> dict[str, list[str]]:
    """Expose frozen public CSV schemas for readers and API metadata."""
    return {
        "network_data": NETWORK_DATA_COLUMNS,
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
        "matched_lda": MATCHED_LDA_COLUMNS,
        "partial_matched_lda": PARTIAL_MATCHED_LDA_COLUMNS,
        "themed_output": THEMED_OUTPUT_COLUMNS,
        "community_transition": COMMUNITY_TRANSITION_COLUMNS,
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
    params: Mapping[str, str], months: Iterable[str]
) -> list[ArtifactCheck]:
    base = _base(params)
    theme_output = Path(params["theme_output_dir"])
    checks: list[ArtifactCheck] = []

    for month in months:
        checks.extend(
            [
                ArtifactCheck(
                    "network_data",
                    base
                    / "network_data"
                    / params["content_type"]
                    / f"{month}{params['year']}.csv",
                    NETWORK_DATA_COLUMNS,
                ),
                ArtifactCheck(
                    "absolute_community_graph",
                    base
                    / "communities"
                    / "graphs"
                    / "absolute"
                    / params["content_type"]
                    / f"{month}.csv",
                    COMMUNITY_GRAPH_COLUMNS,
                ),
                ArtifactCheck(
                    "weighted_community_graph",
                    base
                    / "communities"
                    / "graphs"
                    / "weighted"
                    / params["content_type"]
                    / f"{month}.csv",
                    COMMUNITY_GRAPH_COLUMNS,
                ),
                ArtifactCheck(
                    "community_interactions_absolute",
                    base
                    / "communities"
                    / "interactions"
                    / "absolute"
                    / params["content_type"]
                    / f"{month}.csv",
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
                    / f"{month}.csv",
                    COMMUNITY_INTERACTION_COLUMNS,
                    required=False,
                ),
                ArtifactCheck(
                    "matched_communities",
                    base
                    / "communities"
                    / "matched"
                    / params["content_type"]
                    / f"{month}.csv",
                    MATCHED_COMMUNITY_SUMMARY_COLUMNS,
                ),
                ArtifactCheck(
                    "partial_matched_communities",
                    base
                    / "communities"
                    / "partially_matched"
                    / params["content_type"]
                    / f"{month}.csv",
                    PARTIAL_MATCHED_COMMUNITY_COLUMNS,
                    required=False,
                ),
                ArtifactCheck(
                    "user_centrality",
                    base / "user_centrality" / params["content_type"] / f"{month}.csv",
                    USER_CENTRALITY_COLUMNS,
                ),
                ArtifactCheck(
                    "count_user_messages",
                    base
                    / "count_user_messages"
                    / params["content_type"]
                    / f"{month}.csv",
                    COUNT_USER_MESSAGES_COLUMNS,
                ),
                ArtifactCheck(
                    "daily_messages_stat",
                    base
                    / "daily_messages_stat"
                    / params["content_type"]
                    / f"{month}.csv",
                    DAILY_MESSAGES_STAT_COLUMNS,
                ),
                ArtifactCheck(
                    "lda_scores",
                    base / "LDA" / "scores" / params["content_type"] / f"{month}.csv",
                    LDA_SCORES_COLUMNS,
                ),
                ArtifactCheck(
                    "matched_lda",
                    base
                    / "LDA"
                    / "matched"
                    / params["content_type"]
                    / f"{month}_{params['year']}.csv",
                    MATCHED_LDA_COLUMNS,
                ),
                ArtifactCheck(
                    "partial_matched_lda",
                    base
                    / "LDA"
                    / "partial_matched"
                    / params["content_type"]
                    / f"{month}_{params['year']}.csv",
                    PARTIAL_MATCHED_LDA_COLUMNS,
                    required=False,
                ),
                ArtifactCheck(
                    "themed_output",
                    theme_output / f"{month}_{params['year']}_with_themes.csv",
                    THEMED_OUTPUT_COLUMNS,
                ),
            ]
        )

    checks.append(
        ArtifactCheck(
            "community_transition",
            theme_output / "community_transition.csv",
            COMMUNITY_TRANSITION_COLUMNS,
            non_empty=len(list(months)) > 1,
        )
    )
    return checks


def _validate_artifact(check: ArtifactCheck) -> None:
    path_to_read = check.path
    if not path_to_read.exists():
        # Fallback to .parquet if .csv was requested and missing, or vice versa
        alt_path = path_to_read.with_suffix(
            ".parquet" if path_to_read.suffix == ".csv" else ".csv"
        )
        if alt_path.exists():
            path_to_read = alt_path
        else:
            raise OutputContractError(
                f"Missing required artifact {check.name}: {check.path}"
            )

    if path_to_read.suffix == ".parquet":
        frame = pd.read_parquet(path_to_read)
    else:
        frame = pd.read_csv(path_to_read, low_memory=False)

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
    left_path = left
    if not left_path.exists():
        alt_left = left_path.with_suffix(
            ".parquet" if left_path.suffix == ".csv" else ".csv"
        )
        if alt_left.exists():
            left_path = alt_left

    right_path = right
    if not right_path.exists():
        alt_right = right_path.with_suffix(
            ".parquet" if right_path.suffix == ".csv" else ".csv"
        )
        if alt_right.exists():
            right_path = alt_right

    if not right_path.exists():
        raise OutputContractError(f"Missing copied theme input artifact: {right}")

    if left_path.suffix == ".parquet":
        left_columns = list(pd.read_parquet(left_path).columns)
    else:
        left_columns = list(pd.read_csv(left_path, nrows=0).columns)

    if right_path.suffix == ".parquet":
        right_columns = list(pd.read_parquet(right_path).columns)
    else:
        right_columns = list(pd.read_csv(right_path, nrows=0).columns)

    if left_columns != right_columns:
        raise OutputContractError(
            f"Copied theme input schema differs from public LDA output: {left_path} vs {right_path}"
        )
