import os
import uuid
from typing import Any, Mapping

from prefect import flow, task
from prefect.task_runners import ThreadPoolTaskRunner
from prefect.context import get_run_context

from .models import DatasetIdentity, ArtifactReference, PipelineRunContext
from .hashing import hash_mapping, hash_file
from .settings import configure_prefect_results_dir


@task(retries=0, persist_result=True)
def build_config_digest_task(config: Mapping[str, Any]) -> str:
    """A minimal task to build a config digest deterministically."""
    return hash_mapping(config)


@task(retries=0, persist_result=True)
def create_test_artifact_task(content: str, output_path: str) -> ArtifactReference:
    """A minimal task that writes a small file and returns its ArtifactReference."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    sha256 = hash_file(output_path)
    return ArtifactReference(
        path=output_path,
        sha256=sha256,
        media_type="text/plain",
        byte_size=len(content.encode("utf-8")),
    )


@flow()
def run_orchestration_foundation_flow(
    config: Mapping[str, Any], dataset_metadata: Mapping[str, str], output_root: str
) -> dict[str, Any]:
    """
    Skeleton offline Prefect flow to validate orchestration foundation.
    It builds run context, generates digests, and manages small artifacts.
    """
    configure_prefect_results_dir()

    # 1. Capture Prefect Flow Run ID
    try:
        ctx = get_run_context()
        flow_run_id = str(ctx.flow_run.id) if ctx.flow_run else None
    except Exception:
        flow_run_id = None

    # 2. Build DatasetIdentity
    dataset_identity = DatasetIdentity(
        dataset_id=dataset_metadata.get("dataset_id", "test-dataset"),
        path=dataset_metadata.get("path", "/dev/null"),
        sha256=dataset_metadata.get("sha256", "a" * 64),
        platform=dataset_metadata.get("platform"),
    )

    # 3. Task: Config digest
    config_digest = build_config_digest_task(config)

    # 4. Create Run Context
    pipeline_run_id = str(uuid.uuid4())
    run_context = PipelineRunContext.create(
        pipeline_run_id=pipeline_run_id,
        git_commit="mock-commit",
        config_digest=config_digest,
        output_root=output_root,
        datasets=[dataset_identity],
        prefect_flow_run_id=flow_run_id,
    )

    # 5. Task: Artifact creation
    artifact_path = os.path.join(output_root, "test_artifact.txt")
    artifact_ref = create_test_artifact_task("foundation test content", artifact_path)

    # Return serializable summary
    return {
        "pipeline_run_id": run_context.pipeline_run_id,
        "prefect_flow_run_id": run_context.prefect_flow_run_id,
        "config_digest": run_context.config_digest,
        "artifact_ref_path": artifact_ref.path,
        "artifact_ref_hash": artifact_ref.sha256,
    }
