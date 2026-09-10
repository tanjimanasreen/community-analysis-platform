"""Unit tests for ApiStack, Lambda runtime, Cognito auth, and API Gateway configuration."""

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Match, Template
from community_analysis_infra.api_stack import ApiStack
from community_analysis_infra.config import get_stage_config
from community_analysis_infra.registry_stack import RegistryStack
from community_analysis_infra.storage_stack import StorageStack


@pytest.fixture
def dev_api_template() -> Template:
    app = cdk.App(context={"stage": "dev", "image_tag": "test1234"})
    stage_config = get_stage_config("dev")
    storage = StorageStack(
        app,
        stage_config.format_stack_name("storage"),
        stage_config=stage_config,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    registry = RegistryStack(
        app,
        stage_config.format_stack_name("registry"),
        stage_config=stage_config,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    stack = ApiStack(
        app,
        stage_config.format_stack_name("api"),
        stage_config=stage_config,
        bucket=storage.bucket,
        repository=registry.repository,
        image_tag="test1234",
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)
    return Template.from_stack(stack)


@pytest.fixture
def prod_api_template() -> Template:
    app = cdk.App(context={"stage": "prod", "image_tag": "prod1234"})
    stage_config = get_stage_config("prod")
    storage = StorageStack(
        app,
        stage_config.format_stack_name("storage"),
        stage_config=stage_config,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    registry = RegistryStack(
        app,
        stage_config.format_stack_name("registry"),
        stage_config=stage_config,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    stack = ApiStack(
        app,
        stage_config.format_stack_name("api"),
        stage_config=stage_config,
        bucket=storage.bucket,
        repository=registry.repository,
        image_tag="prod1234",
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)
    return Template.from_stack(stack)


def test_api_stack_missing_image_tag_fails() -> None:
    app = cdk.App(context={"stage": "dev"})
    stage_config = get_stage_config("dev")
    storage = StorageStack(
        app,
        stage_config.format_stack_name("storage"),
        stage_config=stage_config,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    registry = RegistryStack(
        app,
        stage_config.format_stack_name("registry"),
        stage_config=stage_config,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    with pytest.raises(ValueError, match="image_tag is required for ApiStack"):
        ApiStack(
            app,
            stage_config.format_stack_name("api"),
            stage_config=stage_config,
            bucket=storage.bucket,
            repository=registry.repository,
            image_tag="",
            env=cdk.Environment(account="123456789012", region="us-east-1"),
        )


def test_lambda_function_properties(dev_api_template: Template) -> None:
    dev_api_template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "PackageType": "Image",
            "Architectures": ["arm64"],
            "MemorySize": 1024,
            "Timeout": 30,
            "Environment": {
                "Variables": {
                    "COMMUNITY_ANALYSIS_STORAGE_BACKEND": "s3",
                    "COMMUNITY_ANALYSIS_S3_BUCKET": Match.any_value(),
                    "COMMUNITY_ANALYSIS_S3_REGION": Match.any_value(),
                    "COMMUNITY_ANALYSIS_API_ALLOWED_HOSTS": "*",
                    "COMMUNITY_ANALYSIS_API_CATALOG_REFRESH_SECONDS": "60.0",
                    "AWS_LWA_PORT": "8000",
                    "AWS_LWA_READINESS_CHECK_PATH": "/api/v1/health",
                    "AWS_LWA_READINESS_CHECK_HEALTHY_STATUS": "200-399",
                    "LOG_FORMAT": "json",
                    "LOG_LEVEL": "INFO",
                }
            },
        },
    )


def test_lambda_no_vpc_and_no_provisioned_concurrency(dev_api_template: Template) -> None:
    template_dict = dev_api_template.to_json()
    functions = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::Lambda::Function"
    ]
    assert len(functions) == 1
    props = functions[0].get("Properties", {})
    assert "VpcConfig" not in props
    assert "ProvisionedConcurrentExecutions" not in props


def test_cognito_user_pool_configuration(dev_api_template: Template) -> None:
    dev_api_template.has_resource_properties(
        "AWS::Cognito::UserPool",
        {
            "UserPoolName": "community-analysis-dev-user-pool",
            "AdminCreateUserConfig": {
                "AllowAdminCreateUserOnly": True,
            },
        },
    )


def test_cognito_user_pool_client_configuration(dev_api_template: Template) -> None:
    template_dict = dev_api_template.to_json()
    clients = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::Cognito::UserPoolClient"
    ]
    assert len(clients) == 1
    props = clients[0].get("Properties", {})
    assert props.get("ClientName") == "community-analysis-dev-api-client"
    assert props.get("GenerateSecret") is False
    flows = props.get("ExplicitAuthFlows", [])
    assert "ALLOW_USER_PASSWORD_AUTH" in flows
    assert "ALLOW_USER_SRP_AUTH" in flows
    assert "ALLOW_ADMIN_USER_PASSWORD_AUTH" in flows


def test_api_gateway_http_api_configuration(dev_api_template: Template) -> None:
    dev_api_template.has_resource_properties(
        "AWS::ApiGatewayV2::Api",
        {
            "Name": "community-analysis-dev-api",
            "ProtocolType": "HTTP",
        },
    )
    dev_api_template.has_resource_properties(
        "AWS::ApiGatewayV2::Authorizer",
        {
            "AuthorizerType": "JWT",
            "Name": "CognitoAuthorizer",
            "IdentitySource": ["$request.header.Authorization"],
        },
    )


def test_api_gateway_routes(dev_api_template: Template) -> None:
    # Public health route (AuthorizationType=NONE)
    dev_api_template.has_resource_properties(
        "AWS::ApiGatewayV2::Route",
        {
            "RouteKey": "GET /api/v1/health",
            "AuthorizationType": "NONE",
        },
    )
    # Protected default route (AuthorizationType=JWT)
    dev_api_template.has_resource_properties(
        "AWS::ApiGatewayV2::Route",
        {
            "RouteKey": "$default",
            "AuthorizationType": "JWT",
        },
    )


def test_iam_s3_read_permissions_only(dev_api_template: Template) -> None:
    template_dict = dev_api_template.to_json()
    policies = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::IAM::Policy"
    ]
    # Inspect all statements across policies attached to the execution role
    s3_actions = set()
    for policy in policies:
        doc = policy.get("Properties", {}).get("PolicyDocument", {})
        for stmt in doc.get("Statement", []):
            actions = stmt.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            for a in actions:
                if a.startswith("s3:"):
                    s3_actions.add(a)

    assert len(s3_actions) > 0, "S3 read actions must be granted"

    # Positively assert required read capabilities
    has_get_object = any(
        a in ("s3:GetObject", "s3:GetObject*") or a.startswith("s3:GetObject")
        for a in s3_actions
    )
    has_list_bucket = any(
        a in ("s3:ListBucket", "s3:List*") or a.startswith("s3:List")
        for a in s3_actions
    )
    assert has_get_object, f"S3 GetObject capability missing from actions: {s3_actions}"
    assert has_list_bucket, f"S3 List/ListBucket capability missing from actions: {s3_actions}"

    # Reject write, delete, and global wildcard permissions
    for action in s3_actions:
        assert not action.startswith("s3:Put"), f"Write action {action} forbidden"
        assert not action.startswith("s3:Delete"), f"Delete action {action} forbidden"
        assert action != "s3:*", "Wildcard s3:* forbidden"


def test_cloudwatch_log_group_retention(dev_api_template: Template, prod_api_template: Template) -> None:
    dev_api_template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": "/aws/lambda/community-analysis-dev-api",
            "RetentionInDays": 7,
        },
    )
    prod_api_template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": "/aws/lambda/community-analysis-prod-api",
            "RetentionInDays": 30,
        },
    )


def test_cost_and_network_invariants(dev_api_template: Template) -> None:
    dev_api_template.resource_count_is("AWS::EC2::VPC", 0)
    dev_api_template.resource_count_is("AWS::EC2::NatGateway", 0)
    dev_api_template.resource_count_is("AWS::EC2::Instance", 0)
    dev_api_template.resource_count_is("AWS::KMS::Key", 0)


def test_api_stack_outputs(dev_api_template: Template) -> None:
    dev_api_template.has_output("ApiEndpoint", {"Description": "URL of the HTTP API"})
    dev_api_template.has_output("LambdaFunctionName", {"Description": "Name of the API Lambda function"})
    dev_api_template.has_output("CognitoUserPoolId", {"Description": "ID of the Cognito User Pool"})
    dev_api_template.has_output("CognitoAppClientId", {"Description": "ID of the Cognito App Client"})
    dev_api_template.has_output("DeployedImageTag", {"Description": "Immutable ECR image tag deployed"})
