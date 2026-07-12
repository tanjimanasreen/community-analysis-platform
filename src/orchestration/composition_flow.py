import uuid
from typing import Mapping, Any, Optional

from prefect import flow
from prefect.task_runners import ThreadPoolTaskRunner
from prefect.context import get_run_context

from src.orchestration.models import PipelineRunContext, PipelineRunResult, TopicInputBundle, ArtifactReference
from src.orchestration.tasks import (
    validate_run_configuration_task,
    resolve_dataset_identity_task,
    run_monthly_network_community_phase_task,
    run_monthly_topic_phase_task,
    run_monthly_themes_task
)
from src.orchestration.settings import configure_prefect_results_dir

def _extract_topic_bundle(artifacts: list[ArtifactReference]) -> TopicInputBundle:
    """Helper to pull out required files for Topic phase."""
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
        partial_matched_communities=partial
    )

from src.orchestration.models import ThemeInputBundle


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
    Orchestrates the monthly network, community, and topic modeling phases.
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
        platform=platform
    )
    
    context = PipelineRunContext.create(
        pipeline_run_id=pipeline_run_id,
        git_commit="unknown",
        config_digest=val_config.config_digest,
        output_root=val_config.output_root,
        datasets=[dataset_ident],
        prefect_flow_run_id=prefect_flow_run_id
    )
    
    artifacts = run_monthly_network_community_phase_task(
        dataset_identity=dataset_ident,
        config=val_config,
        context=context
    )
    
    # Run topics if requested
    topic_outputs = None
    if run_topics:
        topic_input_bundle = _extract_topic_bundle(artifacts)
        topic_outputs = run_monthly_topic_phase_task(
            input_bundle=topic_input_bundle,
            config=val_config,
            context=context
        )
        
    # Run themes if requested
    theme_outputs = None
    if run_themes and topic_outputs and topic_outputs.matched_communities_topics:
        month_str = str(val_config.raw_config.get("month", "march"))
        theme_input_bundle = ThemeInputBundle(
            monthly_topic_outputs={month_str: topic_outputs.matched_communities_topics}
        )
        theme_outputs = run_monthly_themes_task(
            input_bundle=theme_input_bundle,
            config=val_config,
            context=context
        )
        
    # We can aggregate artifacts or keep them separate. For now, extend the list.
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
        
    return PipelineRunResult(
        context=context,
        artifacts=all_artifacts
    )
