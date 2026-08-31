"""Unit tests for FrontendStack, S3 OAC hosting, CloudFront SPA routing, and browser Cognito auth."""

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Match, Template
from community_analysis_infra.api_stack import ApiStack
from community_analysis_infra.config import get_stage_config
from community_analysis_infra.frontend_stack import FrontendStack
from community_analysis_infra.registry_stack import RegistryStack
from community_analysis_infra.storage_stack import StorageStack


@pytest.fixture
def dev_frontend_template() -> Template:
    app = cdk.App(context={"stage": "dev", "image_tag": "test1234"})
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
        image_tag="test1234",
        env=env,
    )
    frontend = FrontendStack(
        app,
        stage_config.format_stack_name("frontend"),
        stage_config=stage_config,
        http_api=api.http_api,
        user_pool=api.user_pool,
        api_app_client=api.app_client,
        lambda_function=api.lambda_function,
        env=env,
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)
    return Template.from_stack(frontend)


def test_frontend_s3_bucket_configuration(dev_frontend_template: Template) -> None:
    dev_frontend_template.resource_count_is("AWS::S3::Bucket", 1)
    dev_frontend_template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {
                        "ServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256",
                        },
                    },
                ],
            },
        },
    )
    template_dict = dev_frontend_template.to_json()
    buckets = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::S3::Bucket"
    ]
    assert len(buckets) == 1
    assert "WebsiteConfiguration" not in buckets[0].get("Properties", {})


def test_cloudfront_oac_and_no_legacy_oai(dev_frontend_template: Template) -> None:
    # Origin Access Control (OAC) must be used
    dev_frontend_template.resource_count_is("AWS::CloudFront::OriginAccessControl", 1)
    dev_frontend_template.has_resource_properties(
        "AWS::CloudFront::OriginAccessControl",
        {
            "OriginAccessControlConfig": {
                "OriginAccessControlOriginType": "s3",
                "SigningBehavior": "always",
                "SigningProtocol": "sigv4",
            },
        },
    )
    # Legacy OAI must be absent
    dev_frontend_template.resource_count_is("AWS::CloudFront::CloudFrontOriginAccessIdentity", 0)


def test_cloudfront_distribution_and_behaviors(dev_frontend_template: Template) -> None:
    dev_frontend_template.resource_count_is("AWS::CloudFront::Distribution", 1)
    dev_frontend_template.has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": {
                "DefaultRootObject": "index.html",
                "DefaultCacheBehavior": {
                    "ViewerProtocolPolicy": "redirect-to-https",
                    "FunctionAssociations": Match.array_with([
                        Match.object_like({
                            "EventType": "viewer-request",
                        })
                    ]),
                },
                "CacheBehaviors": Match.array_with([
                    Match.object_like({
                        "PathPattern": "/api/*",
                        "AllowedMethods": [
                            "GET",
                            "HEAD",
                            "OPTIONS",
                            "PUT",
                            "PATCH",
                            "POST",
                            "DELETE",
                        ],
                        "ViewerProtocolPolicy": "redirect-to-https",
                        "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
                        "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",
                    })
                ]),
            },
        },
    )


def test_spa_router_cloudfront_function(dev_frontend_template: Template) -> None:
    dev_frontend_template.resource_count_is("AWS::CloudFront::Function", 1)
    dev_frontend_template.has_resource_properties(
        "AWS::CloudFront::Function",
        {
            "Name": "community-analysis-dev-spa-router",
            "FunctionConfig": {
                "Runtime": "cloudfront-js-2.0",
            },
        },
    )


def test_frontend_cognito_client_and_domain(dev_frontend_template: Template) -> None:
    # No new UserPool in FrontendStack
    dev_frontend_template.resource_count_is("AWS::Cognito::UserPool", 0)

    # One Frontend UserPoolClient
    dev_frontend_template.resource_count_is("AWS::Cognito::UserPoolClient", 1)
    dev_frontend_template.has_resource_properties(
        "AWS::Cognito::UserPoolClient",
        {
            "ClientName": "community-analysis-dev-frontend-client",
            "GenerateSecret": False,
            "AllowedOAuthFlows": ["code"],
            "AllowedOAuthFlowsUserPoolClient": True,
            "AllowedOAuthScopes": ["openid", "email", "profile"],
        },
    )

    # Cognito Domain prefix
    dev_frontend_template.resource_count_is("AWS::Cognito::UserPoolDomain", 1)


def test_dual_audience_jwt_authorizer(dev_frontend_template: Template) -> None:
    dev_frontend_template.resource_count_is("AWS::ApiGatewayV2::Authorizer", 1)
    template_dict = dev_frontend_template.to_json()
    authorizers = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::ApiGatewayV2::Authorizer"
    ]
    assert len(authorizers) == 1
    props = authorizers[0].get("Properties", {})
    assert props.get("AuthorizerType") == "JWT"
    assert props.get("IdentitySource") == ["$request.header.Authorization"]
    jwt_cfg = props.get("JwtConfiguration", {})
    assert "Issuer" in jwt_cfg
    audience = jwt_cfg.get("Audience", [])
    assert len(audience) == 2


def test_protected_api_proxy_route(dev_frontend_template: Template) -> None:
    dev_frontend_template.resource_count_is("AWS::ApiGatewayV2::Route", 1)
    dev_frontend_template.has_resource_properties(
        "AWS::ApiGatewayV2::Route",
        {
            "RouteKey": "ANY /api/{proxy+}",
            "AuthorizationType": "JWT",
            "AuthorizerId": Match.any_value(),
            "Target": Match.any_value(),
        },
    )
    dev_frontend_template.resource_count_is("AWS::ApiGatewayV2::Integration", 1)
    dev_frontend_template.has_resource_properties(
        "AWS::ApiGatewayV2::Integration",
        {
            "IntegrationType": "AWS_PROXY",
            "PayloadFormatVersion": "2.0",
        },
    )


def test_public_health_route_preserved_in_api_stack() -> None:
    app = cdk.App(context={"stage": "dev", "image_tag": "test1234"})
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
        image_tag="test1234",
        env=env,
    )
    api_template = Template.from_stack(api)
    api_template.has_resource_properties(
        "AWS::ApiGatewayV2::Route",
        {
            "RouteKey": "GET /api/v1/health",
            "AuthorizationType": "NONE",
        },
    )


def test_infrastructure_exclusions(dev_frontend_template: Template) -> None:
    # 0 new compute / DB / network / identity resources created by FrontendStack
    dev_frontend_template.resource_count_is("AWS::EC2::VPC", 0)
    dev_frontend_template.resource_count_is("AWS::EC2::NatGateway", 0)
    dev_frontend_template.resource_count_is("AWS::EC2::Instance", 0)
    dev_frontend_template.resource_count_is("AWS::WAFv2::WebACL", 0)
    dev_frontend_template.resource_count_is("AWS::Route53::RecordSet", 0)
    dev_frontend_template.resource_count_is("AWS::CertificateManager::Certificate", 0)
    dev_frontend_template.resource_count_is("AWS::Lambda::Function", 0)
    dev_frontend_template.resource_count_is("AWS::Cognito::UserPool", 0)
    dev_frontend_template.resource_count_is("AWS::ApiGatewayV2::Api", 0)


def test_prod_frontend_stack_zero_lambda_functions() -> None:
    app = cdk.App(context={"stage": "prod", "image_tag": "test1234"})
    stage_config = get_stage_config("prod")
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
        image_tag="test1234",
        env=env,
    )
    frontend = FrontendStack(
        app,
        stage_config.format_stack_name("frontend"),
        stage_config=stage_config,
        http_api=api.http_api,
        user_pool=api.user_pool,
        api_app_client=api.app_client,
        lambda_function=api.lambda_function,
        env=env,
    )
    prod_template = Template.from_stack(frontend)
    prod_template.resource_count_is("AWS::Lambda::Function", 0)


def test_frontend_stack_outputs(dev_frontend_template: Template) -> None:
    dev_frontend_template.has_output("FrontendBucketName", {"Description": "Name of the frontend static assets S3 bucket"})
    dev_frontend_template.has_output("CloudFrontDistributionId", {"Description": "ID of the CloudFront distribution"})
    dev_frontend_template.has_output("CloudFrontDomainName", {"Description": "Domain name of the CloudFront distribution"})
    dev_frontend_template.has_output("FrontendCognitoClientId", {"Description": "ID of the frontend Cognito App Client"})
    dev_frontend_template.has_output("CognitoDomain", {"Description": "Domain prefix of the Cognito User Pool"})
