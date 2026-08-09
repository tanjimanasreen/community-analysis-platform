from __future__ import annotations

import logging
import time
import uuid
from dataclasses import replace
from typing import Any, Mapping, Optional

from prefect import flow
from prefect.context import get_run_context
from prefect.task_runners import ThreadPoolTaskRunner

from src.artifacts.run_manifest import (
    complete_run_bundle,
    fail_run_bundle,
    initialize_run_bundle,
    utc_now,
)
from src.orchestration.models import (
    ArtifactReference,
    PipelineRunContext,
    PipelineRunResult,
    ThemeInputBundle,
    TopicInputBundle,
)
from src.orchestration.retry_policy import classify_error
from src.orchestration.settings import configure_prefect_results_dir, get_project_root
from src.orchestration.tasks import (
    resolve_dataset_identity_task,
    run_monthly_network_community_phase_task,
    run_monthly_themes_task,
    run_monthly_topic_phase_task,
    validate_run_configuration_task,
)
from src.themes.benchmark.dataset import load_prompt_templates
from src.tracking.contracts import TRACKING_ADAPTER_VERSION, TRACKING_SCHEMA_VERSION
from src.tracking.factory import create_experiment_tracker
from src.tracking.summaries import (
    artifact_totals,
    build_artifact_manifest,
    build_lineage_summary,
    build_run_metrics_summary,
    network_metrics,
    read_safe_provider_summary,
    resolve_git_metadata,
    theme_metrics,
    topic_metrics,
)

logger = logging.getLogger(__name__)

ORCHESTRATION_SEMANTIC_VERSION = "1.0.0"


def _extract_topic_bundle(artifacts: list[ArtifactReference]) -> TopicInputBundle:
    """Extract required ArtifactReferences for the Topic phase from network outputs."""
    abs_msg = None
    per_msg = None
    matched = None
    partial = None
    for artifact in artifacts:
        if artifact.asset_key.startswith("topic_absolute_messages"):
            abs_msg = artifact
        elif artifact.asset_key.startswith("topic_weighted_messages"):
            per_msg = artifact
        elif artifact.asset_key.startswith("topic_matched_communities"):
            matched = artifact
        elif artifact.asset_key.startswith("topic_partial_matched"):
            partial = artifact

    if not (abs_msg and per_msg and matched):
        raise ValueError("Network phase did not produce required topic inputs.")

    return TopicInputBundle(
        absolute_community_messages=abs_msg,
        weighted_community_messages=per_msg,
        matched_communities=matched,
        partial_matched_communities=partial,
    )


def _provider_parameters(raw: Mapping[str, Any]) -> dict[str, Any]:
    theme_provider = raw.get("theme_provider", {})
    if isinstance(theme_provider, str):
        primary = theme_provider
        fallback_chain: list[str] = []
    elif isinstance(theme_provider, Mapping):
        primary = str(theme_provider.get("primary", "mock"))
        fallback_chain = [
            str(item) for item in theme_provider.get("fallback_chain", [])
        ]
    else:
        primary = "mock"
        fallback_chain = []
    model = str(raw.get("theme_model", ""))
    if not model and ":" in primary:
        _, model = primary.split(":", 1)
    return {
        "configured_primary_provider": primary.split(":", 1)[0],
        "configured_primary_model": model,
        "configured_fallback_count": len(fallback_chain),
        "theme_prompt_version": str(raw.get("prompt_version", "v1")),
    }


def _parent_tags(
    *,
    context: PipelineRunContext,
    dataset_id: str,
    raw: Mapping[str, Any],
    git_branch: str,
) -> dict[str, Any]:
    return {
        "tracking_schema_version": TRACKING_SCHEMA_VERSION,
        "tracking_adapter_version": TRACKING_ADAPTER_VERSION,
        "pipeline_run_id": context.pipeline_run_id,
        "prefect_flow_run_id": context.prefect_flow_run_id or "",
        "dataset_id": dataset_id,
        "data_type": str(raw["data_type"]),
        "content_type": str(raw["content_type"]),
        "month": str(raw.get("month", "evolution")),
        "year": str(raw["year"]),
        "git_commit": context.git_commit,
        "git_branch": git_branch,
        "dvc_revision": context.dvc_revision or "",
        "config_digest": context.config_digest,
        "orchestration_semantic_version": ORCHESTRATION_SEMANTIC_VERSION,
        "execution_mode": "local",
        "run_status": "RUNNING",
    }


def _parent_params(
    raw: Mapping[str, Any], *, run_topics: bool, run_themes: bool
) -> dict[str, Any]:
    lda = raw.get("lda", {}) if isinstance(raw.get("lda"), Mapping) else {}
    return {
        "run_topics": run_topics,
        "run_themes": run_themes,
        "network_algorithm": str(raw.get("network_algorithm", "interaction_graph")),
        "community_algorithm": str(raw.get("community_algorithm", "louvain")),
        "topic_algorithm": str(raw.get("topic_algorithm", "lda")),
        "topic_random_seed": int(lda.get("random_state", raw.get("random_state", 100))),
        **_provider_parameters(raw),
    }


def _run_name(raw: Mapping[str, Any], pipeline_run_id: str) -> str:
    return "-".join(
        [
            str(raw["data_type"]),
            str(raw["content_type"]),
            str(raw["year"]),
            str(raw.get("month", "evolution")),
            pipeline_run_id[:8],
        ]
    )


@flow(
    name="run-monthly-analysis-flow",
    persist_result=True,
)
def run_monthly_analysis_flow(
    config: Mapping[str, Any],
    dataset_path: str,
    dataset_id: str,
    known_sha256: Optional[str] = None,
    platform: Optional[str] = None,
    run_topics: bool = True,
    run_themes: bool = True,
    dvc_revision: Optional[str] = None,
) -> PipelineRunResult:
    """Run the monthly analytical stages with optional local MLflow tracking."""
    configure_prefect_results_dir()
    flow_started = time.perf_counter()
    run_started_at = utc_now()
    project_root = get_project_root()
    pipeline_run_id = str(uuid.uuid4())

    try:
        prefect_flow_run_id = str(get_run_context().flow_run.id)
    except Exception:
        prefect_flow_run_id = str(uuid.uuid4())

    val_config = validate_run_configuration_task(config=config)
    git_commit, git_branch = resolve_git_metadata(project_root)
    dataset_ident = resolve_dataset_identity_task(
        path=dataset_path,
        dataset_id=dataset_id,
        known_sha256=known_sha256,
        platform=platform,
        dvc_revision=dvc_revision,
    )
    if dataset_ident.dvc_pointer and not dataset_ident.dvc_revision:
        dataset_ident = replace(dataset_ident, dvc_revision=git_commit)
    context = PipelineRunContext.create(
        pipeline_run_id=pipeline_run_id,
        git_commit=git_commit,
        config_digest=val_config.config_digest,
        output_root=val_config.output_root,
        datasets=[dataset_ident],
        prefect_flow_run_id=prefect_flow_run_id,
        dvc_revision=dataset_ident.dvc_revision,
    )

    tracker = create_experiment_tracker(val_config.raw_config, project_root)
    tracking_ref = tracker.start_parent_run(
        run_name=_run_name(val_config.raw_config, pipeline_run_id),
        tags=_parent_tags(
            context=context,
            dataset_id=dataset_id,
            raw=val_config.raw_config,
            git_branch=git_branch,
        ),
        params=_parent_params(
            val_config.raw_config,
            run_topics=run_topics,
            run_themes=run_themes,
        ),
    )
    mlflow_run_id = tracking_ref.parent_run_id if tracking_ref is not None else None
    initialize_run_bundle(
        context=context,
        config=val_config,
        started_at=run_started_at,
        mlflow_run_id=mlflow_run_id,
    )
    if tracking_ref is not None:
        tracker.log_json_artifact(
            tracking_ref.parent_run_id,
            filename="theme_prompt_template.json",
            payload=load_prompt_templates(),
            artifact_path="prompts",
        )
    completed_stage_count = 0
    failed_stage_count = 0
    stage_count = 0
    current_stage = "initialization"
    artifacts: list[ArtifactReference] = []
    topic_outputs = None
    theme_outputs = None
    all_artifacts: list[ArtifactReference] = []

    def start_stage(name: str, params: Mapping[str, Any]):
        nonlocal stage_count, current_stage
        current_stage = name
        stage_count += 1
        if tracking_ref is None:
            return None
        return tracker.start_stage_run(
            parent=tracking_ref,
            stage_name=name,
            tags={
                "tracking_schema_version": TRACKING_SCHEMA_VERSION,
                "stage_name": name,
                "stage_semantic_version": "1.0.0",
                "run_status": "RUNNING",
            },
            params=params,
        )

    def failure_tags(stage_name: str, exc: BaseException) -> dict[str, str]:
        category = classify_error(exc) if isinstance(exc, Exception) else None
        return {
            "run_status": "FAILED",
            "failure_category": category.value if category else "UNKNOWN_TERMINAL",
            "failure_stage": stage_name,
            "exception_type": type(exc).__name__,
        }

    def fail_stage(stage_ref: Any, exc: BaseException) -> None:
        nonlocal failed_stage_count
        failed_stage_count += 1
        if stage_ref is not None:
            tracker.log_tags(
                stage_ref.run_id,
                failure_tags(stage_ref.stage_name, exc),
            )
            tracker.finish_run(stage_ref.run_id, "FAILED")

    try:
        network_ref = start_stage(
            "network_community",
            {
                "network_algorithm": str(
                    val_config.raw_config.get("network_algorithm", "interaction_graph")
                ),
                "community_algorithm": str(
                    val_config.raw_config.get("community_algorithm", "louvain")
                ),
            },
        )
        network_started = time.perf_counter()
        try:
            artifacts = run_monthly_network_community_phase_task(
                dataset_identity=dataset_ident,
                config=val_config,
                context=context,
            )
        except Exception as exc:
            fail_stage(network_ref, exc)
            raise
        if network_ref is not None:
            tracker.log_metrics(
                network_ref.run_id,
                network_metrics(artifacts, time.perf_counter() - network_started),
            )
            tracker.log_tags(network_ref.run_id, {"run_status": "FINISHED"})
            tracker.finish_run(network_ref.run_id, "FINISHED")
        completed_stage_count += 1

        if run_topics:
            topic_input_bundle = _extract_topic_bundle(artifacts)
            topic_ref = start_stage(
                "topic",
                {
                    "topic_algorithm": str(
                        val_config.raw_config.get("topic_algorithm", "lda")
                    ),
                    "random_seed": int(
                        (
                            val_config.raw_config.get("lda", {})
                            if isinstance(val_config.raw_config.get("lda"), Mapping)
                            else {}
                        ).get("random_state", 100)
                    ),
                },
            )
            topic_started = time.perf_counter()
            try:
                topic_outputs = run_monthly_topic_phase_task(
                    input_bundle=topic_input_bundle,
                    config=val_config,
                    context=context,
                )
            except Exception as exc:
                fail_stage(topic_ref, exc)
                raise
            if topic_ref is not None:
                tracker.log_metrics(
                    topic_ref.run_id,
                    topic_metrics(topic_outputs, time.perf_counter() - topic_started),
                )
                tracker.log_tags(topic_ref.run_id, {"run_status": "FINISHED"})
                tracker.finish_run(topic_ref.run_id, "FINISHED")
            completed_stage_count += 1

        if run_themes and topic_outputs and topic_outputs.matched_communities_topics:
            month_str = str(val_config.raw_config["month"])
            theme_input_bundle = ThemeInputBundle(
                monthly_topic_outputs={
                    month_str: topic_outputs.matched_communities_topics
                }
            )
            provider_params = _provider_parameters(val_config.raw_config)
            theme_ref = start_stage(
                "theme",
                {
                    "prompt_version": provider_params["theme_prompt_version"],
                    "configured_primary_provider": provider_params[
                        "configured_primary_provider"
                    ],
                    "configured_primary_model": provider_params[
                        "configured_primary_model"
                    ],
                    "configured_fallback_count": provider_params[
                        "configured_fallback_count"
                    ],
                },
            )
            theme_started = time.perf_counter()
            try:
                theme_outputs = run_monthly_themes_task(
                    input_bundle=theme_input_bundle,
                    config=val_config,
                    context=context,
                )
            except Exception as exc:
                fail_stage(theme_ref, exc)
                raise
            if theme_ref is not None:
                tracker.log_metrics(
                    theme_ref.run_id,
                    theme_metrics(
                        theme_input_bundle,
                        theme_outputs,
                        time.perf_counter() - theme_started,
                    ),
                )
                safe_provider = read_safe_provider_summary(
                    theme_outputs.provider_run_summary
                )
                if safe_provider:
                    tracker.log_json_artifact(
                        theme_ref.run_id,
                        filename="provider_run_summary.json",
                        payload=safe_provider,
                    )
                    if tracking_ref is not None:
                        tracker.log_json_artifact(
                            tracking_ref.parent_run_id,
                            filename="provider_run_summary.json",
                            payload=safe_provider,
                        )
                tracker.log_tags(theme_ref.run_id, {"run_status": "FINISHED"})
                tracker.finish_run(theme_ref.run_id, "FINISHED")
            completed_stage_count += 1

        all_artifacts = list(artifacts)
        if topic_outputs:
            all_artifacts.append(topic_outputs.lda_scores)
            if topic_outputs.matched_communities_topics:
                all_artifacts.append(topic_outputs.matched_communities_topics)
            if topic_outputs.partial_matched_communities_topics:
                all_artifacts.append(topic_outputs.partial_matched_communities_topics)
            all_artifacts.extend(topic_outputs.theme_inputs)
        if theme_outputs:
            all_artifacts.extend(theme_outputs.themes)
            all_artifacts.extend(theme_outputs.clustered_themes)
            all_artifacts.extend(theme_outputs.cluster_evidence)
            if theme_outputs.canonical_theme_families:
                all_artifacts.append(theme_outputs.canonical_theme_families)
            if theme_outputs.clustering_embeddings:
                all_artifacts.append(theme_outputs.clustering_embeddings)
            if theme_outputs.similarity_embeddings:
                all_artifacts.append(theme_outputs.similarity_embeddings)
            if theme_outputs.community_transitions:
                all_artifacts.append(theme_outputs.community_transitions)
            if theme_outputs.community_paths:
                all_artifacts.append(theme_outputs.community_paths)
            if theme_outputs.community_path_membership:
                all_artifacts.append(theme_outputs.community_path_membership)
            if theme_outputs.community_path_theme_similarity:
                all_artifacts.append(theme_outputs.community_path_theme_similarity)
            all_artifacts.extend(theme_outputs.visualizations)
            if theme_outputs.provider_run_summary:
                all_artifacts.append(theme_outputs.provider_run_summary)

        complete_run_bundle(
            context=context,
            config=val_config,
            artifacts=all_artifacts,
            started_at=run_started_at,
            mlflow_run_id=mlflow_run_id,
        )

        if tracking_ref is not None:
            total_duration = time.perf_counter() - flow_started
            parent_metrics = {
                "total_duration_seconds": total_duration,
                "stage_count": stage_count,
                "completed_stage_count": completed_stage_count,
                "failed_stage_count": failed_stage_count,
                **artifact_totals(all_artifacts),
            }
            tracker.log_metrics(tracking_ref.parent_run_id, parent_metrics)
            tracker.log_json_artifact(
                tracking_ref.parent_run_id,
                filename="lineage_summary.json",
                payload=build_lineage_summary(
                    context, project_root=project_root, git_branch=git_branch
                ),
            )
            tracker.log_json_artifact(
                tracking_ref.parent_run_id,
                filename="run_metrics_summary.json",
                payload=build_run_metrics_summary(
                    total_duration_seconds=total_duration,
                    stage_count=stage_count,
                    artifacts=all_artifacts,
                    completed_stage_count=completed_stage_count,
                    failed_stage_count=failed_stage_count,
                ),
            )
            if tracker.settings.log_artifact_references:
                tracker.log_json_artifact(
                    tracking_ref.parent_run_id,
                    filename="artifact_reference_manifest.json",
                    payload=build_artifact_manifest(context, all_artifacts),
                )
            tracker.log_tags(
                tracking_ref.parent_run_id,
                {"run_status": "FINISHED"},
            )
            tracker.finish_run(tracking_ref.parent_run_id, "FINISHED")

        return PipelineRunResult(
            context=context,
            artifacts=all_artifacts,
            tracking=tracking_ref,
        )
    except Exception as exc:
        failed_artifacts = list(artifacts)
        if topic_outputs:
            failed_artifacts.append(topic_outputs.lda_scores)
            if topic_outputs.matched_communities_topics:
                failed_artifacts.append(topic_outputs.matched_communities_topics)
            if topic_outputs.partial_matched_communities_topics:
                failed_artifacts.append(
                    topic_outputs.partial_matched_communities_topics
                )
            failed_artifacts.extend(topic_outputs.theme_inputs)
        if theme_outputs:
            failed_artifacts.extend(theme_outputs.themes)
            failed_artifacts.extend(theme_outputs.clustered_themes)
            failed_artifacts.extend(theme_outputs.cluster_evidence)
            if theme_outputs.canonical_theme_families:
                failed_artifacts.append(theme_outputs.canonical_theme_families)
            if theme_outputs.clustering_embeddings:
                failed_artifacts.append(theme_outputs.clustering_embeddings)
            if theme_outputs.similarity_embeddings:
                failed_artifacts.append(theme_outputs.similarity_embeddings)
            if theme_outputs.community_transitions:
                failed_artifacts.append(theme_outputs.community_transitions)
            if theme_outputs.community_paths:
                failed_artifacts.append(theme_outputs.community_paths)
            if theme_outputs.community_path_membership:
                failed_artifacts.append(theme_outputs.community_path_membership)
            if theme_outputs.community_path_theme_similarity:
                failed_artifacts.append(theme_outputs.community_path_theme_similarity)
            failed_artifacts.extend(theme_outputs.visualizations)
            if theme_outputs.provider_run_summary:
                failed_artifacts.append(theme_outputs.provider_run_summary)
        try:
            category = classify_error(exc)
            fail_run_bundle(
                context=context,
                config=val_config,
                started_at=run_started_at,
                failure_stage=current_stage,
                failure_type=type(exc).__name__,
                failure_category=category.value,
                artifacts=failed_artifacts,
                mlflow_run_id=mlflow_run_id,
            )
        except Exception as manifest_exc:
            logger.exception(
                "failed_run_manifest_write_failed run_id=%s stage=%s error_type=%s",
                context.pipeline_run_id,
                current_stage,
                type(manifest_exc).__name__,
            )
        if tracking_ref is not None:
            tracker.log_tags(
                tracking_ref.parent_run_id,
                failure_tags(current_stage, exc),
            )
            tracker.finish_run(tracking_ref.parent_run_id, "FAILED")
        raise


import concurrent.futures
from threading import Lock


@flow(
    name="run-evolution-analysis-flow",
    persist_result=True,
)
def run_evolution_analysis_flow(
    config: Mapping[str, Any],
) -> PipelineRunResult:
    """Run the longitudinal multi-month analytical stages dynamically."""
    configure_prefect_results_dir()
    flow_started = time.perf_counter()
    run_started_at = utc_now()
    project_root = get_project_root()
    pipeline_run_id = str(uuid.uuid4())

    try:
        prefect_flow_run_id = str(get_run_context().flow_run.id)
    except Exception:
        prefect_flow_run_id = str(uuid.uuid4())

    val_config = validate_run_configuration_task(config=config)
    git_commit, git_branch = resolve_git_metadata(project_root)

    context = PipelineRunContext.create(
        pipeline_run_id=pipeline_run_id,
        git_commit=git_commit,
        config_digest=val_config.config_digest,
        output_root=val_config.output_root,
        datasets=[],
        prefect_flow_run_id=prefect_flow_run_id,
        dvc_revision=None,
    )

    tracker = create_experiment_tracker(val_config.raw_config, project_root)
    tracking_ref = tracker.start_parent_run(
        run_name=_run_name(val_config.raw_config, pipeline_run_id) + "-evolution",
        tags=_parent_tags(
            context=context,
            dataset_id="longitudinal",
            raw=val_config.raw_config,
            git_branch=git_branch,
        ),
        params=_parent_params(
            val_config.raw_config,
            run_topics=True,
            run_themes=True,
        ),
    )
    mlflow_run_id = tracking_ref.parent_run_id if tracking_ref is not None else None
    initialize_run_bundle(
        context=context,
        config=val_config,
        started_at=run_started_at,
        mlflow_run_id=mlflow_run_id,
    )
    if tracking_ref is not None:
        tracker.log_json_artifact(
            tracking_ref.parent_run_id,
            filename="theme_prompt_template.json",
            payload=load_prompt_templates(),
            artifact_path="prompts",
        )

    stage_count_lock = Lock()
    completed_stage_count = 0
    failed_stage_count = 0
    stage_count = 0
    current_stage = "initialization"
    all_artifacts: list[ArtifactReference] = []
    dataset_idents: list[DatasetIdentity] = []

    def start_stage(name: str, params: Mapping[str, Any]):
        nonlocal stage_count, current_stage
        with stage_count_lock:
            current_stage = name
            stage_count += 1
        if tracking_ref is None:
            return None
        return tracker.start_stage_run(
            parent=tracking_ref,
            stage_name=name,
            tags={
                "tracking_schema_version": TRACKING_SCHEMA_VERSION,
                "stage_name": name,
                "stage_semantic_version": "1.0.0",
                "run_status": "RUNNING",
            },
            params=params,
        )

    def failure_tags(stage_name: str, exc: BaseException) -> dict[str, str]:
        category = classify_error(exc) if isinstance(exc, Exception) else None
        return {
            "run_status": "FAILED",
            "failure_category": category.value if category else "UNKNOWN_TERMINAL",
            "failure_stage": stage_name,
            "exception_type": type(exc).__name__,
        }

    def fail_stage(stage_ref: Any, exc: BaseException) -> None:
        nonlocal failed_stage_count
        with stage_count_lock:
            failed_stage_count += 1
        if stage_ref is not None:
            tracker.log_tags(
                stage_ref.run_id,
                failure_tags(stage_ref.stage_name, exc),
            )
            tracker.finish_run(stage_ref.run_id, "FAILED")

    try:
        datasets = val_config.raw_config.get("longitudinal_datasets", [])
        if not datasets:
            raise ValueError("No longitudinal_datasets found in configuration.")

        topic_outputs_by_month = {}
        last_val_config = None

        def _process_month(
            ds: dict,
        ) -> tuple[
            str,
            ValidatedRunConfiguration,
            DatasetIdentity,
            list[ArtifactReference],
            Any,
        ]:
            month = ds.get("month")
            input_path = ds.get("input_path")

            mod_raw = dict(val_config.raw_config)
            mod_raw["month"] = month
            mod_raw["input_path"] = input_path

            month_val_config = validate_run_configuration_task(config=mod_raw)
            dataset_ident = resolve_dataset_identity_task(
                path=input_path,
                dataset_id=f"{month}",
            )

            month_artifacts = []
            network_ref = start_stage(
                f"network_{month}", {"network_algorithm": "interaction_graph"}
            )
            network_started = time.perf_counter()
            try:
                network_artifacts = run_monthly_network_community_phase_task(
                    dataset_identity=dataset_ident,
                    config=month_val_config,
                    context=context,
                )
            except Exception as exc:
                fail_stage(network_ref, exc)
                raise
            if network_ref is not None:
                tracker.log_metrics(
                    network_ref.run_id,
                    network_metrics(
                        network_artifacts, time.perf_counter() - network_started
                    ),
                )
                tracker.log_tags(network_ref.run_id, {"run_status": "FINISHED"})
                tracker.finish_run(network_ref.run_id, "FINISHED")

            with stage_count_lock:
                nonlocal completed_stage_count
                completed_stage_count += 1

            month_artifacts.extend(network_artifacts)

            topic_input_bundle = _extract_topic_bundle(network_artifacts)
            topic_ref = start_stage(f"topic_{month}", {"topic_algorithm": "lda"})
            topic_started = time.perf_counter()
            try:
                topic_outputs = run_monthly_topic_phase_task(
                    input_bundle=topic_input_bundle,
                    config=month_val_config,
                    context=context,
                )
            except Exception as exc:
                fail_stage(topic_ref, exc)
                raise
            if topic_ref is not None:
                tracker.log_metrics(
                    topic_ref.run_id,
                    topic_metrics(topic_outputs, time.perf_counter() - topic_started),
                )
                tracker.log_tags(topic_ref.run_id, {"run_status": "FINISHED"})
                tracker.finish_run(topic_ref.run_id, "FINISHED")

            with stage_count_lock:
                completed_stage_count += 1

            month_artifacts.append(topic_outputs.lda_scores)
            if topic_outputs.matched_communities_topics:
                month_artifacts.append(topic_outputs.matched_communities_topics)
            if topic_outputs.partial_matched_communities_topics:
                month_artifacts.append(topic_outputs.partial_matched_communities_topics)
            month_artifacts.extend(topic_outputs.theme_inputs)

            return (
                str(month),
                month_val_config,
                dataset_ident,
                month_artifacts,
                topic_outputs,
            )

        # Run months concurrently
        from contextvars import copy_context

        max_w = int(
            val_config.raw_config.get("orchestration", {}).get("month_workers", 1)
        )
        max_w = max(1, max_w)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as executor:
            # We want to preserve the order of datasets
            futures = []
            for ds in datasets:
                ctx = copy_context()
                futures.append(executor.submit(ctx.run, _process_month, ds))

            for future in futures:
                try:
                    month_str, month_config, dataset_ident, m_artifacts, t_outputs = (
                        future.result()
                    )
                    last_val_config = month_config
                    dataset_idents.append(dataset_ident)
                    all_artifacts.extend(m_artifacts)
                    if t_outputs.matched_communities_topics:
                        topic_outputs_by_month[month_str] = (
                            t_outputs.matched_communities_topics
                        )
                except Exception as exc:
                    # Let the pipeline error out if a thread fails
                    raise exc

        if topic_outputs_by_month:
            theme_input_bundle = ThemeInputBundle(
                monthly_topic_outputs=topic_outputs_by_month
            )
            provider_params = _provider_parameters(val_config.raw_config)
            theme_ref = start_stage(
                "evolution_theme",
                {
                    "prompt_version": provider_params["theme_prompt_version"],
                    "configured_primary_provider": provider_params[
                        "configured_primary_provider"
                    ],
                    "configured_primary_model": provider_params[
                        "configured_primary_model"
                    ],
                    "configured_fallback_count": provider_params[
                        "configured_fallback_count"
                    ],
                },
            )
            theme_started = time.perf_counter()
            try:
                theme_outputs = run_monthly_themes_task(
                    input_bundle=theme_input_bundle,
                    config=last_val_config,
                    context=context,
                )
            except Exception as exc:
                fail_stage(theme_ref, exc)
                raise
            if theme_ref is not None:
                tracker.log_metrics(
                    theme_ref.run_id,
                    theme_metrics(
                        theme_input_bundle,
                        theme_outputs,
                        time.perf_counter() - theme_started,
                    ),
                )
                safe_provider = read_safe_provider_summary(
                    theme_outputs.provider_run_summary
                )
                if safe_provider:
                    tracker.log_json_artifact(
                        theme_ref.run_id,
                        filename="provider_run_summary.json",
                        payload=safe_provider,
                    )
                tracker.log_tags(theme_ref.run_id, {"run_status": "FINISHED"})
                tracker.finish_run(theme_ref.run_id, "FINISHED")
            completed_stage_count += 1

            all_artifacts.extend(theme_outputs.themes)
            all_artifacts.extend(theme_outputs.clustered_themes)
            all_artifacts.extend(theme_outputs.cluster_evidence)
            if theme_outputs.canonical_theme_families:
                all_artifacts.append(theme_outputs.canonical_theme_families)
            if theme_outputs.clustering_embeddings:
                all_artifacts.append(theme_outputs.clustering_embeddings)
            if theme_outputs.similarity_embeddings:
                all_artifacts.append(theme_outputs.similarity_embeddings)
            if theme_outputs.community_transitions:
                all_artifacts.append(theme_outputs.community_transitions)
            if theme_outputs.community_paths:
                all_artifacts.append(theme_outputs.community_paths)
            if theme_outputs.community_path_membership:
                all_artifacts.append(theme_outputs.community_path_membership)
            if theme_outputs.community_path_theme_similarity:
                all_artifacts.append(theme_outputs.community_path_theme_similarity)
            all_artifacts.extend(theme_outputs.visualizations)
            if theme_outputs.provider_run_summary:
                all_artifacts.append(theme_outputs.provider_run_summary)

        context = PipelineRunContext.create(
            pipeline_run_id=context.pipeline_run_id,
            git_commit=context.git_commit,
            config_digest=context.config_digest,
            output_root=context.output_root,
            datasets=dataset_idents,
            prefect_flow_run_id=context.prefect_flow_run_id,
            dvc_revision=context.dvc_revision,
        )

        import os
        from src.artifacts.run_manifest import _fallback_key
        from src.orchestration.tasks import hash_file

        final_manifest_path = None
        seen_keys: set[str] = set()
        filtered_artifacts = []
        for a in all_artifacts:
            if a.asset_key and a.asset_key.startswith("theme_manifest"):
                final_manifest_path = a.path
                continue
            key = a.asset_key or _fallback_key(a.path)
            if key in seen_keys:
                stem = _fallback_key(a.path)
                key = f"{key}_{stem}"
                a = ArtifactReference(
                    path=a.path,
                    sha256=a.sha256,
                    media_type=a.media_type,
                    byte_size=a.byte_size,
                    row_count=a.row_count,
                    asset_key=key,
                )
            seen_keys.add(key)
            filtered_artifacts.append(a)

        if final_manifest_path and os.path.exists(final_manifest_path):
            manifest_key = "theme_manifest"
            if manifest_key in seen_keys:
                manifest_key = f"{manifest_key}_final"
            filtered_artifacts.append(
                ArtifactReference(
                    path=final_manifest_path,
                    sha256=hash_file(final_manifest_path),
                    media_type="application/json",
                    byte_size=os.path.getsize(final_manifest_path),
                    asset_key=manifest_key,
                )
            )
        all_artifacts = filtered_artifacts

        complete_run_bundle(
            context=context,
            config=val_config,
            artifacts=all_artifacts,
            started_at=run_started_at,
            mlflow_run_id=mlflow_run_id,
        )

        if tracking_ref is not None:
            total_duration = time.perf_counter() - flow_started
            parent_metrics = {
                "total_duration_seconds": total_duration,
                "stage_count": stage_count,
                "completed_stage_count": completed_stage_count,
                "failed_stage_count": failed_stage_count,
                **artifact_totals(all_artifacts),
            }
            tracker.log_metrics(tracking_ref.parent_run_id, parent_metrics)
            tracker.log_json_artifact(
                tracking_ref.parent_run_id,
                filename="lineage_summary.json",
                payload=build_lineage_summary(
                    context, project_root=project_root, git_branch=git_branch
                ),
            )
            tracker.log_json_artifact(
                tracking_ref.parent_run_id,
                filename="run_metrics_summary.json",
                payload=build_run_metrics_summary(
                    total_duration_seconds=total_duration,
                    stage_count=stage_count,
                    artifacts=all_artifacts,
                    completed_stage_count=completed_stage_count,
                    failed_stage_count=failed_stage_count,
                ),
            )
            if tracker.settings.log_artifact_references:
                tracker.log_json_artifact(
                    tracking_ref.parent_run_id,
                    filename="artifact_reference_manifest.json",
                    payload=build_artifact_manifest(context, all_artifacts),
                )
            tracker.log_tags(tracking_ref.parent_run_id, {"run_status": "FINISHED"})
            tracker.finish_run(tracking_ref.parent_run_id, "FINISHED")

        return PipelineRunResult(
            context=context,
            artifacts=all_artifacts,
            tracking=tracking_ref,
        )

    except Exception as exc:
        try:
            category = classify_error(exc)
            fail_run_bundle(
                context=context,
                config=val_config,
                started_at=run_started_at,
                failure_stage=current_stage,
                failure_type=type(exc).__name__,
                failure_category=category.value,
                artifacts=all_artifacts,
                mlflow_run_id=mlflow_run_id,
            )
        except Exception as manifest_exc:
            logger.exception(
                "failed_run_manifest_write_failed run_id=%s stage=%s error_type=%s",
                context.pipeline_run_id,
                current_stage,
                type(manifest_exc).__name__,
            )
        if tracking_ref is not None:
            tracker.log_tags(
                tracking_ref.parent_run_id,
                failure_tags(current_stage, exc),
            )
            tracker.finish_run(tracking_ref.parent_run_id, "FAILED")
        raise
