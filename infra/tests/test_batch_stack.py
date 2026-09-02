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
        tei_analytics_image_tag="test-tei-analytics-sha",
        tei_image_tag="test-tei-sha",
        env=env,
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)
    return Template.from_stack(batch_stack)


def test_analytics_ecr_repository(dev_batch_template: Template) -> None:
    # 2 ECR Repositories: Analytics + TEI
    dev_batch_template.resource_count_is("AWS::ECR::Repository", 2)
    dev_batch_template.resource_count_is("AWS::KMS::Key", 0)
    for repo_name in ["community-analysis-dev-analytics", "community-analysis-dev-tei"]:
        dev_batch_template.has_resource_properties(
            "AWS::ECR::Repository",
            {
                "RepositoryName": repo_name,
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
    assert len(repos) == 2
    for repo in repos:
        # Verify AES256 server-side encryption
        encryption_config = repo.get("Properties", {}).get("EncryptionConfiguration")
        if encryption_config is not None:
            assert encryption_config.get("EncryptionType") == "AES256"
            assert "KmsKey" not in encryption_config
        assert repo.get("DeletionPolicy") == "Delete"
        assert repo.get("UpdateReplacePolicy") == "Delete"

        # Verify lifecycle policy strictly expires untagged images only
        lifecycle_text = (
            repo.get("Properties", {})
            .get("LifecyclePolicy", {})
            .get("LifecyclePolicyText")
        )
        assert lifecycle_text is not None
        import json

        lifecycle_data = json.loads(lifecycle_text)
        rules = lifecycle_data.get("rules", [])
        assert len(rules) == 1
        rule = rules[0]
        assert rule.get("selection", {}).get("tagStatus") == "untagged"
        assert rule.get("selection", {}).get("countType") == "sinceImagePushed"
        assert rule.get("selection", {}).get("countUnit") == "days"
        assert rule.get("selection", {}).get("countNumber") == 1
        assert rule.get("action", {}).get("type") == "expire"


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
    dev_batch_template.resource_count_is("AWS::Batch::JobDefinition", 2)
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


def test_fargate_tei_multi_container_job_definition(
    dev_batch_template: Template,
) -> None:
    """Verify additive multi-container TEI Job Definition properties."""
    dev_batch_template.has_resource_properties(
        "AWS::Batch::JobDefinition",
        {
            "JobDefinitionName": "community-analysis-dev-analytics-tei-job",
            "Type": "container",
            "PlatformCapabilities": ["FARGATE"],
            "Timeout": {
                "AttemptDurationSeconds": 7200,
            },
            "RetryStrategy": {
                "Attempts": 2,
            },
            "EcsProperties": {
                "TaskProperties": [
                    {
                        "NetworkConfiguration": {
                            "AssignPublicIp": "ENABLED",
                        },
                        "EphemeralStorage": {
                            "SizeInGiB": 30,
                        },
                        "RuntimePlatform": {
                            "CpuArchitecture": "ARM64",
                            "OperatingSystemFamily": "LINUX",
                        },
                        "Containers": Match.array_with(
                            [
                                Match.object_like(
                                    {
                                        "Name": "analytics",
                                        "Essential": True,
                                        "ResourceRequirements": [
                                            {"Type": "VCPU", "Value": "4"},
                                            {"Type": "MEMORY", "Value": "16384"},
                                        ],
                                        "DependsOn": [
                                            {
                                                "Condition": "START",
                                                "ContainerName": "tei-similarity",
                                            },
                                            {
                                                "Condition": "START",
                                                "ContainerName": "tei-clustering",
                                            },
                                        ],
                                        "LogConfiguration": {
                                            "LogDriver": "awslogs",
                                            "Options": Match.object_like(
                                                {
                                                    "awslogs-stream-prefix": "analytics",
                                                }
                                            ),
                                        },
                                        "Environment": Match.array_with(
                                            [
                                                {
                                                    "Name": "THEME_SIMILARITY_PROVIDER",
                                                    "Value": "tei",
                                                },
                                                {
                                                    "Name": "THEME_CLUSTERING_PROVIDER",
                                                    "Value": "tei",
                                                },
                                                {
                                                    "Name": "THEME_SIMILARITY_FAILURE_POLICY",
                                                    "Value": "fail",
                                                },
                                                {
                                                    "Name": "TEI_SIMILARITY_BASE_URL",
                                                    "Value": "http://127.0.0.1:8080",
                                                },
                                                {
                                                    "Name": "TEI_CLUSTERING_BASE_URL",
                                                    "Value": "http://127.0.0.1:8081",
                                                },
                                            ]
                                        ),
                                    }
                                ),
                                Match.object_like(
                                    {
                                        "Name": "tei-similarity",
                                        "Essential": False,
                                        "Command": [
                                            "--model-id",
                                            "/models/similarity",
                                            "--port",
                                            "8080",
                                        ],
                                        "ResourceRequirements": [
                                            {"Type": "VCPU", "Value": "2"},
                                            {"Type": "MEMORY", "Value": "4096"},
                                        ],
                                        "LogConfiguration": {
                                            "LogDriver": "awslogs",
                                            "Options": Match.object_like(
                                                {
                                                    "awslogs-stream-prefix": "tei-similarity",
                                                }
                                            ),
                                        },
                                    }
                                ),
                                Match.object_like(
                                    {
                                        "Name": "tei-clustering",
                                        "Essential": False,
                                        "Command": [
                                            "--model-id",
                                            "/models/clustering",
                                            "--port",
                                            "8081",
                                        ],
                                        "ResourceRequirements": [
                                            {"Type": "VCPU", "Value": "2"},
                                            {"Type": "MEMORY", "Value": "4096"},
                                        ],
                                        "LogConfiguration": {
                                            "LogDriver": "awslogs",
                                            "Options": Match.object_like(
                                                {
                                                    "awslogs-stream-prefix": "tei-clustering",
                                                }
                                            ),
                                        },
                                    }
                                ),
                            ]
                        ),
                    }
                ]
            },
        },
    )

    # Verify structurally that Fargate-unsupported properties (IpcMode, PidMode) are ABSENT
    template_dict = dev_batch_template.to_json()
    job_defs = [
        res
        for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::Batch::JobDefinition"
        and res.get("Properties", {}).get("JobDefinitionName")
        == "community-analysis-dev-analytics-tei-job"
    ]
    assert len(job_defs) == 1
    task_props = (
        job_defs[0]
        .get("Properties", {})
        .get("EcsProperties", {})
        .get("TaskProperties", [{}])[0]
    )
    assert "IpcMode" not in task_props
    assert "PidMode" not in task_props
    assert "ipcMode" not in task_props
    assert "pidMode" not in task_props

    containers = task_props.get("Containers", [])
    assert len(containers) == 3
    for c in containers:
        assert "Privileged" not in c
        assert not any(
            req.get("Type") == "GPU" for req in c.get("ResourceRequirements", [])
        )

    container_map = {c["Name"]: c for c in containers}
    assert container_map["tei-similarity"]["Command"] == [
        "--model-id",
        "/models/similarity",
        "--port",
        "8080",
    ]
    assert container_map["tei-clustering"]["Command"] == [
        "--model-id",
        "/models/clustering",
        "--port",
        "8081",
    ]
    for name in ["tei-similarity", "tei-clustering"]:
        cmd_str = " ".join(container_map[name]["Command"])
        assert "sentence-transformers/" not in cmd_str


def test_iam_roles_and_scoped_s3_permissions(dev_batch_template: Template) -> None:
    # Execution role + Job role = 2 IAM Roles in BatchStack
    dev_batch_template.resource_count_is("AWS::IAM::Role", 2)

    template_dict = dev_batch_template.to_json()
    job_policy_statements = []
    exec_policy_statements = []
    for res in template_dict.get("Resources", {}).values():
        if res.get("Type") == "AWS::IAM::Policy":
            roles = res.get("Properties", {}).get("Roles", [])
            policy_doc = res.get("Properties", {}).get("PolicyDocument", {})
            for statement in policy_doc.get("Statement", []):
                for role_ref in roles:
                    if isinstance(role_ref, dict) and "Ref" in role_ref:
                        ref_str = role_ref["Ref"]
                        if "JobRole" in ref_str:
                            job_policy_statements.append(statement)
                        elif "ExecutionRole" in ref_str:
                            exec_policy_statements.append(statement)

    # 1. Verify ListBucket statement exists with prefix condition
    list_statements = [
        s for s in job_policy_statements if s.get("Action") == "s3:ListBucket"
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
    get_statements = [
        s for s in job_policy_statements if s.get("Action") == "s3:GetObject"
    ]
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
    put_statements = [
        s for s in job_policy_statements if s.get("Action") == "s3:PutObject"
    ]
    assert len(put_statements) == 1
    put_stmt = put_statements[0]
    assert put_stmt.get("Effect") == "Allow"
    put_resources = put_stmt.get("Resource", [])
    assert len(put_resources) == 3
    joined_put = [str(r) for r in put_resources]
    assert any("runs/*" in r for r in joined_put)
    assert any("reports/*" in r for r in joined_put)
    assert any("cache/*" in r for r in joined_put)

    # 4. Verify no wildcard s3:*, Resource: *, configs/*, or bucket-admin actions exist in JobRole
    for statement in job_policy_statements:
        actions = statement.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        assert "s3:*" not in actions
        assert "s3:DeleteBucket" not in actions
        assert "s3:PutBucketPolicy" not in actions
        assert "s3:DeleteObject" not in actions
        for act in actions:
            assert not act.startswith("secretsmanager:")
            assert not act.startswith("ssm:")
            assert act != "*"

        resources = statement.get("Resource", [])
        if isinstance(resources, str):
            resources = [resources]
        for res in resources:
            if any(act.startswith("s3:") for act in actions):
                if isinstance(res, str):
                    assert res != "*"
            if isinstance(res, str):
                assert "configs/*" not in res
            elif isinstance(res, dict) and "Fn::Join" in res:
                joined_parts = "".join(str(p) for p in res["Fn::Join"][1])
                assert "configs/*" not in joined_parts

    # 5. Verify ExecutionRole has scoped secretsmanager read (no wildcards)
    exec_actions = []
    for statement in exec_policy_statements:
        actions = statement.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        exec_actions.extend(actions)
        for act in actions:
            assert act != "*"
            assert act != "secretsmanager:*"
    assert "secretsmanager:GetSecretValue" in exec_actions


def test_no_ecs_service_alb_or_cloud_map(dev_batch_template: Template) -> None:
    """Verify that BatchStack contains no ECS services, load balancers, or service discovery."""
    dev_batch_template.resource_count_is("AWS::ECS::Service", 0)
    dev_batch_template.resource_count_is("AWS::ElasticLoadBalancingV2::LoadBalancer", 0)
    dev_batch_template.resource_count_is("AWS::ServiceDiscovery::Service", 0)


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


def test_batch_stack_outputs(dev_batch_template: Template) -> None:
    outputs = dev_batch_template.to_json().get("Outputs", {})
    expected_outputs = [
        "AnalyticsRepositoryUri",
        "TeiRepositoryUri",
        "TeiRepositoryName",
        "BatchVpcId",
        "BatchJobQueueArn",
        "BatchJobQueueName",
        "BatchJobDefinitionArn",
        "BatchJobDefinitionName",
        "BatchTeiJobDefinitionArn",
        "BatchTeiJobDefinitionName",
        "OpenAiSecretArn",
        "AzureTranslatorSecretArn",
    ]
    for exp in expected_outputs:
        assert exp in outputs, f"Missing expected output: {exp}"


def test_batch_stack_secrets_and_data_root(dev_batch_template: Template) -> None:
    """Verify that BatchStack defines secrets and injects DATA_ROOT and provider secrets."""
    # Verify 2 secrets manager secrets are created
    dev_batch_template.resource_count_is("AWS::SecretsManager::Secret", 2)
    dev_batch_template.has_resource_properties(
        "AWS::SecretsManager::Secret",
        {"Name": "community-analysis-dev-openai-api-key"},
    )
    dev_batch_template.has_resource_properties(
        "AWS::SecretsManager::Secret",
        {"Name": "community-analysis-dev-azure-translator-key"},
    )

    # Verify DeletionPolicy and UpdateReplacePolicy are Retain even in dev
    template_dict = dev_batch_template.to_json()
    secrets = [
        res
        for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::SecretsManager::Secret"
    ]
    assert len(secrets) == 2
    for sec in secrets:
        assert sec.get("DeletionPolicy") == "Retain"
        assert sec.get("UpdateReplacePolicy") == "Retain"

    # Verify single-container job def has DATA_ROOT and Secrets
    dev_batch_template.has_resource_properties(
        "AWS::Batch::JobDefinition",
        {
            "JobDefinitionName": "community-analysis-dev-analytics-job",
            "ContainerProperties": Match.object_like(
                {
                    "Environment": Match.array_with(
                        [{"Name": "DATA_ROOT", "Value": "/app/workspace/data/raw"}]
                    ),
                    "Secrets": Match.array_with(
                        [
                            Match.object_like({"Name": "OPENAI_API_KEY"}),
                            Match.object_like({"Name": "AZURE_TRANSLATOR_KEY"}),
                        ]
                    ),
                }
            ),
        },
    )

    # Verify multi-container TEI job def analytics container has DATA_ROOT and Secrets
    template_dict = dev_batch_template.to_json()
    job_defs = [
        res
        for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::Batch::JobDefinition"
        and res.get("Properties", {}).get("JobDefinitionName")
        == "community-analysis-dev-analytics-tei-job"
    ]
    assert len(job_defs) == 1
    containers = (
        job_defs[0]
        .get("Properties", {})
        .get("EcsProperties", {})
        .get("TaskProperties", [{}])[0]
        .get("Containers", [])
    )
    analytics_container = [c for c in containers if c.get("Name") == "analytics"][0]

    env_names = [e.get("Name") for e in analytics_container.get("Environment", [])]
    assert "DATA_ROOT" in env_names

    secret_names = [s.get("Name") for s in analytics_container.get("Secrets", [])]
    assert "OPENAI_API_KEY" in secret_names
    assert "AZURE_TRANSLATOR_KEY" in secret_names


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
        tei_analytics_image_tag="prod-tei-analytics-sha",
        tei_image_tag="prod-tei-sha",
        env=env,
    )
    prod_template = Template.from_stack(batch_stack)
    prod_template.resource_count_is("AWS::ECR::Repository", 2)
    prod_template.resource_count_is("AWS::Batch::JobDefinition", 2)
    prod_template.resource_count_is("AWS::KMS::Key", 0)
    for repo_name in [
        "community-analysis-prod-analytics",
        "community-analysis-prod-tei",
    ]:
        prod_template.has_resource_properties(
            "AWS::ECR::Repository",
            {
                "RepositoryName": repo_name,
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
    assert len(repos) == 2
    for repo in repos:
        # Verify AES256 server-side encryption
        encryption_config = repo.get("Properties", {}).get("EncryptionConfiguration")
        if encryption_config is not None:
            assert encryption_config.get("EncryptionType") == "AES256"
            assert "KmsKey" not in encryption_config
        assert repo.get("DeletionPolicy") == "Retain"
        assert repo.get("UpdateReplacePolicy") == "Retain"

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


def test_distinct_image_tag_wiring_in_batch_stack() -> None:
    """Verify that batch_image_tag, tei_analytics_image_tag, and tei_image_tag are distinct and independent."""
    import json

    stage_config = get_stage_config("dev")
    env = cdk.Environment(account="123456789012", region="us-east-1")
    app = cdk.App()
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
        batch_image_tag="plan094-3adeb1fd",
        tei_analytics_image_tag="plan095-analytics-sha",
        tei_image_tag="plan095-tei-sha",
        env=env,
    )
    template = Template.from_stack(batch_stack)
    template_dict = template.to_json()

    # Find both job definitions in the synthesized CloudFormation template
    p094_job_def = None
    p095_job_def = None
    for res in template_dict.get("Resources", {}).values():
        if res.get("Type") == "AWS::Batch::JobDefinition":
            job_name = res.get("Properties", {}).get("JobDefinitionName")
            if job_name == "community-analysis-dev-analytics-job":
                p094_job_def = res
            elif job_name == "community-analysis-dev-analytics-tei-job":
                p095_job_def = res

    assert p094_job_def is not None, "Plan 094 AnalyticsJobDefinition must exist"
    assert p095_job_def is not None, "Plan 095 AnalyticsTeiJobDefinition must exist"

    # 1. Existing AnalyticsJobDefinition image contains :plan094-3adeb1fd
    p094_container_img = json.dumps(p094_job_def["Properties"]["ContainerProperties"]["Image"])
    assert ":plan094-3adeb1fd" in p094_container_img

    # 2. Plan 095 AnalyticsTeiJobDefinition containers
    containers = (
        p095_job_def["Properties"]["EcsProperties"]["TaskProperties"][0]["Containers"]
    )
    assert len(containers) == 3
    container_map = {c["Name"]: c for c in containers}

    # 3. Plan 095 Analytics container image contains :plan095-analytics-sha
    p095_analytics_img = json.dumps(container_map["analytics"]["Image"])
    assert ":plan095-analytics-sha" in p095_analytics_img

    # 4. Plan 095 tei-similarity and tei-clustering containers contain :plan095-tei-sha
    sim_img = json.dumps(container_map["tei-similarity"]["Image"])
    clust_img = json.dumps(container_map["tei-clustering"]["Image"])
    assert ":plan095-tei-sha" in sim_img
    assert ":plan095-tei-sha" in clust_img

    # 5. Plan 095 analytics container image != existing Plan 094 image tag
    assert ":plan094-3adeb1fd" not in p095_analytics_img
    assert ":plan095-analytics-sha" not in p094_container_img


def test_batch_stack_fails_when_plan095_tags_missing() -> None:
    """Verify that BatchStack fails fast when explicit Plan 095 tags are missing."""
    import pytest

    stage_config = get_stage_config("dev")
    env = cdk.Environment(account="123456789012", region="us-east-1")
    app = cdk.App()
    storage = StorageStack(
        app,
        stage_config.format_stack_name("storage"),
        stage_config=stage_config,
        env=env,
    )

    with pytest.raises(ValueError, match="tei_analytics_image_tag is required"):
        BatchStack(
            app,
            "BatchMissingAnalyticsTag",
            stage_config=stage_config,
            bucket=storage.bucket,
            batch_image_tag="batch-sha",
            tei_analytics_image_tag="",
            tei_image_tag="tei-sha",
            env=env,
        )

    with pytest.raises(ValueError, match="tei_image_tag is required"):
        BatchStack(
            app,
            "BatchMissingTeiTag",
            stage_config=stage_config,
            bucket=storage.bucket,
            batch_image_tag="batch-sha",
            tei_analytics_image_tag="analytics-sha",
            tei_image_tag="",
            env=env,
        )
