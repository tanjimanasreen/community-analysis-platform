#!/usr/bin/env python3
"""Operational evolution runner for AWS Batch.

Submits, observes, and verifies canonical evolution runs without modifying
infrastructure, building images, or altering analytical configs.

Correlates the exact submitted Batch job to its exact CloudWatch log stream,
extracts the exact analytical run_id emitted by the batch_runner, and verifies
all canonical artifacts in the completed run manifest.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aws_run_evolution")

APPROVED_CANONICAL_CONFIGS = {
    "configs/telegram/forwarded_message_evolution.yml",
    "configs/twitter/reply_evolution.yml",
    "configs/twitter/retweet_quote_evolution.yml",
}


def validate_environment(environment: str) -> None:
    """Ensure runtime environment is strictly dev."""
    if environment != "dev":
        raise ValueError(
            f"Environment '{environment}' is forbidden. aws_run_evolution.py currently supports "
            "'dev' only. Plan 098 governs production."
        )


def validate_canonical_config(config_path: str | Path) -> str:
    """Ensure requested configuration is strictly one of the approved canonical evolution configs."""
    normalized = str(config_path).strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]

    if normalized not in APPROVED_CANONICAL_CONFIGS:
        raise ValueError(
            f"Configuration '{config_path}' is not an approved canonical evolution config. "
            f"Approved configs are: {sorted(APPROVED_CANONICAL_CONFIGS)}"
        )
    return normalized


def submit_evolution_batch_job(
    batch_client: Any,
    *,
    environment: str,
    config_path: str,
    job_name_prefix: str = "community-analysis",
    job_queue: str | None = None,
    job_definition: str | None = None,
) -> tuple[str, str]:
    """Submit the evolution pipeline Batch job."""
    queue = job_queue or f"{job_name_prefix}-{environment}-queue"
    job_def = job_definition or f"{job_name_prefix}-{environment}-analytics-tei-job"
    sanitized_config = re.sub(r"[^a-zA-Z0-9-]", "-", Path(config_path).stem)
    timestamp = time.strftime("%Y%m%d%H%M%S")
    job_name = f"{job_name_prefix}-{environment}-{sanitized_config}-{timestamp}"

    container_overrides = {
        "environment": [
            {"name": "CONFIG_PATH", "value": config_path},
            {"name": "PIPELINE_COMMAND", "value": "run-evolution-pipeline"},
        ]
    }

    logger.info(
        "Submitting Batch job '%s' to queue '%s' using job definition '%s'...",
        job_name,
        queue,
        job_def,
    )
    response = batch_client.submit_job(
        jobName=job_name,
        jobQueue=queue,
        jobDefinition=job_def,
        containerOverrides=container_overrides,
    )
    job_id = response["jobId"]
    logger.info("Batch job submitted successfully: jobId=%s", job_id)
    return job_name, job_id


def wait_for_batch_job(
    batch_client: Any,
    job_id: str,
    *,
    poll_interval_seconds: float = 15.0,
    timeout_seconds: float = 7200.0,
) -> str:
    """Poll AWS Batch job until terminal state (SUCCEEDED or FAILED)."""
    started_at = time.time()
    last_status = None

    while True:
        elapsed = time.time() - started_at
        if elapsed > timeout_seconds:
            raise TimeoutError(f"Job {job_id} exceeded timeout of {timeout_seconds}s (elapsed: {elapsed:.1f}s)")

        response = batch_client.describe_jobs(jobs=[job_id])
        jobs = response.get("jobs", [])
        if not jobs:
            raise RuntimeError(f"Job {job_id} not found in Batch describe_jobs response")

        job_info = jobs[0]
        status = job_info.get("status")

        if status != last_status:
            logger.info("Job %s status changed: %s (elapsed: %.1fs)", job_id, status, elapsed)
            last_status = status

        if status == "SUCCEEDED":
            logger.info("Job %s SUCCEEDED in %.1fs", job_id, elapsed)
            return status
        elif status == "FAILED":
            reason = job_info.get("statusReason", "No reason provided")
            logger.error("Job %s FAILED: %s", job_id, reason)
            raise RuntimeError(f"Batch job {job_id} failed: {reason}")

        time.sleep(poll_interval_seconds)


def get_batch_job_log_stream_name(
    job_info: dict[str, Any],
    container_name: str = "analytics",
) -> str | None:
    """Extract CloudWatch log stream name for the specified container from Batch job description."""
    # 1. Multi-container ecsProperties (Fargate task properties)
    for task_prop in job_info.get("ecsProperties", {}).get("taskProperties", []):
        for c in task_prop.get("containers", []):
            if c.get("name") == container_name and c.get("logStreamName"):
                return c["logStreamName"]

    # 2. Multi-container top-level containers list
    for c in job_info.get("containers", []):
        if c.get("name") == container_name and c.get("logStreamName"):
            return c["logStreamName"]

    # 3. Single-container top-level container
    container = job_info.get("container", {})
    if container.get("logStreamName"):
        return container["logStreamName"]

    # 4. Check attempts (latest attempt)
    attempts = job_info.get("attempts", [])
    if attempts:
        latest_attempt = attempts[-1]
        for task_prop in latest_attempt.get("ecsProperties", {}).get("taskProperties", []):
            for c in task_prop.get("containers", []):
                if c.get("name") == container_name and c.get("logStreamName"):
                    return c["logStreamName"]
        for c in latest_attempt.get("containers", []):
            if c.get("name") == container_name and c.get("logStreamName"):
                return c["logStreamName"]
        if latest_attempt.get("container", {}).get("logStreamName"):
            return latest_attempt["container"]["logStreamName"]

    return None


def extract_run_id_from_log_events(events: list[dict[str, Any]]) -> str:
    """Parse CloudWatch log events and extract the exact analytical run_id emitted by batch_runner.

    Fails closed if no run_id is found or if conflicting run_ids are observed.
    """
    patterns = [
        re.compile(r"batch_job_completed_successfully\s+run_id=([a-zA-Z0-9_.-]+)"),
        re.compile(r"run_manifest_verified\s+run_id=([a-zA-Z0-9_.-]+)"),
        re.compile(r"pipeline_execution_finished\s+run_id=([a-zA-Z0-9_.-]+)"),
        re.compile(r"uploading_manifest_last.*runs/([a-zA-Z0-9_.-]+)/manifest\.json"),
        re.compile(r'"run_id":\s*"([a-zA-Z0-9_.-]+)"'),
    ]

    discovered_run_ids: set[str] = set()
    for event in events:
        msg = event.get("message", "")
        for pat in patterns:
            for match in pat.finditer(msg):
                discovered_run_ids.add(match.group(1))

    if not discovered_run_ids:
        raise RuntimeError(
            "Could not extract analytical run_id from Batch job CloudWatch logs. "
            "No matching completion or manifest log events found."
        )

    if len(discovered_run_ids) > 1:
        raise RuntimeError(
            f"Conflicting run_ids discovered in Batch job CloudWatch logs: {sorted(discovered_run_ids)}. "
            "Refusing to proceed with ambiguous run identity."
        )

    run_id = next(iter(discovered_run_ids))
    logger.info("Extracted exact run_id '%s' from Batch job CloudWatch logs.", run_id)
    return run_id


def discover_run_id_from_batch_job(
    batch_client: Any,
    logs_client: Any,
    job_id: str,
    log_group_name: str,
) -> str:
    """Deterministically discover the exact analytical run_id from a Batch job's CloudWatch log stream."""
    logger.info("Describing Batch job %s to locate analytics container log stream...", job_id)
    response = batch_client.describe_jobs(jobs=[job_id])
    jobs = response.get("jobs", [])
    if not jobs:
        raise RuntimeError(f"Batch job {job_id} not found in describe_jobs response")

    job_info = jobs[0]
    log_stream = get_batch_job_log_stream_name(job_info, container_name="analytics")
    if not log_stream:
        raise RuntimeError(
            f"Could not locate CloudWatch log stream name for 'analytics' container in Batch job {job_id}"
        )

    logger.info("Reading log events from group '%s', stream '%s'...", log_group_name, log_stream)
    events: list[dict[str, Any]] = []
    next_token = None

    while True:
        kwargs: dict[str, Any] = {
            "logGroupName": log_group_name,
            "logStreamName": log_stream,
            "startFromHead": True,
        }
        if next_token:
            kwargs["nextToken"] = next_token

        res = logs_client.get_log_events(**kwargs)
        batch_events = res.get("events", [])
        events.extend(batch_events)

        token = res.get("nextForwardToken")
        if not token or token == next_token:
            break
        next_token = token
        # Prevent runaway log fetch in massive streams
        if len(events) >= 5000:
            break

    return extract_run_id_from_log_events(events)


def verify_completed_manifest(
    s3_client: Any,
    bucket_name: str,
    run_id: str,
) -> dict[str, Any]:
    """Verify that runs/<run_id>/manifest.json exists, status is completed,
    and all canonical artifacts recorded in the manifest exist in S3.

    Follows Plan 095 verified semantics: canonical artifact count = len(manifest['artifacts']).
    Extra objects in S3 do not affect verification.
    """
    manifest_key = f"runs/{run_id}/manifest.json"
    logger.info("Fetching manifest from s3://%s/%s...", bucket_name, manifest_key)

    response = s3_client.get_object(Bucket=bucket_name, Key=manifest_key)
    manifest_bytes = response["Body"].read()
    manifest = json.loads(manifest_bytes.decode("utf-8"))

    # Validate status
    status = manifest.get("status")
    if status != "completed":
        raise ValueError(f"Expected manifest status 'completed', got '{status}'")

    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("Manifest artifacts must be a list")
    if len(artifacts) == 0:
        raise ValueError("Manifest contains 0 artifacts")

    logger.info("Verifying %d canonical artifacts recorded in manifest...", len(artifacts))
    for item in artifacts:
        if not isinstance(item, dict):
            raise ValueError(f"Malformed artifact entry in manifest: {item}")
        rel_path = item.get("path")
        if not rel_path:
            raise ValueError(f"Artifact entry missing 'path': {item}")

        s3_key = f"runs/{run_id}/{rel_path.lstrip('/')}"
        try:
            head_resp = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        except Exception as e:
            raise FileNotFoundError(
                f"Canonical artifact from manifest not found in S3: s3://{bucket_name}/{s3_key}"
            ) from e

        expected_size = item.get("byte_size")
        if expected_size is not None:
            actual_size = head_resp.get("ContentLength")
            if actual_size is not None and actual_size != expected_size:
                raise ValueError(
                    f"Size mismatch for canonical artifact s3://{bucket_name}/{s3_key}: "
                    f"manifest expects {expected_size} bytes, got {actual_size} bytes"
                )

    logger.info(
        "Manifest and %d canonical artifacts verified successfully for run '%s'.",
        len(artifacts),
        run_id,
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run and verify canonical evolution Batch job.")
    parser.add_argument("--environment", default="dev", help="Runtime environment (must be 'dev')")
    parser.add_argument(
        "--config-path",
        required=True,
        help="Path to approved canonical evolution config",
    )
    parser.add_argument("--wait", action="store_true", default=True, help="Wait for job completion")
    parser.add_argument("--verify-manifest", action="store_true", default=True, help="Verify run manifest and artifacts in S3")
    parser.add_argument("--s3-bucket", help="S3 bucket name (auto-discovered from account/region if omitted)")
    parser.add_argument("--region", default="us-east-1", help="AWS Region (default: us-east-1)")
    parser.add_argument("--poll-interval", type=float, default=15.0, help="Poll interval in seconds")
    parser.add_argument("--timeout", type=float, default=7200.0, help="Timeout in seconds")

    args = parser.parse_args(argv)

    validate_environment(args.environment)
    canonical_config = validate_canonical_config(args.config_path)

    import boto3

    batch_client = boto3.client("batch", region_name=args.region)
    logs_client = boto3.client("logs", region_name=args.region)
    s3_client = boto3.client("s3", region_name=args.region)
    sts_client = boto3.client("sts", region_name=args.region)

    account_id = sts_client.get_caller_identity()["Account"]
    bucket_name = args.s3_bucket or f"community-analysis-{args.environment}-{account_id}-{args.region}-data"
    log_group_name = f"/aws/batch/job/community-analysis-{args.environment}"

    job_name, job_id = submit_evolution_batch_job(
        batch_client,
        environment=args.environment,
        config_path=canonical_config,
    )

    if args.wait:
        wait_for_batch_job(
            batch_client,
            job_id,
            poll_interval_seconds=args.poll_interval,
            timeout_seconds=args.timeout,
        )

    if args.verify_manifest:
        run_id = discover_run_id_from_batch_job(
            batch_client,
            logs_client,
            job_id,
            log_group_name,
        )
        verify_completed_manifest(s3_client, bucket_name, run_id)

    logger.info("aws_run_evolution completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
