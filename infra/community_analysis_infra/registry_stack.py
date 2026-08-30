"""Registry stack definition for community-analysis API container images."""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_ecr as ecr
from constructs import Construct
from community_analysis_infra.config import StageConfig


class RegistryStack(cdk.Stack):
    """Container registry infrastructure stack.

    Provisions a single private, encrypted ECR repository for storing
    immutable API container images.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        stage_config: StageConfig,
        env: cdk.Environment | None = None,
        description: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            scope,
            construct_id,
            env=env,
            description=description,
            **kwargs,
        )

        self.stage_config = stage_config

        # Deterministic repository naming: <project>-<stage>-api
        repository_name = f"{stage_config.project_name}-{stage_config.stage_name}-api"

        is_dev = stage_config.stage_name == "dev"
        removal_policy = cdk.RemovalPolicy.DESTROY if is_dev else cdk.RemovalPolicy.RETAIN
        empty_on_delete = True if is_dev else False

        # Private ECR repository with immutable tags, AES256 encryption, and untagged lifecycle cleanup
        self.repository = ecr.Repository(
            self,
            "ApiRepository",
            repository_name=repository_name,
            image_tag_mutability=ecr.TagMutability.IMMUTABLE,
            encryption=ecr.RepositoryEncryption.AES_256,
            removal_policy=removal_policy,
            empty_on_delete=empty_on_delete,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Expire untagged images older than 1 day",
                    tag_status=ecr.TagStatus.UNTAGGED,
                    max_image_age=cdk.Duration.days(1),
                ),
            ],
        )

        # CloudFormation outputs for deployment and CI reference
        cdk.CfnOutput(
            self,
            "RepositoryName",
            value=self.repository.repository_name,
            description="Name of the API container repository",
        )

        cdk.CfnOutput(
            self,
            "RepositoryArn",
            value=self.repository.repository_arn,
            description="ARN of the API container repository",
        )

        cdk.CfnOutput(
            self,
            "RepositoryUri",
            value=self.repository.repository_uri,
            description="URI of the API container repository",
        )
