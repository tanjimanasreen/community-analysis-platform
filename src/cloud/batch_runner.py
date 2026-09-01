"""AWS Batch analytical pipeline execution wrapper.

Handles:
1. Parsing explicit Batch job parameters and environment variables.
2. Synchronizing raw inputs and stage cache from S3 to local workspace.
3. Invoking the canonical Python pipeline flow (`run-evolution-pipeline` or
   `run-all`).
4. Verifying completion manifest integrity.
5. Publishing completed run bundles and cache to S3 with manifest.json
   uploaded LAST.
6. Structured logging and fail-fast exit status.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import boto3

from src.config.loader import load_config, validate_run_config
from src.logging_config import setup_logging
from src.themes.tei_health import wait_for_tei_services

logger = logging.getLogger("community_analysis.batch_runner")


@dataclass(frozen=True)
class BatchRunnerConfig:
    """Resolved runtime configuration for AWS Batch execution."""

    config_path: str
    command: str
    s3_bucket: str | None
    theme_provider: str | None
    dataset_id: str | None
    workspace_dir: Path
    skip_s3_download: bool
    skip_s3_upload: bool
    dry_run: bool


def parse_args(args: Sequence[str] | None = None) -> BatchRunnerConfig:
    """Parse CLI options and resolve environment variable fallbacks."""
    parser = argparse.ArgumentParser(
        description="Community Analysis AWS Batch Analytical Pipeline Runner"
    )
    parser.add_argument(
        "--config",
        dest="config_path",
        default=os.environ.get("CONFIG_PATH") or os.environ.get("CONFIG"),
        help="Path to pipeline configuration YAML (or env CONFIG_PATH)",
    )
    parser.add_argument(
        "--command",
        dest="command",
        default=os.environ.get("PIPELINE_COMMAND"),
        choices=["run-evolution-pipeline", "run-all"],
        help="Pipeline command to execute (or env PIPELINE_COMMAND)",
    )
    parser.add_argument(
        "--s3-bucket",
        dest="s3_bucket",
        default=os.environ.get("COMMUNITY_ANALYSIS_S3_BUCKET")
        or os.environ.get("S3_BUCKET"),
        help="S3 bucket for input/output storage (or env COMMUNITY_ANALYSIS_S3_BUCKET)",
    )
    parser.add_argument(
        "--theme-provider",
        dest="theme_provider",
        default=os.environ.get("THEME_PROVIDER"),
        help="Override theme provider (e.g. 'mock' or 'openai')",
    )
    parser.add_argument(
        "--dataset-id",
        dest="dataset_id",
        default=os.environ.get("DATASET_ID"),
        help="Optional dataset ID override (or env DATASET_ID)",
    )
    parser.add_argument(
        "--workspace",
        dest="workspace",
        default=os.environ.get("WORKSPACE_DIR") or "/app/workspace",
        help="Local writable working directory",
    )
    parser.add_argument(
        "--skip-s3-download",
        dest="skip_s3_download",
        action="store_true",
        default=os.environ.get("SKIP_S3_DOWNLOAD", "").lower() in ("true", "1", "yes"),
        help="Skip downloading inputs from S3 (useful for local testing)",
    )
    parser.add_argument(
        "--skip-s3-upload",
        dest="skip_s3_upload",
        action="store_true",
        default=os.environ.get("SKIP_S3_UPLOAD", "").lower() in ("true", "1", "yes"),
        help="Skip uploading outputs to S3 (useful for local testing)",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Validate parameters and configuration without executing pipeline",
    )

    parsed = parser.parse_args(args)

    if not parsed.config_path:
        parser.error(
            "Configuration path is required. Provide via --config or env CONFIG_PATH"
        )

    # Resolve default command from config content if not explicitly supplied
    command = parsed.command
    if not command:
        try:
            raw_cfg = load_config(parsed.config_path)
            if "longitudinal_datasets" in raw_cfg:
                command = "run-evolution-pipeline"
            else:
                command = "run-all"
        except Exception:
            command = "run-evolution-pipeline"

    workspace_dir = Path(parsed.workspace).resolve()

    return BatchRunnerConfig(
        config_path=parsed.config_path,
        command=command,
        s3_bucket=parsed.s3_bucket.strip() if parsed.s3_bucket else None,
        theme_provider=parsed.theme_provider.strip() if parsed.theme_provider else None,
        dataset_id=parsed.dataset_id.strip() if parsed.dataset_id else None,
        workspace_dir=workspace_dir,
        skip_s3_download=parsed.skip_s3_download,
        skip_s3_upload=parsed.skip_s3_upload,
        dry_run=parsed.dry_run,
    )


def _safe_s3_dest_path(target_dir: Path, rel_path: str, raw_key: str) -> Path:
    """Validate and resolve S3 object destination path to prevent traversal.

    Rejects:
    - Absolute paths
    - Path components containing '..'
    - Paths escaping target_dir
    """
    if (
        Path(rel_path).is_absolute()
        or rel_path.startswith("/")
        or rel_path.startswith("\\")
    ):
        raise ValueError(f"Absolute path detected in S3 object key: {raw_key!r}")

    path_obj = Path(rel_path)
    if ".." in path_obj.parts or ".." in rel_path.replace("\\", "/").split("/"):
        raise ValueError(f"Path traversal detected in S3 object key: {raw_key!r}")

    resolved_target = target_dir.resolve()
    dest_path = (resolved_target / path_obj).resolve()

    try:
        dest_path.relative_to(resolved_target)
    except ValueError:
        raise ValueError(
            f"Destination path escapes target directory for S3 object key: {raw_key!r}"
        )

    if dest_path == resolved_target:
        raise ValueError(
            "Invalid target path matching root directory for S3 object key: "
            f"{raw_key!r}"
        )

    return dest_path


def download_s3_prefix(
    s3_client: Any, bucket: str, prefix: str, target_dir: Path
) -> int:
    """Download all objects under S3 prefix to local target directory."""
    target_dir.mkdir(parents=True, exist_ok=True)
    clean_prefix = prefix.strip().lstrip("/")
    if clean_prefix and not clean_prefix.endswith("/"):
        clean_prefix = f"{clean_prefix}/"

    paginator = s3_client.get_paginator("list_objects_v2")
    count = 0

    for page in paginator.paginate(Bucket=bucket, Prefix=clean_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            rel_path = key[len(clean_prefix) :].lstrip("/")
            if not rel_path or rel_path.endswith("/"):
                continue
            dest_file = _safe_s3_dest_path(target_dir, rel_path, key)
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info(
                "downloading_s3_object bucket=%s key=%s dest=%s", bucket, key, dest_file
            )
            s3_client.download_file(bucket, key, str(dest_file))
            count += 1

    return count


def upload_local_tree_to_s3(
    s3_client: Any, local_dir: Path, bucket: str, prefix: str
) -> int:
    """Upload all files from a local directory tree to S3 under prefix."""
    if not local_dir.exists():
        return 0

    count = 0
    clean_prefix = prefix.strip().lstrip("/")
    if clean_prefix and not clean_prefix.endswith("/"):
        clean_prefix = f"{clean_prefix}/"

    for file_path in local_dir.rglob("*"):
        if file_path.is_file():
            rel_path = file_path.relative_to(local_dir).as_posix()
            s3_key = f"{clean_prefix}{rel_path}"
            logger.info(
                "uploading_s3_object src=%s bucket=%s key=%s", file_path, bucket, s3_key
            )
            s3_client.upload_file(str(file_path), bucket, s3_key)
            count += 1

    return count


def publish_completed_run_to_s3(
    s3_client: Any,
    bucket: str,
    run_dir: Path,
    run_id: str,
    output_root: Path,
) -> None:
    """Publish verified completed run outputs to S3, uploading manifest.json LAST."""
    manifest_file = run_dir / "manifest.json"
    if not manifest_file.exists():
        raise RuntimeError(f"Manifest not found at: {manifest_file}")

    # 1. Upload all run artifacts EXCEPT the top-level completion manifest
    for file_path in sorted(run_dir.rglob("*")):
        if file_path.is_file() and file_path != manifest_file:
            rel_path = file_path.relative_to(run_dir).as_posix()
            s3_key = f"runs/{run_id}/{rel_path}"
            logger.info(
                "uploading_run_artifact src=%s bucket=%s key=%s",
                file_path,
                bucket,
                s3_key,
            )
            s3_client.upload_file(str(file_path), bucket, s3_key)

    # 2. Upload reports/ if present
    reports_dir = output_root / "reports"
    if reports_dir.exists():
        for file_path in sorted(reports_dir.rglob("*")):
            if file_path.is_file():
                rel_path = file_path.relative_to(reports_dir).as_posix()
                s3_key = f"reports/{rel_path}"
                logger.info(
                    "uploading_report src=%s bucket=%s key=%s",
                    file_path,
                    bucket,
                    s3_key,
                )
                s3_client.upload_file(str(file_path), bucket, s3_key)

    # 3. Upload cache/ if present
    stage_cache_dir = output_root / ".stage_cache"
    if stage_cache_dir.exists():
        for file_path in sorted(stage_cache_dir.rglob("*")):
            if file_path.is_file():
                rel_path = file_path.relative_to(stage_cache_dir).as_posix()
                s3_key = f"cache/{rel_path}"
                logger.info(
                    "uploading_cache_entry src=%s bucket=%s key=%s",
                    file_path,
                    bucket,
                    s3_key,
                )
                s3_client.upload_file(str(file_path), bucket, s3_key)

    # 4. Upload manifest.json LAST as the completion marker
    manifest_key = f"runs/{run_id}/manifest.json"
    logger.info(
        "uploading_manifest_last src=%s bucket=%s key=%s",
        manifest_file,
        bucket,
        manifest_key,
    )
    s3_client.upload_file(str(manifest_file), bucket, manifest_key)


def run_batch_job(config: BatchRunnerConfig, s3_client: Any = None) -> int:
    """Execute complete Batch analytical job lifecycle."""
    job_start = time.perf_counter()
    logger.info(
        "batch_job_started config=%s command=%s workspace=%s s3_bucket=%s",
        config.config_path,
        config.command,
        config.workspace_dir,
        config.s3_bucket,
    )

    # Ensure workspace directory structure exists
    config.workspace_dir.mkdir(parents=True, exist_ok=True)
    local_data_dir = config.workspace_dir / "data"
    local_data_dir.mkdir(parents=True, exist_ok=True)
    workspace_output_dir = (config.workspace_dir / "output").resolve()
    workspace_output_dir.mkdir(parents=True, exist_ok=True)
    local_cache_dir = workspace_output_dir / ".stage_cache"

    s3 = s3_client
    if (
        s3 is None
        and config.s3_bucket
        and not (config.skip_s3_download and config.skip_s3_upload)
    ):
        s3 = boto3.client("s3")

    # 1. Download raw inputs & cache from S3 if configured
    if s3 and config.s3_bucket and not config.skip_s3_download:
        logger.info("syncing_s3_inputs bucket=%s prefix=raw/", config.s3_bucket)
        downloaded_inputs = download_s3_prefix(
            s3, config.s3_bucket, "raw/", local_data_dir / "raw"
        )
        logger.info("downloaded_inputs_count count=%d", downloaded_inputs)

        logger.info("syncing_s3_cache bucket=%s prefix=cache/", config.s3_bucket)
        downloaded_cache = download_s3_prefix(
            s3, config.s3_bucket, "cache/", local_cache_dir
        )
        logger.info("downloaded_cache_count count=%d", downloaded_cache)

    # 2. Load and validate configuration, safely redirecting output_base_path
    cfg = load_config(config.config_path)
    cfg["output_base_path"] = str(workspace_output_dir)

    if config.dataset_id:
        datasets = cfg.get("datasets", []) + cfg.get("longitudinal_datasets", [])
        ds = next(
            (
                d
                for d in datasets
                if d.get("id") == config.dataset_id
                or d.get("month") == config.dataset_id
            ),
            None,
        )
        if ds:
            cfg.update(ds)
        else:
            logger.warning("dataset_id_not_found dataset_id=%s", config.dataset_id)

    if config.theme_provider:
        if "theme_provider" not in cfg or not isinstance(cfg["theme_provider"], dict):
            cfg["theme_provider"] = {}
        cfg["theme_provider"]["primary"] = config.theme_provider
        if config.theme_provider == "mock":
            if "theme" not in cfg or not isinstance(cfg["theme"], dict):
                cfg["theme"] = {}
            if "THEME_CLUSTERING_PROVIDER" not in os.environ:
                cfg["theme"].setdefault("clustering_provider", "mock")
            if "THEME_SIMILARITY_PROVIDER" not in os.environ:
                cfg["theme"].setdefault("similarity_provider", "mock")

    # Explicit embedding-provider environment variables act as operator runtime overrides
    if "theme" not in cfg or not isinstance(cfg["theme"], dict):
        cfg["theme"] = {}
    if "THEME_SIMILARITY_PROVIDER" in os.environ:
        sim_env = os.environ["THEME_SIMILARITY_PROVIDER"].strip()
        if sim_env:
            cfg["theme"]["similarity_provider"] = sim_env
    if "THEME_CLUSTERING_PROVIDER" in os.environ:
        clust_env = os.environ["THEME_CLUSTERING_PROVIDER"].strip()
        if clust_env:
            cfg["theme"]["clustering_provider"] = clust_env

    validate_run_config(cfg)

    if config.dry_run:
        logger.info(
            "batch_job_dry_run_complete config_valid=true output_base_path=%s",
            workspace_output_dir,
        )
        return 0

    # Ensure TEI services are ready before starting analytical pipeline flow
    wait_for_tei_services(cfg)

    # 3. Execute analytical pipeline flow
    logger.info(
        "executing_pipeline_flow command=%s output_root=%s",
        config.command,
        workspace_output_dir,
    )
    pipeline_start = time.perf_counter()

    if config.command == "run-evolution-pipeline":
        from src.orchestration.composition_flow import run_evolution_analysis_flow

        result = run_evolution_analysis_flow(config=cfg)
    elif config.command == "run-all":
        from src.orchestration.composition_flow import run_monthly_analysis_flow

        input_path = cfg.get("input_path", "data/telegram/03_2024.csv")
        ds_id = config.dataset_id or cfg.get("id", "default")
        result = run_monthly_analysis_flow(
            config=cfg,
            dataset_path=input_path,
            dataset_id=ds_id,
            run_topics=True,
            run_themes=True,
        )
    else:
        raise ValueError(f"Unsupported pipeline command: {config.command}")

    pipeline_duration = time.perf_counter() - pipeline_start
    run_id = result.context.pipeline_run_id
    output_root = Path(result.context.output_root)

    logger.info(
        "pipeline_execution_finished run_id=%s duration_seconds=%.2f output_root=%s",
        run_id,
        pipeline_duration,
        output_root,
    )

    # 4. Verify completed run manifest
    run_dir = output_root / "runs" / run_id
    manifest_path = run_dir / "manifest.json"

    if not manifest_path.exists():
        raise RuntimeError(
            f"Pipeline finished but run manifest not found at: {manifest_path}"
        )

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    if manifest_data.get("status") != "completed":
        status = manifest_data.get("status")
        failure = manifest_data.get("failure_stage")
        raise RuntimeError(
            f"Run manifest status is '{status}' (failure_stage={failure}). "
            "Refusing to publish incomplete run."
        )

    logger.info(
        "run_manifest_verified run_id=%s artifact_count=%d",
        run_id,
        len(manifest_data.get("artifacts", [])),
    )

    # 5. Publish completed artifacts to S3 with manifest.json uploaded LAST
    if s3 and config.s3_bucket and not config.skip_s3_upload:
        publish_completed_run_to_s3(
            s3_client=s3,
            bucket=config.s3_bucket,
            run_dir=run_dir,
            run_id=run_id,
            output_root=output_root,
        )

    total_duration = time.perf_counter() - job_start
    logger.info(
        "batch_job_completed_successfully run_id=%s total_duration_seconds=%.2f",
        run_id,
        total_duration,
    )
    return 0


def main() -> None:
    """CLI entrypoint for batch_runner."""
    setup_logging()
    try:
        config = parse_args()
        exit_code = run_batch_job(config)
        sys.exit(exit_code)
    except Exception as exc:
        logger.exception("batch_job_failed error=%s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
