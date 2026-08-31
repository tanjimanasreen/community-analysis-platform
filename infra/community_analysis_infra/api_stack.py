"""API stack definition for community-analysis authenticated Lambda and HTTP API."""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import (
    aws_apigatewayv2 as apigw2,
    aws_apigatewayv2_authorizers as apigw2_auth,
    aws_apigatewayv2_integrations as apigw2_integrations,
    aws_cognito as cognito,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
)
from constructs import Construct
from community_analysis_infra.config import StageConfig


class ApiStack(cdk.Stack):
    """Authenticated API serving infrastructure stack.

    Provisions:
      - Amazon Cognito User Pool & App Client (JWT authentication)
      - AWS Lambda container function (ARM64 Graviton2 with Lambda Web Adapter)
      - Dedicated CloudWatch Log Group with 7-day dev retention
      - Least-privilege read-only S3 IAM execution role
      - API Gateway HTTP API (v2) with JWT authorizer ( protected, /health public)
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        stage_config: StageConfig,
        bucket: s3.IBucket,
        repository: ecr.IRepository,
        image_tag: str,
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

        if not image_tag or not str(image_tag).strip():
            raise ValueError(
                "image_tag is required for ApiStack. Pass via CDK context: -c image_tag=<GIT_SHA>"
            )

        self.stage_config = stage_config
        self.image_tag = str(image_tag).strip()

        is_dev = stage_config.stage_name == "dev"
        removal_policy = cdk.RemovalPolicy.DESTROY if is_dev else cdk.RemovalPolicy.RETAIN

        # 1. Cognito User Pool & App Client
        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"{stage_config.project_name}-{stage_config.stage_name}-user-pool",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True, username=True),
            removal_policy=removal_policy,
        )

        self.app_client = self.user_pool.add_client(
            "ApiClient",
            user_pool_client_name=f"{stage_config.project_name}-{stage_config.stage_name}-api-client",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True,
            ),
        )

        # 2. CloudWatch Log Group
        log_group_name = f"/aws/lambda/{stage_config.project_name}-{stage_config.stage_name}-api"
        self.log_group = logs.LogGroup(
            self,
            "ApiLogGroup",
            log_group_name=log_group_name,
            retention=logs.RetentionDays.ONE_WEEK if is_dev else logs.RetentionDays.ONE_MONTH,
            removal_policy=removal_policy,
        )

        # 3. IAM Execution Role
        self.execution_role = iam.Role(
            self,
            "ApiLambdaRole",
            role_name=f"{stage_config.project_name}-{stage_config.stage_name}-api-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )

        # 4. Lambda Container Function
        self.lambda_function = lambda_.DockerImageFunction(
            self,
            "ApiFunction",
            function_name=f"{stage_config.project_name}-{stage_config.stage_name}-api",
            code=lambda_.DockerImageCode.from_ecr(
                repository=repository,
                tag_or_digest=self.image_tag,
            ),
            architecture=lambda_.Architecture.ARM_64,
            memory_size=1024,
            timeout=cdk.Duration.seconds(30),
            role=self.execution_role,
            log_group=self.log_group,
            environment={
                "COMMUNITY_ANALYSIS_STORAGE_BACKEND": "s3",
                "COMMUNITY_ANALYSIS_S3_BUCKET": bucket.bucket_name,
                "COMMUNITY_ANALYSIS_S3_REGION": self.region or cdk.Aws.REGION,
                "COMMUNITY_ANALYSIS_API_ALLOWED_HOSTS": "*",
                "AWS_LWA_PORT": "8000",
                "AWS_LWA_READINESS_CHECK_PATH": "/api/v1/health",
                "AWS_LWA_READINESS_CHECK_HEALTHY_STATUS": "200-399",
                "LOG_FORMAT": "json",
                "LOG_LEVEL": "INFO",
            },
        )

        # 5. Read-only S3 permissions on Plan-089 bucket
        bucket.grant_read(self.execution_role)

        # 6. API Gateway HTTP API (v2) with Cognito JWT Authorizer
        self.authorizer = apigw2_auth.HttpJwtAuthorizer(
            "CognitoAuthorizer",
            jwt_issuer=self.user_pool.user_pool_provider_url,
            jwt_audience=[self.app_client.user_pool_client_id],
        )

        integration = apigw2_integrations.HttpLambdaIntegration(
            "ApiLambdaIntegration",
            handler=self.lambda_function,
        )

        self.http_api = apigw2.HttpApi(
            self,
            "HttpApi",
            api_name=f"{stage_config.project_name}-{stage_config.stage_name}-api",
            description=f"HTTP API serving community-analysis read-only artifacts ({stage_config.stage_name})",
            default_integration=integration,
            default_authorizer=self.authorizer,
        )

        # Public process health route overrides default authorizer
        self.http_api.add_routes(
            path="/api/v1/health",
            methods=[apigw2.HttpMethod.GET],
            integration=integration,
            authorizer=apigw2.HttpNoneAuthorizer(),
        )

        # 7. CloudFormation Outputs
        cdk.CfnOutput(
            self,
            "ApiEndpoint",
            value=self.http_api.api_endpoint,
            description="URL of the HTTP API",
        )

        cdk.CfnOutput(
            self,
            "LambdaFunctionName",
            value=self.lambda_function.function_name,
            description="Name of the API Lambda function",
        )

        cdk.CfnOutput(
            self,
            "CognitoUserPoolId",
            value=self.user_pool.user_pool_id,
            description="ID of the Cognito User Pool",
        )

        cdk.CfnOutput(
            self,
            "CognitoAppClientId",
            value=self.app_client.user_pool_client_id,
            description="ID of the Cognito App Client",
        )

        cdk.CfnOutput(
            self,
            "DeployedImageTag",
            value=self.image_tag,
            description="Immutable ECR image tag deployed",
        )
