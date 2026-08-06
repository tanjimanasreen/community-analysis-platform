import logging
import uuid
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
from src.orchestration.models import PipelineRunContext, PipelineRunResult
from src.orchestration.retry_policy import classify_error
from src.orchestration.settings import configure_prefect_results_dir
from src.orchestration.tasks import (
    resolve_dataset_identity_task,
    run_monthly_network_community_phase_task,
    validate_run_configuration_task,
)

logger = logging.getLogger(__name__)


@flow(
    name="run-monthly-network-foundation-flow",
    persist_result=True,
)
def run_monthly_network_foundation_flow(
    config: Mapping[str, Any],
    dataset_path: str,
    dataset_id: str,
    known_sha256: Optional[str] = None,
    platform: Optional[str] = None,
) -> PipelineRunResult:
    """Orchestrate the monthly network/community phase with a run manifest."""
    configure_prefect_results_dir()
    started_at = utc_now()
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
    initialize_run_bundle(
        context=context,
        config=val_config,
        started_at=started_at,
    )

    artifacts = []
    try:
        artifacts = run_monthly_network_community_phase_task(
            dataset_identity=dataset_ident,
            config=val_config,
            context=context,
        )
        complete_run_bundle(
            context=context,
            config=val_config,
            artifacts=artifacts,
            started_at=started_at,
        )
        return PipelineRunResult(context=context, artifacts=artifacts)
    except Exception as exc:
        try:
            fail_run_bundle(
                context=context,
                config=val_config,
                started_at=started_at,
                failure_stage="network_community",
                failure_type=type(exc).__name__,
                failure_category=classify_error(exc).value,
                artifacts=artifacts,
            )
        except Exception as manifest_exc:
            logger.exception(
                "failed_run_manifest_write_failed run_id=%s stage=network_community error_type=%s",
                context.pipeline_run_id,
                type(manifest_exc).__name__,
            )
        raise
