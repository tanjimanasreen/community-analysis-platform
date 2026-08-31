"""Frontend stack definition for community-analysis S3 hosting, CloudFront CDN, and browser Cognito auth."""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import (
    aws_apigatewayv2 as apigw2,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_cognito as cognito,
    aws_lambda as lambda_,
    aws_s3 as s3,
)
from constructs import Construct
from community_analysis_infra.config import StageConfig


class FrontendStack(cdk.Stack):
    """Frontend infrastructure stack.

    Provisions:
      - Private S3 bucket for frontend Vite SPA static assets (SSE-S3, SSL enforced)
      - CloudFront Origin Access Control (OAC) for secure S3 bucket access
      - CloudFront Function for extensionless SPA client routing (/ -> /index.html)
      - CloudFront Distribution (/* -> private S3 with OAC, /api/* -> existing API Gateway)
      - Amazon Cognito frontend App Client (PKCE authorization code grant, no client secret)
      - Amazon Cognito managed-login domain prefix
      - Dual-audience API Gateway JWT Authorizer and ANY /api/{proxy+} route accepting both API and frontend clients
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        stage_config: StageConfig,
        http_api: apigw2.IHttpApi,
        user_pool: cognito.IUserPool,
        api_app_client: cognito.IUserPoolClient,
        lambda_function: lambda_.IFunction,
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
        is_dev = stage_config.stage_name == "dev"
        removal_policy = cdk.RemovalPolicy.DESTROY if is_dev else cdk.RemovalPolicy.RETAIN

        # 1. Private Frontend S3 Bucket
        bucket_name = (
            f"{stage_config.project_name}-{stage_config.stage_name}-"
            f"{cdk.Aws.ACCOUNT_ID}-{cdk.Aws.REGION}-frontend"
        )

        self.frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=False,
            removal_policy=removal_policy,
            auto_delete_objects=False,
        )

        # 2. CloudFront Function for SPA Client-Side Routing
        spa_code = (
            "function handler(event) {\n"
            "    var request = event.request;\n"
            "    var uri = request.uri;\n"
            "    if (uri.startsWith('/api/')) {\n"
            "        return request;\n"
            "    }\n"
            "    var lastSegment = uri.substring(uri.lastIndexOf('/') + 1);\n"
            "    if (!lastSegment.includes('.')) {\n"
            "        request.uri = '/index.html';\n"
            "    }\n"
            "    return request;\n"
            "}\n"
        )

        self.spa_router_function = cloudfront.Function(
            self,
            "SpaRouterFunction",
            function_name=f"{stage_config.project_name}-{stage_config.stage_name}-spa-router",
            comment="Rewrites extensionless frontend SPA routes to /index.html",
            code=cloudfront.FunctionCode.from_inline(spa_code),
            runtime=cloudfront.FunctionRuntime.JS_2_0,
        )

        # 3. Origins: S3 (OAC) and API Gateway
        s3_origin = origins.S3BucketOrigin.with_origin_access_control(self.frontend_bucket)
        api_origin = origins.HttpOrigin(
            f"{http_api.http_api_id}.execute-api.{self.region or cdk.Aws.REGION}.amazonaws.com"
        )

        # 4. CloudFront Distribution
        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            comment=f"Frontend CDN and API Gateway distribution for {stage_config.project_name} ({stage_config.stage_name})",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=s3_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                function_associations=[
                    cloudfront.FunctionAssociation(
                        function=self.spa_router_function,
                        event_type=cloudfront.FunctionEventType.VIEWER_REQUEST,
                    )
                ],
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=api_origin,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                )
            },
        )

        # 5. Frontend Cognito App Client
        self.frontend_client = cognito.UserPoolClient(
            self,
            "FrontendClient",
            user_pool=user_pool,
            user_pool_client_name=f"{stage_config.project_name}-{stage_config.stage_name}-frontend-client",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(
                user_srp=True,
                user_password=True,
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=[f"https://{self.distribution.distribution_domain_name}"],
                logout_urls=[f"https://{self.distribution.distribution_domain_name}"],
            ),
        )

        # 6. Cognito Managed Domain
        domain_prefix = f"{stage_config.project_name}-{stage_config.stage_name}-{cdk.Aws.ACCOUNT_ID}"
        self.cognito_domain = cognito.UserPoolDomain(
            self,
            "UserPoolDomain",
            user_pool=user_pool,
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=domain_prefix,
            ),
        )

        # 7. Dual-Audience JWT Authorizer (accepts both Plan-092 API client and Plan-093 Frontend client)
        self.api_authorizer = apigw2.CfnAuthorizer(
            self,
            "FrontendApiAuthorizer",
            api_id=http_api.http_api_id,
            authorizer_type="JWT",
            identity_source=["$request.header.Authorization"],
            name=f"{stage_config.project_name}-{stage_config.stage_name}-dual-jwt-authorizer",
            jwt_configuration=apigw2.CfnAuthorizer.JWTConfigurationProperty(
                issuer=user_pool.user_pool_provider_url,
                audience=[
                    api_app_client.user_pool_client_id,
                    self.frontend_client.user_pool_client_id,
                ],
            ),
        )

        # 8. API Gateway Integration targeting existing Plan-092 Lambda container
        self.proxy_integration = apigw2.CfnIntegration(
            self,
            "FrontendProxyIntegration",
            api_id=http_api.http_api_id,
            integration_type="AWS_PROXY",
            integration_uri=lambda_function.function_arn,
            payload_format_version="2.0",
        )

        # 9. Explicit Protected Route for all /api/{proxy+} requests
        self.proxy_route = apigw2.CfnRoute(
            self,
            "FrontendApiProxyRoute",
            api_id=http_api.http_api_id,
            route_key="ANY /api/{proxy+}",
            authorization_type="JWT",
            authorizer_id=self.api_authorizer.ref,
            target=cdk.Fn.join("/", ["integrations", self.proxy_integration.ref]),
        )

        # 10. Permission for API Gateway to invoke existing Lambda for proxy route
        self.proxy_permission = lambda_.CfnPermission(
            self,
            "FrontendProxyRoutePermission",
            action="lambda:InvokeFunction",
            function_name=lambda_function.function_name,
            principal="apigateway.amazonaws.com",
            source_arn=cdk.Fn.join(
                "",
                [
                    "arn:",
                    cdk.Aws.PARTITION,
                    ":execute-api:",
                    cdk.Aws.REGION,
                    ":",
                    cdk.Aws.ACCOUNT_ID,
                    ":",
                    http_api.http_api_id,
                    "/*/*",
                ],
            ),
        )

        # 11. CloudFormation Outputs
        cdk.CfnOutput(
            self,
            "FrontendBucketName",
            value=self.frontend_bucket.bucket_name,
            description="Name of the frontend static assets S3 bucket",
        )

        cdk.CfnOutput(
            self,
            "CloudFrontDistributionId",
            value=self.distribution.distribution_id,
            description="ID of the CloudFront distribution",
        )

        cdk.CfnOutput(
            self,
            "CloudFrontDomainName",
            value=self.distribution.distribution_domain_name,
            description="Domain name of the CloudFront distribution",
        )

        cdk.CfnOutput(
            self,
            "FrontendCognitoClientId",
            value=self.frontend_client.user_pool_client_id,
            description="ID of the frontend Cognito App Client",
        )

        cdk.CfnOutput(
            self,
            "CognitoDomain",
            value=self.cognito_domain.domain_name,
            description="Domain prefix of the Cognito User Pool",
        )
