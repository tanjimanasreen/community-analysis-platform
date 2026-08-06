from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

TRACKING_SCHEMA_VERSION = "1.0"
TRACKING_ADAPTER_VERSION = "1.0.0"
MAX_SUMMARY_BYTES = 64 * 1024

PARENT_TAG_KEYS = frozenset(
    {
        "tracking_schema_version",
        "tracking_adapter_version",
        "pipeline_run_id",
        "prefect_flow_run_id",
        "dataset_id",
        "data_type",
        "content_type",
        "month",
        "year",
        "git_commit",
        "git_branch",
        "dvc_revision",
        "config_digest",
        "orchestration_semantic_version",
        "execution_mode",
        "run_status",
        "failure_category",
        "failure_stage",
        "exception_type",
    }
)
PARENT_PARAM_KEYS = frozenset(
    {
        "run_topics",
        "run_themes",
        "network_algorithm",
        "community_algorithm",
        "topic_algorithm",
        "topic_random_seed",
        "theme_prompt_version",
        "configured_primary_provider",
        "configured_primary_model",
        "configured_fallback_count",
    }
)
STAGE_TAG_KEYS = frozenset(
    {
        "tracking_schema_version",
        "stage_name",
        "stage_semantic_version",
        "run_status",
        "failure_category",
        "failure_stage",
        "exception_type",
    }
)
STAGE_PARAM_KEYS = frozenset(
    {
        "network_algorithm",
        "community_algorithm",
        "topic_algorithm",
        "random_seed",
        "prompt_version",
        "configured_primary_provider",
        "configured_primary_model",
        "configured_fallback_count",
    }
)
STATUS_TAG_KEYS = frozenset(
    {"run_status", "failure_category", "failure_stage", "exception_type"}
)

PARENT_METRIC_KEYS = frozenset(
    {
        "total_duration_seconds",
        "stage_count",
        "completed_stage_count",
        "failed_stage_count",
        "artifact_count",
        "artifact_total_bytes",
    }
)
STAGE_METRIC_KEYS = frozenset(
    {
        "stage_duration_seconds",
        "artifact_count",
        "artifact_total_bytes",
        "theme_input_artifact_count",
        "matched_community_count",
        "partial_match_count",
        "theme_input_count",
        "theme_output_count",
        "theme_generation_success_count",
        "visualization_count",
        "llm_prompt_tokens",
        "llm_completion_tokens",
        "llm_tokens_per_second",
        "llm_total_cost",
        "llm_calls",
        "llm_avg_latency_ms",
        "llm_avg_ttft_ms",
        "llm_avg_tpot_ms",
    }
)
METRIC_KEYS = PARENT_METRIC_KEYS | STAGE_METRIC_KEYS


@dataclass(frozen=True)
class TrackingSettings:
    enabled: bool
    backend: str | None = None
    experiment_name: str | None = None
    backend_store_path: str | None = None
    artifact_root: str | None = None
    tracking_uri: str | None = None
    artifact_uri: str | None = None
    nested_stage_runs: bool = True
    failure_policy: str = "warn"
    log_artifact_references: bool = True


@dataclass(frozen=True)
class TrackingRunReference:
    backend: str
    experiment_id: str
    parent_run_id: str
    tracking_uri: str


@dataclass(frozen=True)
class StageRunReference:
    run_id: str
    stage_name: str


class ExperimentTracker(Protocol):
    settings: TrackingSettings

    def start_parent_run(
        self,
        *,
        run_name: str,
        tags: Mapping[str, Any],
        params: Mapping[str, Any],
    ) -> TrackingRunReference | None: ...

    def start_stage_run(
        self,
        *,
        parent: TrackingRunReference,
        stage_name: str,
        tags: Mapping[str, Any],
        params: Mapping[str, Any],
    ) -> StageRunReference | None: ...

    def log_metrics(self, run_id: str, metrics: Mapping[str, Any]) -> None: ...

    def log_tags(self, run_id: str, tags: Mapping[str, Any]) -> None: ...

    def log_params(self, run_id: str, params: Mapping[str, Any]) -> None: ...

    def log_json_artifact(
        self,
        run_id: str,
        *,
        filename: str,
        payload: Mapping[str, Any],
        artifact_path: str = "summaries",
    ) -> None: ...

    def log_table(
        self,
        run_id: str,
        *,
        filename: str,
        df: Any,
    ) -> None: ...

    def finish_run(self, run_id: str, status: str) -> None: ...
