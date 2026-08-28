"""Unit tests for StorageStack and S3 bucket security and configuration."""

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Match, Template
from community_analysis_infra.config import get_stage_config
from community_analysis_infra.storage_stack import StorageStack


@pytest.fixture
def dev_storage_template() -> Template:
    app = cdk.App(context={"stage": "dev"})
    stage_config = get_stage_config("dev")
    stack = StorageStack(
        app,
        stage_config.format_stack_name("storage"),
        stage_config=stage_config,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)
    return Template.from_stack(stack)


@pytest.fixture
def prod_storage_template() -> Template:
    app = cdk.App(context={"stage": "prod"})
    stage_config = get_stage_config("prod")
    stack = StorageStack(
        app,
        stage_config.format_stack_name("storage"),
        stage_config=stage_config,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)
    return Template.from_stack(stack)


def test_storage_stack_resource_counts(dev_storage_template: Template) -> None:
    # Exactly one S3 bucket and one SSL enforcement bucket policy
    dev_storage_template.resource_count_is("AWS::S3::Bucket", 1)
    dev_storage_template.resource_count_is("AWS::S3::BucketPolicy", 1)
    dev_storage_template.resource_count_is("AWS::KMS::Key", 0)


def test_s3_bucket_public_access_blocked(dev_storage_template: Template) -> None:
    dev_storage_template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            }
        },
    )


def test_s3_bucket_encryption_is_sse_s3(dev_storage_template: Template) -> None:
    dev_storage_template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {
                        "ServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }
        },
    )


def test_s3_bucket_versioning_disabled(dev_storage_template: Template) -> None:
    # VersioningConfiguration should not be Enabled
    template_dict = dev_storage_template.to_json()
    buckets = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::S3::Bucket"
    ]
    assert len(buckets) == 1
    versioning_config = buckets[0].get("Properties", {}).get("VersioningConfiguration")
    assert versioning_config is None or versioning_config.get("Status") != "Enabled"


def test_s3_bucket_removal_policy_is_retain(dev_storage_template: Template) -> None:
    template_dict = dev_storage_template.to_json()
    buckets = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::S3::Bucket"
    ]
    assert len(buckets) == 1
    assert buckets[0].get("DeletionPolicy") == "Retain"
    assert buckets[0].get("UpdateReplacePolicy") == "Retain"


def test_s3_bucket_ssl_enforcement_policy(dev_storage_template: Template) -> None:
    # Bucket policy must deny non-HTTPS transport
    dev_storage_template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": "s3:*",
                                "Effect": "Deny",
                                "Condition": {
                                    "Bool": {
                                        "aws:SecureTransport": "false"
                                    }
                                },
                            }
                        )
                    ]
                )
            }
        },
    )


def test_s3_bucket_deterministic_naming_dev(dev_storage_template: Template) -> None:
    template_dict = dev_storage_template.to_json()
    buckets = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::S3::Bucket"
    ]
    bucket_name = buckets[0].get("Properties", {}).get("BucketName")
    # BucketName is a string or Fn::Join structure starting with community-analysis-dev-
    if isinstance(bucket_name, str):
        assert "community-analysis-dev-" in bucket_name
    elif isinstance(bucket_name, dict):
        assert "Fn::Join" in bucket_name or "Fn::Sub" in bucket_name


def test_s3_bucket_deterministic_naming_prod(prod_storage_template: Template) -> None:
    template_dict = prod_storage_template.to_json()
    buckets = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::S3::Bucket"
    ]
    bucket_name = buckets[0].get("Properties", {}).get("BucketName")
    if isinstance(bucket_name, str):
        assert "community-analysis-prod-" in bucket_name
    elif isinstance(bucket_name, dict):
        assert "Fn::Join" in bucket_name or "Fn::Sub" in bucket_name


def test_storage_stack_cfn_outputs(dev_storage_template: Template) -> None:
    dev_storage_template.has_output("BucketName", {})
    dev_storage_template.has_output("BucketArn", {})


def test_app_synthesis_includes_storage_stack() -> None:
    app = cdk.App(context={"stage": "dev"})
    stage_config = get_stage_config("dev")
    storage_stack = StorageStack(
        app,
        stage_config.format_stack_name("storage"),
        stage_config=stage_config,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    synth = app.synth()
    assert "community-analysis-dev-storage" in [s.stack_name for s in synth.stacks]
