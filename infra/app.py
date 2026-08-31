#!/usr/bin/env python3
"""AWS CDK App entry point for community-analysis infrastructure."""

import os
import aws_cdk as cdk
from community_analysis_infra.api_stack import ApiStack
from community_analysis_infra.baseline_stack import CommunityAnalysisBaselineStack
from community_analysis_infra.config import get_stage_config
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

# Resolve explicit image_tag for ApiStack (-c image_tag=... or IMAGE_TAG=...)
raw_image_tag = app.node.try_get_context("image_tag") or os.environ.get("IMAGE_TAG")
if not raw_image_tag or not str(raw_image_tag).strip():
    raise ValueError(
        "image_tag is required. Pass via CDK context: -c image_tag=<GIT_SHA> or environment: IMAGE_TAG=<GIT_SHA>"
    )
image_tag = str(raw_image_tag).strip()

# API stack containing authenticated Lambda container and API Gateway HTTP API
api_stack_name = stage_config.format_stack_name("api")
ApiStack(
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

# Apply deterministic standard tags across all constructs in the App
for key, value in stage_config.tags.items():
    cdk.Tags.of(app).add(key, value)

app.synth()
