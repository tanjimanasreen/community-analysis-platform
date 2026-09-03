#!/usr/bin/env python3
"""Dev Continuous Deployment (CD) helper script for community-analysis.

Orchestrates the safe, reproducible dev deployment pipeline:
1. Dev-only validation
2. Deterministic immutable TEI fingerprinting (reusing existing image when unchanged)
3. API and Analytics image build and push
4. Scoped CDK deployment of dev application stacks in dependency order (excluding CI/CD stack)
5. Frontend Vite build, S3 sync, and CloudFront cache invalidation
6. Bounded CD acceptance Batch run using the 3-container TEI job definition and THEME_PROVIDER=mock
7. Manifest verification (len(manifest['artifacts']))
8. Live API and frontend smoke testing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aws_cd")

APPROVED_DEV_APPLICATION_STACKS = [
    "community-analysis-dev-storage",
    "community-analysis-dev-registry",
    "community-analysis-dev-api",
    "community-analysis-dev-frontend",
    "community-analysis-dev-batch",
]


def validate_environment(environment: str) -> None:
    """Ensure deployment environment is strictly dev."""
    if environment != "dev":
        raise ValueError(
            f"Environment '{environment}' is forbidden. aws_cd.py currently supports "
            "'dev' only. Plan 098 governs production deployment."
        )


def validate_source_sha(source_sha: str) -> str:
    """Ensure source commit SHA is valid hex string (7 to 40 characters)."""
    clean_sha = source_sha.strip()
    if not (7 <= len(clean_sha) <= 40) or not re.fullmatch(r"[0-9a-fA-F]+", clean_sha):
        raise ValueError(
            f"Invalid source SHA '{source_sha}'. Expected a 7-40 character hexadecimal string."
        )
    return clean_sha.lower()


def compute_tei_fingerprint(dockerfile_path: Path | str = "Dockerfile.tei") -> str:
    """Compute deterministic immutable fingerprint of material TEI image build inputs.

    Includes the exact Dockerfile.tei content (which pins base image digest,
    huggingface_hub pin, model IDs, and model revision commits).
    """
    path = Path(dockerfile_path)
    if not path.is_file():
        raise FileNotFoundError(f"Material TEI input file not found: {dockerfile_path}")
    content = path.read_bytes()
    sha = hashlib.sha256(content).hexdigest()
    return f"tei-{sha[:16]}"


def check_ecr_image_exists(
    ecr_client: Any,
    repository_name: str,
    image_tag: str,
) -> bool:
    """Check if an image with the given tag already exists in the ECR repository."""
    try:
        response = ecr_client.describe_images(
            repositoryName=repository_name,
            imageIds=[{"imageTag": image_tag}],
        )
        return len(response.get("imageDetails", [])) > 0
    except ecr_client.exceptions.ImageNotFoundException:
        return False
    except ecr_client.exceptions.RepositoryNotFoundException:
        return False
    except Exception as e:
        logger.warning(
            "Could not check ECR image existence for %s:%s: %s",
            repository_name,
            image_tag,
            e,
        )
        return False


def run_command(
    cmd: list[str],
    *,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a shell command safely."""
    logger.info("Running: %s (cwd=%s)", " ".join(cmd), cwd or ".")
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    res = subprocess.run(cmd, cwd=cwd, env=merged_env)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {res.returncode}: {' '.join(cmd)}")
    return res


def cleanup_github_runner_docker_state(image_ref: str) -> None:
    """Remove exact pushed image and clear disposable builder cache under GitHub Actions."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return

    logger.info("Cleaning up local Docker state in GitHub Actions: %s", image_ref)
    run_command(["docker", "image", "rm", image_ref])
    run_command(["docker", "builder", "prune", "--force"])


def get_cloudformation_stack_outputs(
    cfn_client: Any,
    stack_name: str,
) -> dict[str, str]:
    """Retrieve all outputs for a CloudFormation stack."""
    response = cfn_client.describe_stacks(StackName=stack_name)
    stacks = response.get("Stacks", [])
    if not stacks:
        raise RuntimeError(f"Stack '{stack_name}' not found")
    outputs = {}
    for item in stacks[0].get("Outputs", []):
        outputs[item["OutputKey"]] = item["OutputValue"]
    return outputs


def deploy_cdk_application_stacks(
    *,
    stage: str,
    image_tag: str,
    tei_image_tag: str,
    infra_dir: Path | str = "infra",
    cdk_bin: str = "npx cdk",
) -> None:
    """Deploy dev application stacks in strict dependency order without touching cicd stack."""
    cmd = [
        "npx",
        "cdk",
        "deploy",
        *APPROVED_DEV_APPLICATION_STACKS,
        "--require-approval",
        "never",
        "-c",
        f"stage={stage}",
        "-c",
        f"image_tag={image_tag}",
        "-c",
        f"batch_image_tag={image_tag}",
        "-c",
        f"tei_analytics_image_tag={image_tag}",
        "-c",
        f"tei_image_tag={tei_image_tag}",
    ]
    run_command(cmd, cwd=infra_dir)


def build_and_deploy_frontend(
    *,
    frontend_dir: Path | str = "frontend",
    bucket_name: str,
    distribution_id: str,
) -> None:
    """Build Vite frontend assets, sync to S3, and invalidate CloudFront distribution."""
    logger.info("Building frontend distribution in %s...", frontend_dir)
    run_command(["npm", "run", "build"], cwd=frontend_dir)

    dist_dir = Path(frontend_dir) / "dist"
    if not dist_dir.is_dir():
        raise RuntimeError(f"Frontend dist directory '{dist_dir}' not found after build")

    logger.info("Syncing frontend assets to s3://%s...", bucket_name)
    run_command(["aws", "s3", "sync", str(dist_dir), f"s3://{bucket_name}", "--delete"])

    logger.info("Invalidating CloudFront distribution '%s'...", distribution_id)
    run_command(
        [
            "aws",
            "cloudfront",
            "create-invalidation",
            "--distribution-id",
            distribution_id,
            "--paths",
            "/*",
        ]
    )


def smoke_test_frontend(
    cloudfront_domain: str,
    *,
    timeout: float = 15.0,
) -> None:
    """Verify frontend delivery via CloudFront (HTTP 200 and root element)."""
    url = f"https://{cloudfront_domain}/"
    logger.info("Smoke testing frontend delivery: %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "CommunityAnalysis-CD-Smoke/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        assert resp.status == 200, f"Frontend returned HTTP {resp.status} (expected 200)"
        html = resp.read().decode("utf-8")
        assert '<div id="root">' in html or 'id="root"' in html, "Frontend HTML does not contain root element"
    logger.info("Frontend smoke test passed: HTTP 200 OK with valid root container.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CD deployment helper for community-analysis dev.")
    parser.add_argument("--environment", default="dev", help="Deployment environment (must be 'dev')")
    parser.add_argument("--source-sha", required=True, help="Git commit SHA being deployed")
    parser.add_argument(
        "--acceptance-config",
        default="tests/configs/test_evolution.yml",
        help="Config path for CD acceptance run",
    )
    parser.add_argument(
        "--acceptance-theme-provider",
        default="mock",
        help="Theme provider for CD acceptance run (default: mock)",
    )
    parser.add_argument("--region", default="us-east-1", help="AWS Region (default: us-east-1)")
    parser.add_argument("--skip-image-build", action="store_true", help="Skip Docker build and push")
    parser.add_argument("--skip-deploy", action="store_true", help="Skip CDK deployment")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend build and sync")
    parser.add_argument("--skip-acceptance", action="store_true", help="Skip CD acceptance Batch run")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip live API and frontend smoke tests")

    args = parser.parse_args(argv)

    validate_environment(args.environment)
    clean_sha = validate_source_sha(args.source_sha)
    tei_fingerprint = compute_tei_fingerprint("Dockerfile.tei")

    logger.info("Source SHA: %s", clean_sha)
    logger.info("Material TEI build fingerprint: %s", tei_fingerprint)

    import boto3

    ecr_client = boto3.client("ecr", region_name=args.region)
    cfn_client = boto3.client("cloudformation", region_name=args.region)
    sts_client = boto3.client("sts", region_name=args.region)
    batch_client = boto3.client("batch", region_name=args.region)
    logs_client = boto3.client("logs", region_name=args.region)
    s3_client = boto3.client("s3", region_name=args.region)

    account_id = sts_client.get_caller_identity()["Account"]
    ecr_registry = f"{account_id}.dkr.ecr.{args.region}.amazonaws.com"

    # 1. Build & Push Images (ECR authentication is handled externally by cd.yml)
    if not args.skip_image_build:
        # 1a. TEI Image (check if exact fingerprint exists)
        tei_repo = f"community-analysis-{args.environment}-tei"
        tei_image_ref = f"{ecr_registry}/{tei_repo}:{tei_fingerprint}"
        if check_ecr_image_exists(ecr_client, tei_repo, tei_fingerprint):
            logger.info(
                "TEI image %s:%s already exists in ECR. Reusing existing image without rebuilding.",
                tei_repo,
                tei_fingerprint,
            )
        else:
            logger.info("Building TEI image %s:%s...", tei_repo, tei_fingerprint)
            run_command(
                [
                    "docker",
                    "build",
                    "--platform",
                    "linux/arm64",
                    "-t",
                    tei_image_ref,
                    "-f",
                    "Dockerfile.tei",
                    ".",
                ]
            )
            run_command(["docker", "push", tei_image_ref])
            cleanup_github_runner_docker_state(tei_image_ref)

        # 1b. API Image
        api_repo = f"community-analysis-{args.environment}-api"
        api_image_ref = f"{ecr_registry}/{api_repo}:{clean_sha}"
        logger.info("Building API image %s:%s...", api_repo, clean_sha)
        run_command(
            [
                "docker",
                "build",
                "--platform",
                "linux/arm64",
                "-t",
                api_image_ref,
                "-f",
                "Dockerfile.api",
                ".",
            ]
        )
        run_command(["docker", "push", api_image_ref])
        cleanup_github_runner_docker_state(api_image_ref)

        # 1c. Analytics Image
        analytics_repo = f"community-analysis-{args.environment}-analytics"
        analytics_image_ref = f"{ecr_registry}/{analytics_repo}:{clean_sha}"
        logger.info("Building Analytics image %s:%s...", analytics_repo, clean_sha)
        run_command(
            [
                "docker",
                "build",
                "--platform",
                "linux/arm64",
                "-t",
                analytics_image_ref,
                "-f",
                "Dockerfile.analytics",
                ".",
            ]
        )
        run_command(["docker", "push", analytics_image_ref])
        cleanup_github_runner_docker_state(analytics_image_ref)

    # 2. Deploy CDK application stacks
    if not args.skip_deploy:
        logger.info("Deploying CDK application stacks for %s...", args.environment)
        deploy_cdk_application_stacks(
            stage=args.environment,
            image_tag=clean_sha,
            tei_image_tag=tei_fingerprint,
        )

    # Gather stack outputs
    api_stack_name = f"community-analysis-{args.environment}-api"
    frontend_stack_name = f"community-analysis-{args.environment}-frontend"
    storage_stack_name = f"community-analysis-{args.environment}-storage"

    api_outputs = get_cloudformation_stack_outputs(cfn_client, api_stack_name)
    frontend_outputs = get_cloudformation_stack_outputs(cfn_client, frontend_stack_name)

    api_endpoint = api_outputs.get("ApiEndpoint", "")
    user_pool_id = api_outputs.get("CognitoUserPoolId", "")
    app_client_id = api_outputs.get("CognitoAppClientId", "")

    frontend_bucket = frontend_outputs.get("FrontendBucketName", "")
    distribution_id = frontend_outputs.get("CloudFrontDistributionId", "")
    cloudfront_domain = frontend_outputs.get("CloudFrontDomainName", "")
    data_bucket = f"community-analysis-{args.environment}-{account_id}-{args.region}-data"

    # 3. Frontend Build & Deploy
    if not args.skip_frontend and frontend_bucket and distribution_id:
        build_and_deploy_frontend(
            bucket_name=frontend_bucket,
            distribution_id=distribution_id,
        )

    # 4. CD Acceptance Batch Run
    accepted_run_id = None
    if not args.skip_acceptance:
        from scripts.aws_run_evolution import (
            discover_run_id_from_batch_job,
            verify_completed_manifest,
            wait_for_batch_job,
        )

        logger.info(
            "Submitting CD acceptance Batch job (config=%s, provider=%s)...",
            args.acceptance_config,
            args.acceptance_theme_provider,
        )
        queue = f"community-analysis-{args.environment}-queue"
        job_def = f"community-analysis-{args.environment}-analytics-tei-job"
        job_name = f"community-analysis-{args.environment}-acceptance-{time.strftime('%Y%m%d%H%M%S')}"

        container_overrides = {
            "environment": [
                {"name": "CONFIG_PATH", "value": args.acceptance_config},
                {"name": "PIPELINE_COMMAND", "value": "run-evolution-pipeline"},
                {"name": "THEME_PROVIDER", "value": args.acceptance_theme_provider},
            ]
        }
        res = batch_client.submit_job(
            jobName=job_name,
            jobQueue=queue,
            jobDefinition=job_def,
            containerOverrides=container_overrides,
        )
        job_id = res["jobId"]
        wait_for_batch_job(batch_client, job_id, timeout_seconds=7200.0)

        # Discover exact run ID from job's CloudWatch logs and verify canonical manifest & artifacts
        log_group_name = f"/aws/batch/job/community-analysis-{args.environment}"
        accepted_run_id = discover_run_id_from_batch_job(
            batch_client,
            logs_client,
            job_id,
            log_group_name,
        )
        verify_completed_manifest(s3_client, data_bucket, accepted_run_id)

    # 5. Live Smoke Tests
    if not args.skip_smoke:
        if accepted_run_id and api_endpoint:
            from scripts.smoke_live_api import main as smoke_main

            logger.info("Executing live API smoke tests against %s (run_id: %s)...", api_endpoint, accepted_run_id)
            smoke_args = [
                "--api-url",
                api_endpoint,
                "--run-id",
                accepted_run_id,
                "--user-pool-id",
                user_pool_id,
                "--client-id",
                app_client_id,
                "--region",
                args.region,
            ]
            smoke_exit = smoke_main(smoke_args)
            if smoke_exit != 0:
                raise RuntimeError(f"Live API smoke testing failed with exit code {smoke_exit}")

        if cloudfront_domain:
            smoke_test_frontend(cloudfront_domain)

    logger.info("CD deployment and acceptance passed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
