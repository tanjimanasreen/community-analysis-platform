import uuid
from typing import Mapping, Any, Optional

from prefect import flow
from prefect.task_runners import ThreadPoolTaskRunner
from prefect.context import get_run_context

from src.orchestration.models import PipelineRunContext, PipelineRunResult
from src.orchestration.tasks import (
    validate_run_configuration_task,
    resolve_dataset_identity_task,
    run_monthly_network_community_phase_task
)
from src.orchestration.settings import configure_prefect_results_dir

@flow(
    name="run-monthly-network-foundation-flow",
    task_runner=ThreadPoolTaskRunner(max_workers=1),
    persist_result=True,
)
def run_monthly_network_foundation_flow(
    config: Mapping[str, Any],
    dataset_path: str,
    dataset_id: str,
    known_sha256: Optional[str] = None,
    platform: Optional[str] = None
) -> PipelineRunResult:
    """
    Orchestrates the monthly network and community phase.
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

    return PipelineRunResult(
        context=context,
        artifacts=artifacts
    )
