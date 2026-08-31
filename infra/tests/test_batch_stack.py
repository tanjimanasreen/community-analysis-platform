"""Unit tests for AWS Batch analytical compute infrastructure stack (BatchStack)."""

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Match, Template
from community_analysis_infra.api_stack import ApiStack
from community_analysis_infra.batch_stack import BatchStack
from community_analysis_infra.config import get_stage_config
from community_analysis_infra.frontend_stack import FrontendStack
from community_analysis_infra.registry_stack import RegistryStack
from community_analysis_infra.storage_stack import StorageStack


@pytest.fixture
def dev_batch_template() -> Template:
    app = cdk.App(context={"stage": "dev", "batch_image_tag": "test-batch-sha"})
    stage_config = get_stage_config("dev")
    env = cdk.Environment(account="123456789012", region="us-east-1")

    storage = StorageStack(
        app,
        stage_config.format_stack_name("storage"),
        stage_config=stage_config,
        env=env,
    )
    batch_stack = BatchStack(
        app,
        stage_config.format_stack_name("batch"),
        stage_config=stage_config,
        bucket=storage.bucket,
        batch_image_tag="test-batch-sha",
        env=env,
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)
    return Template.from_stack(batch_stack)


def test_analytics_ecr_repository(dev_batch_template: Template) -> None:
    dev_batch_template.resource_count_is("AWS::ECR::Repository", 1)
    dev_batch_template.resource_count_is("AWS::KMS::Key", 0)
    dev_batch_template.has_resource_properties(
        "AWS::ECR::Repository",
        {
            "RepositoryName": "community-analysis-dev-analytics",
            "ImageTagMutability": "IMMUTABLE",
            "ImageScanningConfiguration": Match.absent(),
            "EmptyOnDelete": True,
            "LifecyclePolicy": {
                "LifecyclePolicyText": Match.string_like_regexp(
                    ".*Expire untagged images after 1 day.*"
                ),
            },
        },
    )
    template_dict = dev_batch_template.to_json()
    repos = [
        res
        for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::ECR::Repository"
    ]
    assert len(repos) == 1
    # Verify AES256 server-side encryption
    encryption_config = repos[0].get("Properties", {}).get("EncryptionConfiguration")
    if encryption_config is not None:
        assert encryption_config.get("EncryptionType") == "AES256"
        assert "KmsKey" not in encryption_config
    assert repos[0].get("DeletionPolicy") == "Delete"
    assert repos[0].get("UpdateReplacePolicy") == "Delete"


def test_dedicated_vpc_and_zero_nat_gateways(dev_batch_template: Template) -> None:
    dev_batch_template.resource_count_is("AWS::EC2::VPC", 1)
    dev_batch_template.resource_count_is("AWS::EC2::InternetGateway", 1)
    dev_batch_template.resource_count_is("AWS::EC2::NatGateway", 0)
    dev_batch_template.resource_count_is("AWS::EC2::Subnet", 2)


def test_fargate_compute_environments(dev_batch_template: Template) -> None:
    dev_batch_template.resource_count_is("AWS::Batch::ComputeEnvironment", 2)

    # Spot environment
    dev_batch_template.has_resource_properties(
        "AWS::Batch::ComputeEnvironment",
        {
            "ComputeResources": {
                "Type": "FARGATE_SPOT",
                "MaxvCpus": 16,
                "MinvCpus": Match.absent(),
                "DesiredvCpus": Match.absent(),
            },
            "Type": "managed",
            "State": "ENABLED",
        },
    )

    # On-Demand environment
    dev_batch_template.has_resource_properties(
        "AWS::Batch::ComputeEnvironment",
        {
            "ComputeResources": {
                "Type": "FARGATE",
                "MaxvCpus": 16,
                "MinvCpus": Match.absent(),
                "DesiredvCpus": Match.absent(),
            },
            "Type": "managed",
            "State": "ENABLED",
        },
    )


def test_job_queue_prioritization(dev_batch_template: Template) -> None:
    dev_batch_template.resource_count_is("AWS::Batch::JobQueue", 1)
    dev_batch_template.has_resource_properties(
        "AWS::Batch::JobQueue",
        {
            "JobQueueName": "community-analysis-dev-queue",
            "Priority": 1,
            "State": "ENABLED",
            "ComputeEnvironmentOrder": [
                Match.object_like(
                    {
                        "Order": 1,
                    }
                ),
                Match.object_like(
                    {
                        "Order": 2,
                    }
                ),
            ],
        },
    )


def test_fargate_job_definition(dev_batch_template: Template) -> None:
    dev_batch_template.resource_count_is("AWS::Batch::JobDefinition", 1)
    dev_batch_template.has_resource_properties(
        "AWS::Batch::JobDefinition",
        {
            "JobDefinitionName": "community-analysis-dev-analytics-job",
            "Type": "container",
            "PlatformCapabilities": ["FARGATE"],
            "Timeout": {
                "AttemptDurationSeconds": 7200,
            },
            "RetryStrategy": {
                "Attempts": 2,
            },
            "ContainerProperties": {
                "NetworkConfiguration": {
                    "AssignPublicIp": "ENABLED",
                },
                "EphemeralStorage": {
                    "SizeInGiB": 30,
                },
                "ResourceRequirements": [
                    {"Type": "MEMORY", "Value": "16384"},
                    {"Type": "VCPU", "Value": "4"},
                ],
                "RuntimePlatform": {
                    "CpuArchitecture": "ARM64",
                    "OperatingSystemFamily": "LINUX",
                },
            },
        },
    )


def test_iam_roles_and_scoped_s3_permissions(dev_batch_template: Template) -> None:
    # Execution role + Job role = 2 IAM Roles in BatchStack
    dev_batch_template.resource_count_is("AWS::IAM::Role", 2)

    template_dict = dev_batch_template.to_json()
    policy_statements = []
    for res in template_dict.get("Resources", {}).values():
        if res.get("Type") == "AWS::IAM::Policy":
            policy_doc = res.get("Properties", {}).get("PolicyDocument", {})
            for statement in policy_doc.get("Statement", []):
                policy_statements.append(statement)

    # 1. Verify ListBucket statement exists with prefix condition
    list_statements = [
        s for s in policy_statements if s.get("Action") == "s3:ListBucket"
    ]
    assert len(list_statements) == 1
    list_stmt = list_statements[0]
    assert list_stmt.get("Effect") == "Allow"
    assert list_stmt.get("Condition") == {
        "StringLike": {
            "s3:prefix": ["raw/*", "cache/*"],
        }
    }

    # 2. Verify GetObject statement exists and is scoped to raw/* and cache/*
    get_statements = [s for s in policy_statements if s.get("Action") == "s3:GetObject"]
    assert len(get_statements) == 1
    get_stmt = get_statements[0]
    assert get_stmt.get("Effect") == "Allow"
    get_resources = get_stmt.get("Resource", [])
    assert len(get_resources) == 2
    # Verify raw/* and cache/* are in the resources
    joined_get = [str(r) for r in get_resources]
    assert any("raw/*" in r for r in joined_get)
    assert any("cache/*" in r for r in joined_get)

    # 3. Verify PutObject statement exists and is scoped to runs/*, reports/*, cache/*
    put_statements = [s for s in policy_statements if s.get("Action") == "s3:PutObject"]
    assert len(put_statements) == 1
    put_stmt = put_statements[0]
    assert put_stmt.get("Effect") == "Allow"
    put_resources = put_stmt.get("Resource", [])
    assert len(put_resources) == 3
    joined_put = [str(r) for r in put_resources]
    assert any("runs/*" in r for r in joined_put)
    assert any("reports/*" in r for r in joined_put)
    assert any("cache/*" in r for r in joined_put)

    # 4. Verify no wildcard s3:*, Resource: *, configs/*, or bucket-admin actions exist
    for statement in policy_statements:
        actions = statement.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        assert "s3:*" not in actions
        assert "s3:DeleteBucket" not in actions
        assert "s3:PutBucketPolicy" not in actions
        assert "s3:DeleteObject" not in actions

        resources = statement.get("Resource", [])
        if isinstance(resources, str):
            resources = [resources]
        for res in resources:
            if isinstance(res, str):
                assert "configs/*" not in res
            elif isinstance(res, dict) and "Fn::Join" in res:
                joined_parts = "".join(str(p) for p in res["Fn::Join"][1])
                assert "configs/*" not in joined_parts


def test_cloudwatch_log_group(dev_batch_template: Template) -> None:
    dev_batch_template.resource_count_is("AWS::Logs::LogGroup", 1)
    dev_batch_template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": "/aws/batch/job/community-analysis-dev",
            "RetentionInDays": 7,
        },
    )


def test_batch_security_group_no_inbound(dev_batch_template: Template) -> None:
    dev_batch_template.resource_count_is("AWS::EC2::SecurityGroup", 1)
    dev_batch_template.has_resource_properties(
        "AWS::EC2::SecurityGroup",
        {
            "SecurityGroupEgress": Match.array_with(
                [
                    Match.object_like(
                        {
                            "CidrIp": "0.0.0.0/0",
                            "IpProtocol": "-1",
                        }
                    )
                ]
            ),
            "SecurityGroupIngress": Match.absent(),
        },
    )


def test_batch_stack_infrastructure_exclusions(dev_batch_template: Template) -> None:
    dev_batch_template.resource_count_is("AWS::Lambda::Function", 0)
    dev_batch_template.resource_count_is("AWS::ApiGatewayV2::Api", 0)
    dev_batch_template.resource_count_is("AWS::Cognito::UserPool", 0)
    dev_batch_template.resource_count_is("AWS::CloudFront::Distribution", 0)
    dev_batch_template.resource_count_is("AWS::WAFv2::WebACL", 0)
    dev_batch_template.resource_count_is("AWS::RDS::DBInstance", 0)
    dev_batch_template.resource_count_is("AWS::ECS::Service", 0)
    dev_batch_template.resource_count_is("AWS::EC2::NatGateway", 0)


def test_prod_batch_stack_retention() -> None:
    app = cdk.App(context={"stage": "prod", "batch_image_tag": "prod-batch-sha"})
    stage_config = get_stage_config("prod")
    env = cdk.Environment(account="123456789012", region="us-east-1")

    storage = StorageStack(
        app,
        stage_config.format_stack_name("storage"),
        stage_config=stage_config,
        env=env,
    )
    batch_stack = BatchStack(
        app,
        stage_config.format_stack_name("batch"),
        stage_config=stage_config,
        bucket=storage.bucket,
        batch_image_tag="prod-batch-sha",
        env=env,
    )
    prod_template = Template.from_stack(batch_stack)
    prod_template.resource_count_is("AWS::ECR::Repository", 1)
    prod_template.resource_count_is("AWS::KMS::Key", 0)
    prod_template.has_resource_properties(
        "AWS::ECR::Repository",
        {
            "RepositoryName": "community-analysis-prod-analytics",
            "ImageTagMutability": "IMMUTABLE",
            "ImageScanningConfiguration": Match.absent(),
            "EmptyOnDelete": False,
            "LifecyclePolicy": {
                "LifecyclePolicyText": Match.string_like_regexp(
                    ".*Expire untagged images after 1 day.*"
                ),
            },
        },
    )
    prod_dict = prod_template.to_json()
    repos = [
        res
        for res in prod_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::ECR::Repository"
    ]
    assert len(repos) == 1
    # Verify AES256 server-side encryption
    encryption_config = repos[0].get("Properties", {}).get("EncryptionConfiguration")
    if encryption_config is not None:
        assert encryption_config.get("EncryptionType") == "AES256"
        assert "KmsKey" not in encryption_config
    assert repos[0].get("DeletionPolicy") == "Retain"
    assert repos[0].get("UpdateReplacePolicy") == "Retain"

    prod_template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": "/aws/batch/job/community-analysis-prod",
            "RetentionInDays": 30,
        },
    )


def test_batch_cdk_context_isolation() -> None:
    """Verify that ApiStack and FrontendStack can synthesize without batch_image_tag."""
    app = cdk.App(context={"stage": "dev", "image_tag": "94fa3081"})
    stage_config = get_stage_config("dev")
    env = cdk.Environment(account="123456789012", region="us-east-1")

    storage = StorageStack(
        app,
        stage_config.format_stack_name("storage"),
        stage_config=stage_config,
        env=env,
    )
    registry = RegistryStack(
        app,
        stage_config.format_stack_name("registry"),
        stage_config=stage_config,
        env=env,
    )
    api = ApiStack(
        app,
        stage_config.format_stack_name("api"),
        stage_config=stage_config,
        bucket=storage.bucket,
        repository=registry.repository,
        image_tag="94fa3081",
        env=env,
    )
    FrontendStack(
        app,
        stage_config.format_stack_name("frontend"),
        stage_config=stage_config,
        http_api=api.http_api,
        user_pool=api.user_pool,
        api_app_client=api.app_client,
        lambda_function=api.lambda_function,
        env=env,
    )

    synth_result = app.synth()
    assert synth_result is not None
    stack_names = [s.stack_name for s in synth_result.stacks]
    assert "community-analysis-dev-api" in stack_names
    assert "community-analysis-dev-frontend" in stack_names
    assert "community-analysis-dev-batch" not in stack_names
