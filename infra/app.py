#!/usr/bin/env python3
"""AWS CDK App entry point for community-analysis infrastructure."""

import os
import aws_cdk as cdk
from community_analysis_infra.api_stack import ApiStack
from community_analysis_infra.baseline_stack import CommunityAnalysisBaselineStack
from community_analysis_infra.batch_stack import BatchStack
from community_analysis_infra.config import get_stage_config
from community_analysis_infra.frontend_stack import FrontendStack
from community_analysis_infra.registry_stack import RegistryStack
from community_analysis_infra.storage_stack import StorageStack

app = cdk.App()

# Resolve stage from CDK context (-c stage=...) or environment variable (STAGE=...).
# Explicit stage is required; silent defaulting to "dev" or "prod" is forbidden.
raw_stage = app.node.try_get_context("stage") or os.environ.get("STAGE")
stage_config = get_stage_config(raw_stage)

# Baseline stack for synthesis and configuration verification
baseline_stack_name = stage_config.format_stack_name("baseline")
CommunityAnalysisBaselineStack(
    app,
    baseline_stack_name,
    env=cdk.Environment(
        account=stage_config.account,
        region=stage_config.region,
    ),
    description=f"Baseline infrastructure verification stack for {stage_config.project_name} ({stage_config.stage_name})",
)

# Storage stack containing analytical data and artifact S3 bucket
storage_stack_name = stage_config.format_stack_name("storage")
storage_stack = StorageStack(
    app,
    storage_stack_name,
    stage_config=stage_config,
    env=cdk.Environment(
        account=stage_config.account,
        region=stage_config.region,
    ),
    description=f"Storage infrastructure for {stage_config.project_name} ({stage_config.stage_name})",
)

# Registry stack containing private ECR repository for API container images
registry_stack_name = stage_config.format_stack_name("registry")
registry_stack = RegistryStack(
    app,
    registry_stack_name,
    stage_config=stage_config,
    env=cdk.Environment(
        account=stage_config.account,
        region=stage_config.region,
    ),
    description=f"Container registry infrastructure for {stage_config.project_name} ({stage_config.stage_name})",
)

# Check whether synthesis is restricted to CI/CD bootstrap stack only
raw_target = app.node.try_get_context("target") or app.node.try_get_context("stack")
raw_cicd_only = app.node.try_get_context("cicd_only") or os.environ.get("CICD_ONLY")
cicd_only = (
    str(raw_cicd_only).strip().lower() in ("true", "1", "yes")
    or str(raw_target).strip().lower() in ("cicd", "community-analysis-dev-cicd")
)

if not cicd_only:
    # Resolve explicit image_tag for ApiStack (-c image_tag=... or IMAGE_TAG=...)
    raw_image_tag = app.node.try_get_context("image_tag") or os.environ.get("IMAGE_TAG")
    if not raw_image_tag or not str(raw_image_tag).strip():
        raise ValueError(
            "image_tag is required. Pass via CDK context: -c image_tag=<GIT_SHA> or environment: IMAGE_TAG=<GIT_SHA>"
        )
    image_tag = str(raw_image_tag).strip()

    # API stack containing authenticated Lambda container and API Gateway HTTP API
    api_stack_name = stage_config.format_stack_name("api")
    api_stack = ApiStack(
        app,
        api_stack_name,
        stage_config=stage_config,
        bucket=storage_stack.bucket,
        repository=registry_stack.repository,
        image_tag=image_tag,
        env=cdk.Environment(
            account=stage_config.account,
            region=stage_config.region,
        ),
        description=f"Authenticated API serving infrastructure for {stage_config.project_name} ({stage_config.stage_name})",
    )

    # Frontend stack containing private S3 bucket, CloudFront distribution, and browser Cognito client
    frontend_stack_name = stage_config.format_stack_name("frontend")
    FrontendStack(
        app,
        frontend_stack_name,
        stage_config=stage_config,
        http_api=api_stack.http_api,
        user_pool=api_stack.user_pool,
        api_app_client=api_stack.app_client,
        lambda_function=api_stack.lambda_function,
        env=cdk.Environment(
            account=stage_config.account,
            region=stage_config.region,
        ),
        description=f"Frontend hosting, CloudFront CDN, and browser auth infrastructure for {stage_config.project_name} ({stage_config.stage_name})",
    )

    # Resolve optional batch_image_tag for BatchStack (-c batch_image_tag=... or BATCH_IMAGE_TAG=...)
    raw_batch_image_tag = app.node.try_get_context("batch_image_tag") or os.environ.get(
        "BATCH_IMAGE_TAG"
    )
    if raw_batch_image_tag and str(raw_batch_image_tag).strip():
        batch_image_tag = str(raw_batch_image_tag).strip()
        raw_tei_analytics_image_tag = (
            app.node.try_get_context("tei_analytics_image_tag")
            or os.environ.get("TEI_ANALYTICS_IMAGE_TAG")
        )
        if not raw_tei_analytics_image_tag or not str(raw_tei_analytics_image_tag).strip():
            raise ValueError(
                "tei_analytics_image_tag (-c tei_analytics_image_tag=... or env TEI_ANALYTICS_IMAGE_TAG) "
                "is required when synthesizing BatchStack."
            )
        tei_analytics_image_tag = str(raw_tei_analytics_image_tag).strip()

        raw_tei_image_tag = app.node.try_get_context("tei_image_tag") or os.environ.get(
            "TEI_IMAGE_TAG"
        )
        if not raw_tei_image_tag or not str(raw_tei_image_tag).strip():
            raise ValueError(
                "tei_image_tag (-c tei_image_tag=... or env TEI_IMAGE_TAG) "
                "is required when synthesizing BatchStack."
            )
        tei_image_tag = str(raw_tei_image_tag).strip()

        batch_stack_name = stage_config.format_stack_name("batch")
        BatchStack(
            app,
            batch_stack_name,
            stage_config=stage_config,
            bucket=storage_stack.bucket,
            batch_image_tag=batch_image_tag,
            tei_analytics_image_tag=tei_analytics_image_tag,
            tei_image_tag=tei_image_tag,
            env=cdk.Environment(
                account=stage_config.account,
                region=stage_config.region,
            ),
            description=f"AWS Batch analytical compute infrastructure for {stage_config.project_name} ({stage_config.stage_name})",
        )

# CI/CD OIDC Identity and Roles Stack (dev only, for GitHub Actions deployment and evolution runner)
if stage_config.stage_name == "dev":
    raw_github_oidc_subject = app.node.try_get_context(
        "github_oidc_subject"
    ) or os.environ.get("GITHUB_OIDC_SUBJECT")
    github_oidc_subject = (
        str(raw_github_oidc_subject).strip() if raw_github_oidc_subject else None
    )

    # When cicd_only is requested, github_oidc_subject is mandatory (fail closed)
    if cicd_only and not github_oidc_subject:
        from community_analysis_infra.cicd_stack import validate_oidc_subject

        validate_oidc_subject(None)

    # Instantiate CicdStack if cicd_only is active OR if an explicit OIDC subject is supplied
    if cicd_only or github_oidc_subject:
        from community_analysis_infra.cicd_stack import CicdStack

        raw_use_existing_provider = app.node.try_get_context(
            "use_existing_oidc_provider"
        ) or os.environ.get("USE_EXISTING_OIDC_PROVIDER")
        use_existing_oidc_provider = str(raw_use_existing_provider).strip().lower() in (
            "true",
            "1",
            "yes",
        )
        raw_oidc_provider_arn = app.node.try_get_context(
            "oidc_provider_arn"
        ) or os.environ.get("OIDC_PROVIDER_ARN")
        oidc_provider_arn = (
            str(raw_oidc_provider_arn).strip() if raw_oidc_provider_arn else None
        )

        cicd_stack_name = stage_config.format_stack_name("cicd")
        CicdStack(
            app,
            cicd_stack_name,
            stage_config=stage_config,
            use_existing_oidc_provider=use_existing_oidc_provider,
            oidc_provider_arn=oidc_provider_arn,
            github_oidc_subject=github_oidc_subject,
            env=cdk.Environment(
                account=stage_config.account,
                region=stage_config.region,
            ),
            description=f"GitHub Actions OIDC and CI/CD identity infrastructure for {stage_config.project_name} ({stage_config.stage_name})",
        )

# Apply deterministic standard tags across all constructs in the App
for key, value in stage_config.tags.items():
    cdk.Tags.of(app).add(key, value)

app.synth()
