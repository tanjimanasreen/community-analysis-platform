import uuid
from typing import Any, Mapping, Optional

from prefect import flow
from prefect.context import get_run_context
from prefect.task_runners import ThreadPoolTaskRunner

from src.orchestration.models import (
    ArtifactReference,
    PipelineRunContext,
    PipelineRunResult,
    ThemeInputBundle,
    TopicInputBundle,
)
from src.orchestration.settings import configure_prefect_results_dir
from src.orchestration.tasks import (
    resolve_dataset_identity_task,
    run_monthly_network_community_phase_task,
    run_monthly_themes_task,
    run_monthly_topic_phase_task,
    validate_run_configuration_task,
)


def _extract_topic_bundle(artifacts: list[ArtifactReference]) -> TopicInputBundle:
    """Extract required ArtifactReferences for the Topic phase from network outputs."""
    abs_msg = None
    per_msg = None
    matched = None
    partial = None
    for a in artifacts:
        if a.asset_key == "topic_absolute_messages":
            abs_msg = a
        elif a.asset_key == "topic_weighted_messages":
            per_msg = a
        elif a.asset_key == "topic_matched":
            matched = a
        elif a.asset_key == "topic_partial_matched":
            partial = a

    if not (abs_msg and per_msg and matched):
        raise ValueError("Network phase did not produce required topic inputs.")

    return TopicInputBundle(
        absolute_community_messages=abs_msg,
        weighted_community_messages=per_msg,
        matched_communities=matched,
        partial_matched_communities=partial,
    )


@flow(
    name="run-monthly-analysis-flow",
    task_runner=ThreadPoolTaskRunner(max_workers=1),
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
) -> PipelineRunResult:
    """
    Orchestrates the monthly network, community, topic-model, and theme phases.

    Stage dependencies:
        1. validate_run_configuration_task
        2. resolve_dataset_identity_task
        3. run_monthly_network_community_phase_task
        4. run_monthly_topic_phase_task   (if run_topics=True)
        5. run_monthly_themes_task        (if run_themes=True and topic outputs exist)

    All large objects (DataFrames, models) stay inside tasks.
    Only ArtifactReferences, PipelineRunContext, and small typed metadata cross task
    boundaries or enter Prefect persisted result storage.
    """
    configure_prefect_results_dir()

    pipeline_run_id = str(uuid.uuid4())

    try:
        ctx = get_run_context()
        prefect_flow_run_id = str(ctx.flow_run.id)
    except Exception:
        prefect_flow_run_id = str(uuid.uuid4())

    val_config = validate_run_configuration_task(config=config)

    dataset_ident = resolve_dataset_identity_task(
        path=dataset_path,
        dataset_id=dataset_id,
        known_sha256=known_sha256,
        platform=platform,
    )

    context = PipelineRunContext.create(
        pipeline_run_id=pipeline_run_id,
        git_commit="unknown",
        config_digest=val_config.config_digest,
        output_root=val_config.output_root,
        datasets=[dataset_ident],
        prefect_flow_run_id=prefect_flow_run_id,
    )

    artifacts = run_monthly_network_community_phase_task(
        dataset_identity=dataset_ident,
        config=val_config,
        context=context,
    )

    topic_outputs = None
    if run_topics:
        topic_input_bundle = _extract_topic_bundle(artifacts)
        topic_outputs = run_monthly_topic_phase_task(
            input_bundle=topic_input_bundle,
            config=val_config,
            context=context,
        )

    theme_outputs = None
    if run_themes and topic_outputs and topic_outputs.matched_communities_topics:
        month_str = str(val_config.raw_config["month"])
        theme_input_bundle = ThemeInputBundle(
            monthly_topic_outputs={month_str: topic_outputs.matched_communities_topics}
        )
        theme_outputs = run_monthly_themes_task(
            input_bundle=theme_input_bundle,
            config=val_config,
            context=context,
        )

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
        if theme_outputs.community_transitions:
            all_artifacts.append(theme_outputs.community_transitions)
        all_artifacts.extend(theme_outputs.visualizations)
        if theme_outputs.provider_run_summary:
            all_artifacts.append(theme_outputs.provider_run_summary)

    return PipelineRunResult(context=context, artifacts=all_artifacts)
