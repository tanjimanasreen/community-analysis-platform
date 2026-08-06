from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from src.artifacts.run_manifest import run_root_path
from src.orchestration.models import (
    ArtifactReference,
    DatasetIdentity,
    PipelineRunContext,
    ThemeInputBundle,
    ThemeOutputBundle,
    TopicOutputBundle,
)
from src.tracking.contracts import (
    TRACKING_ADAPTER_VERSION,
    TRACKING_SCHEMA_VERSION,
)
from src.tracking.sanitization import safe_relative_path, sanitize_json_payload


def resolve_git_metadata(project_root: str | Path) -> tuple[str, str]:
    root = Path(project_root)

    def run(*args: str) -> str:
        try:
            value = subprocess.run(
                ["git", *args],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
            return value or "unknown"
        except (OSError, subprocess.SubprocessError):
            return "unknown"

    return run("rev-parse", "HEAD"), run("branch", "--show-current")


def artifact_totals(artifacts: Iterable[ArtifactReference]) -> dict[str, float]:
    refs = list(artifacts)
    return {
        "artifact_count": float(len(refs)),
        "artifact_total_bytes": float(sum(ref.byte_size or 0 for ref in refs)),
    }


def topic_metrics(
    bundle: TopicOutputBundle, duration_seconds: float
) -> dict[str, float]:
    refs = [bundle.lda_scores]
    refs.extend(
        ref
        for ref in (
            bundle.matched_communities_topics,
            bundle.partial_matched_communities_topics,
        )
        if ref is not None
    )
    refs.extend(bundle.theme_inputs)
    metrics = {
        **artifact_totals(refs),
        "theme_input_artifact_count": float(len(bundle.theme_inputs)),
        "stage_duration_seconds": max(0.0, float(duration_seconds)),
    }
    if bundle.matched_communities_topics is not None:
        metrics["matched_community_count"] = float(
            bundle.matched_communities_topics.row_count or 0
        )
    if bundle.partial_matched_communities_topics is not None:
        metrics["partial_match_count"] = float(
            bundle.partial_matched_communities_topics.row_count or 0
        )

    # LDA score artifacts contain one compact row, so reading them here does
    # not create a large tracking-side data dependency.  Export the thesis
    # perplexity/coherence pairs as named MLflow metrics when available.
    try:
        import ast
        import pandas as pd

        score_frame = pd.read_parquet(bundle.lda_scores.path)
        if not score_frame.empty:
            score_row = score_frame.iloc[0]
            for column in (
                "unigram_absolute",
                "unigram_weighted",
                "bigram_absolute",
                "bigram_weighted",
            ):
                value = score_row.get(column)
                if isinstance(value, str):
                    value = ast.literal_eval(value)
                if hasattr(value, "tolist"):
                    value = value.tolist()
                if isinstance(value, (list, tuple)) and len(value) >= 2:
                    metrics[f"lda_{column}_perplexity"] = float(value[0])
                    metrics[f"lda_{column}_coherence"] = float(value[1])
    except (OSError, ValueError, SyntaxError, TypeError, ImportError):
        pass
    return metrics


def theme_metrics(
    input_bundle: ThemeInputBundle,
    bundle: ThemeOutputBundle,
    duration_seconds: float,
) -> dict[str, float]:
    refs = list(bundle.themes)
    if bundle.community_transitions:
        refs.append(bundle.community_transitions)
    refs.extend(bundle.visualizations)
    if bundle.provider_run_summary:
        refs.append(bundle.provider_run_summary)
    input_rows = sum(
        ref.row_count or 0 for ref in input_bundle.monthly_topic_outputs.values()
    )
    output_rows = sum(ref.row_count or 0 for ref in bundle.themes)
    metrics = {
        **artifact_totals(refs),
        "theme_input_count": float(input_rows),
        "theme_output_count": float(output_rows),
        "theme_generation_success_count": float(output_rows),
        "visualization_count": float(len(bundle.visualizations)),
        "stage_duration_seconds": max(0.0, float(duration_seconds)),
    }

    safe_provider = read_safe_provider_summary(bundle.provider_run_summary)
    if safe_provider and "run_metrics" in safe_provider:
        rm = safe_provider["run_metrics"]
        if "total_prompt_tokens" in rm:
            metrics["llm_prompt_tokens"] = float(rm["total_prompt_tokens"])
        if "total_completion_tokens" in rm:
            metrics["llm_completion_tokens"] = float(rm["total_completion_tokens"])
            if (
                metrics["llm_completion_tokens"] > 0
                and metrics["stage_duration_seconds"] > 0
            ):
                metrics["llm_tokens_per_second"] = (
                    metrics["llm_completion_tokens"] / metrics["stage_duration_seconds"]
                )
        if "total_cost" in rm:
            metrics["llm_total_cost"] = float(rm["total_cost"])
        if "calls" in rm:
            metrics["llm_calls"] = float(rm["calls"])
        for source_key, metric_key in (
            ("logical_theme_requests", "llm_logical_requests"),
            ("outbound_requests", "llm_outbound_requests"),
            ("cache_hits", "llm_cache_hits"),
            ("cache_misses", "llm_cache_misses"),
            ("cache_writes", "llm_cache_writes"),
            ("cache_errors", "llm_cache_errors"),
            ("fallback_attempts", "llm_fallback_attempts"),
        ):
            if source_key in rm:
                metrics[metric_key] = float(rm[source_key])
        if "latency_ms_list" in rm and rm["latency_ms_list"]:
            metrics["llm_avg_latency_ms"] = float(
                sum(rm["latency_ms_list"]) / len(rm["latency_ms_list"])
            )
            metrics["llm_max_latency_ms"] = float(max(rm["latency_ms_list"]))

    return metrics


def network_metrics(
    artifacts: Sequence[ArtifactReference], duration_seconds: float
) -> dict[str, float]:
    return {
        **artifact_totals(artifacts),
        "stage_duration_seconds": max(0.0, float(duration_seconds)),
    }


def _artifact_stage(asset_key: str) -> str:
    if (
        asset_key.startswith("themes_")
        or asset_key.startswith("visualization_")
        or asset_key in {"community_transitions", "provider_run_summary"}
    ):
        return "theme"
    if asset_key in {
        "lda_scores",
        "matched_communities_topics",
        "partial_matched_communities_topics",
        "theme_manifest",
    }:
        return "topic"
    return "network_community"


def build_artifact_manifest(
    context: PipelineRunContext,
    artifacts: Sequence[ArtifactReference],
) -> dict[str, Any]:
    run_root = run_root_path(context.output_root, context.pipeline_run_id)
    items = []
    for ref in artifacts:
        asset_key = ref.asset_key or "unknown"
        items.append(
            {
                "asset_key": asset_key,
                "relative_path": safe_relative_path(ref.path, run_root),
                "sha256": ref.sha256,
                "byte_size": ref.byte_size or 0,
                "media_type": ref.media_type,
                "stage": _artifact_stage(asset_key),
            }
        )
    return {
        "schema_version": TRACKING_SCHEMA_VERSION,
        "pipeline_run_id": context.pipeline_run_id,
        "artifacts": items,
    }


def _dataset_entry(dataset: DatasetIdentity, project_root: Path) -> dict[str, Any]:
    path = Path(dataset.path)
    entry: dict[str, Any] = {
        "dataset_id": dataset.dataset_id,
        "dataset_relative_path": safe_relative_path(path, project_root),
        "dataset_sha256": dataset.sha256,
        "dataset_byte_size": path.stat().st_size if path.exists() else 0,
    }
    if dataset.dvc_pointer:
        entry["dvc_file_relative_path"] = safe_relative_path(
            dataset.dvc_pointer, project_root
        )
    if dataset.dvc_content_hash:
        entry["dvc_content_hash"] = dataset.dvc_content_hash
    if dataset.dvc_revision:
        entry["dvc_revision"] = dataset.dvc_revision
    return entry


def build_lineage_summary(
    context: PipelineRunContext,
    *,
    project_root: str | Path,
    git_branch: str,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    return {
        "schema_version": TRACKING_SCHEMA_VERSION,
        "tracking_adapter_version": TRACKING_ADAPTER_VERSION,
        "pipeline_run_id": context.pipeline_run_id,
        "prefect_flow_run_id": context.prefect_flow_run_id or "",
        "git_commit": context.git_commit,
        "git_branch": git_branch,
        "dvc_revision": context.dvc_revision or "",
        "config_digest": context.config_digest,
        "datasets": [
            _dataset_entry(dataset, root) for dataset in context.dataset_identities
        ],
    }


def build_run_metrics_summary(
    *,
    total_duration_seconds: float,
    stage_count: int,
    artifacts: Sequence[ArtifactReference],
    completed_stage_count: int,
    failed_stage_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": TRACKING_SCHEMA_VERSION,
        "metrics": {
            "total_duration_seconds": max(0.0, float(total_duration_seconds)),
            "stage_count": stage_count,
            "artifact_count": len(artifacts),
            "artifact_total_bytes": sum(ref.byte_size or 0 for ref in artifacts),
            "completed_stage_count": completed_stage_count,
            "failed_stage_count": failed_stage_count,
        },
    }


def read_safe_provider_summary(
    ref: ArtifactReference | None,
) -> dict[str, Any] | None:
    if ref is None or ref.media_type != "application/json":
        return None
    path = Path(ref.path)
    if not path.is_file() or path.stat().st_size > 64 * 1024:
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    allowed = {
        "schema_version",
        "configured_primary_provider",
        "configured_primary_model",
        "configured_fallback_chain",
        "provider_config_digest",
        "prompt_version",
        "generation_settings_digest",
        "semantic_task_version",
        "run_metrics",
    }
    if not isinstance(payload, Mapping) or set(payload) - allowed:
        return None

    payload_copy = dict(payload)
    if "run_metrics" in payload_copy and isinstance(payload_copy["run_metrics"], dict):
        run_metrics_copy = dict(payload_copy["run_metrics"])
        run_metrics_copy.pop("prompts_and_responses", None)
        payload_copy["run_metrics"] = run_metrics_copy

    try:
        clean = sanitize_json_payload(payload_copy)
    except ValueError:
        return None
    return dict(clean)
