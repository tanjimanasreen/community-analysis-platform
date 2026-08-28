"""Storage stack definition for community-analysis analytical artifacts and datasets."""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_s3 as s3
from constructs import Construct
from community_analysis_infra.config import StageConfig


class StorageStack(cdk.Stack):
    """Storage infrastructure stack.

    Provisions a single private, encrypted S3 bucket for storing
    raw inputs, longitudinal run bundles, stage caches, and reports.
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

        # Deterministic bucket naming: <project>-<stage>-<account>-<region>-data
        # Uses CloudFormation pseudo-parameters / tokens safely
        bucket_name = (
            f"{stage_config.project_name}-{stage_config.stage_name}-"
            f"{cdk.Aws.ACCOUNT_ID}-{cdk.Aws.REGION}-data"
        )

        # Single private S3 bucket with S3-managed encryption and blocked public access
        self.bucket = s3.Bucket(
            self,
            "DataBucket",
            bucket_name=bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=False,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            auto_delete_objects=False,
        )

        # Minimal CloudFormation outputs for downstream reference
        cdk.CfnOutput(
            self,
            "BucketName",
            value=self.bucket.bucket_name,
            description="Name of the primary analytical data and artifact bucket",
        )

        cdk.CfnOutput(
            self,
            "BucketArn",
            value=self.bucket.bucket_arn,
            description="ARN of the primary analytical data and artifact bucket",
        )
