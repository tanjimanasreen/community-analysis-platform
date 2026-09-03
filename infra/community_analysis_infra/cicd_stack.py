"""AWS CDK Stack for GitHub Actions OIDC identity and CI/CD roles.

Provisions:
- GitHub OIDC Identity Provider (https://token.actions.githubusercontent.com)
  or imports existing provider if configured
- Dev Deployment IAM Role (community-analysis-dev-github-deploy) for cd.yml
- Dev Operational Pipeline Runner IAM Role (community-analysis-dev-github-pipeline) for run-evolution.yml
- Least-privilege IAM policies scoped to dev resources
- CloudFormation outputs for DeployRoleArn and PipelineRoleArn
"""

from __future__ import annotations

import re

import aws_cdk as cdk
import aws_cdk.aws_iam as iam
import constructs

from community_analysis_infra.config import StageConfig

GITHUB_OIDC_URL = "https://token.actions.githubusercontent.com"
GITHUB_OIDC_AUDIENCE = "sts.amazonaws.com"
GITHUB_REPOSITORY = "tanjimanasreen/community-analysis-platform"

LEGACY_GITHUB_DEV_SUBJECT = (
    "repo:tanjimanasreen/community-analysis-platform:ref:refs/heads/dev"
)
IMMUTABLE_GITHUB_DEV_SUBJECT_PATTERN = re.compile(
    r"^repo:tanjimanasreen@[a-zA-Z0-9_-]+/community-analysis-platform@[a-zA-Z0-9_-]+:ref:refs/heads/dev$"
)


def validate_oidc_subject(subject: str | None) -> str:
    """Validate GitHub Actions OIDC subject condition string.

    Enforces fail-closed validation:
    - Must be an explicit non-empty string (no silent fallback)
    - Must strictly match either the legacy name-based dev subject:
      'repo:tanjimanasreen/community-analysis-platform:ref:refs/heads/dev'
      OR the immutable owner/repo ID dev subject:
      'repo:tanjimanasreen@<owner_id>/community-analysis-platform@<repo_id>:ref:refs/heads/dev'
    - Rejects wildcards ('*'), main branch, other branches, PR subjects, environment subjects,
      other repositories, and other owners.
    """
    if subject is None or not str(subject).strip():
        raise ValueError(
            "github_oidc_subject is required for CI/CD bootstrap synthesis. "
            "Pass via CDK context: -c github_oidc_subject=<EXACT_SUBJECT> or "
            "environment: GITHUB_OIDC_SUBJECT=<EXACT_SUBJECT>\n"
            "Accepted forms:\n"
            f"  1. Legacy: '{LEGACY_GITHUB_DEV_SUBJECT}'\n"
            "  2. Immutable: 'repo:tanjimanasreen@<owner_id>/community-analysis-platform@<repo_id>:ref:refs/heads/dev'"
        )

    cleaned = str(subject).strip()

    if "*" in cleaned:
        raise ValueError(
            f"Unsafe OIDC subject '{cleaned}': wildcard patterns are strictly forbidden"
        )
    if "ref:refs/heads/main" in cleaned or cleaned.endswith(":main"):
        raise ValueError(
            f"Unsafe OIDC subject '{cleaned}': trust for 'main' branch is forbidden in Plan 097 "
            "(Plan 098 covers production)"
        )
    if ":environment:" in cleaned:
        raise ValueError(
            f"Unsafe OIDC subject '{cleaned}': environment subjects are forbidden in Plan 097 "
            "(must target dev branch ref)"
        )
    if ":pull_request" in cleaned:
        raise ValueError(
            f"Unsafe OIDC subject '{cleaned}': pull_request subjects are forbidden"
        )

    # Check exact approved forms
    if cleaned == LEGACY_GITHUB_DEV_SUBJECT:
        return cleaned
    if IMMUTABLE_GITHUB_DEV_SUBJECT_PATTERN.fullmatch(cleaned):
        return cleaned

    raise ValueError(
        f"Unsafe or unsupported OIDC subject '{cleaned}'. Must strictly match either legacy dev form "
        f"'{LEGACY_GITHUB_DEV_SUBJECT}' or immutable dev form "
        "'repo:tanjimanasreen@<owner_id>/community-analysis-platform@<repo_id>:ref:refs/heads/dev'"
    )


class CicdStack(cdk.Stack):
    """CDK stack managing GitHub Actions OIDC identity provider and roles for dev."""

    def __init__(
        self,
        scope: constructs.Construct,
        construct_id: str,
        *,
        stage_config: StageConfig,
        use_existing_oidc_provider: bool = False,
        oidc_provider_arn: str | None = None,
        github_oidc_subject: str | None = None,
        cdk_qualifier: str = "hnb659fds",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if stage_config.stage_name != "dev":
            raise ValueError(
                f"CicdStack currently supports 'dev' only. Stage '{stage_config.stage_name}' "
                "is out of scope for Plan 097 (Plan 098 covers production)."
            )

        self.stage_config = stage_config
        project = stage_config.project_name
        stage = stage_config.stage_name

        # 1. GitHub OIDC Provider (create via L2 construct without hardcoded thumbprints, or import existing)
        if use_existing_oidc_provider or oidc_provider_arn:
            resolved_provider_arn = (
                oidc_provider_arn
                or f"arn:{self.partition}:iam::{self.account}:oidc-provider/token.actions.githubusercontent.com"
            )
            self.oidc_provider_arn = resolved_provider_arn
        else:
            self.oidc_provider = iam.OpenIdConnectProvider(
                self,
                "GitHubOidcProvider",
                url=GITHUB_OIDC_URL,
                client_ids=[GITHUB_OIDC_AUDIENCE],
            )
            self.oidc_provider_arn = self.oidc_provider.open_id_connect_provider_arn

        # Exact repository and branch trust condition (fail-closed, no default, exact StringEquals only)
        self.oidc_subject = validate_oidc_subject(github_oidc_subject)

        oidc_principal = iam.FederatedPrincipal(
            federated=self.oidc_provider_arn,
            conditions={
                "StringEquals": {
                    f"{GITHUB_OIDC_URL.replace('https://', '')}:aud": GITHUB_OIDC_AUDIENCE,
                    f"{GITHUB_OIDC_URL.replace('https://', '')}:sub": self.oidc_subject,
                }
            },
            assume_role_action="sts:AssumeRoleWithWebIdentity",
        )

        # 2. Dev Deploy Role (for cd.yml)
        deploy_role_name = f"{project}-{stage}-github-deploy"
        self.deploy_role = iam.Role(
            self,
            "GitHubDeployRole",
            role_name=deploy_role_name,
            assumed_by=oidc_principal,
            description="GitHub Actions role for deploying dev application stacks and running acceptance",
        )

        # 2a. CDK Bootstrap Role Assume Policy (explicitly scoped; cfn-exec-role is NEVER assumable)
        allowed_bootstrap_roles = [
            f"arn:{self.partition}:iam::{self.account}:role/cdk-{cdk_qualifier}-deploy-role-{self.account}-{self.region}",
            f"arn:{self.partition}:iam::{self.account}:role/cdk-{cdk_qualifier}-file-publishing-role-{self.account}-{self.region}",
            f"arn:{self.partition}:iam::{self.account}:role/cdk-{cdk_qualifier}-image-publishing-role-{self.account}-{self.region}",
            f"arn:{self.partition}:iam::{self.account}:role/cdk-{cdk_qualifier}-lookup-role-{self.account}-{self.region}",
        ]
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="CdkBootstrapRoleAssume",
                effect=iam.Effect.ALLOW,
                actions=["sts:AssumeRole"],
                resources=allowed_bootstrap_roles,
            )
        )

        # 2b. ECR Push & Pull Policies for approved dev repositories
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="EcrGetAuthToken",
                effect=iam.Effect.ALLOW,
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],
            )
        )
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="EcrRepositoryScopedDevAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:PutImage",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload",
                    "ecr:DescribeImages",
                    "ecr:DescribeRepositories",
                    "ecr:ListImages",
                ],
                resources=[
                    f"arn:{self.partition}:ecr:{self.region}:{self.account}:repository/{project}-{stage}-api",
                    f"arn:{self.partition}:ecr:{self.region}:{self.account}:repository/{project}-{stage}-analytics",
                    f"arn:{self.partition}:ecr:{self.region}:{self.account}:repository/{project}-{stage}-tei",
                ],
            )
        )

        # 2c. Frontend S3 & CloudFront Invalidation Policies
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="FrontendBucketPublish",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:DeleteObject",
                ],
                resources=[
                    f"arn:{self.partition}:s3:::{project}-{stage}-*-frontend",
                    f"arn:{self.partition}:s3:::{project}-{stage}-*-frontend/*",
                ],
            )
        )
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudFrontInvalidateDevDistribution",
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudfront:CreateInvalidation",
                    "cloudfront:GetInvalidation",
                ],
                resources=[
                    f"arn:{self.partition}:cloudfront::{self.account}:distribution/*",
                ],
            )
        )

        # 2d. Batch Acceptance Run & Verification Policies
        # Split by AWS IAM resource scoping requirements: SubmitJob is resource-scoped, DescribeJobs/DescribeJobDefinitions require *
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="BatchSubmitAcceptance",
                effect=iam.Effect.ALLOW,
                actions=["batch:SubmitJob"],
                resources=[
                    f"arn:{self.partition}:batch:{self.region}:{self.account}:job-queue/{project}-{stage}-queue",
                    f"arn:{self.partition}:batch:{self.region}:{self.account}:job-definition/{project}-{stage}-analytics-tei-job:*",
                ],
            )
        )
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="BatchDescribeJobsAcceptance",
                effect=iam.Effect.ALLOW,
                actions=["batch:DescribeJobs", "batch:DescribeJobDefinitions"],
                resources=["*"],
            )
        )
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="StorageBucketAcceptanceRead",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                ],
                resources=[
                    f"arn:{self.partition}:s3:::{project}-{stage}-*-data",
                    f"arn:{self.partition}:s3:::{project}-{stage}-*-data/runs/*",
                    f"arn:{self.partition}:s3:::{project}-{stage}-*-data/reports/*",
                    f"arn:{self.partition}:s3:::{project}-{stage}-*-data/raw/*",
                ],
            )
        )
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudWatchLogsAcceptanceRead",
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:GetLogEvents",
                    "logs:FilterLogEvents",
                    "logs:DescribeLogStreams",
                    "logs:DescribeLogGroups",
                ],
                resources=[
                    f"arn:{self.partition}:logs:{self.region}:{self.account}:log-group:/aws/batch/job/{project}-{stage}*",
                    f"arn:{self.partition}:logs:{self.region}:{self.account}:log-group:/aws/lambda/{project}-{stage}*",
                ],
            )
        )

        # 2e. Temporary Cognito Smoke User Operations for CD Live Smoke Testing
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="CognitoTemporarySmokeUserOps",
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminSetUserPassword",
                    "cognito-idp:AdminInitiateAuth",
                    "cognito-idp:AdminDeleteUser",
                ],
                resources=[
                    f"arn:{self.partition}:cognito-idp:{self.region}:{self.account}:userpool/*",
                ],
            )
        )

        # 2f. CloudFormation Read Application Stack Outputs for CD acceptance and smoke testing
        self.deploy_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudFormationReadApplicationStackOutputs",
                effect=iam.Effect.ALLOW,
                actions=["cloudformation:DescribeStacks"],
                resources=[
                    f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{project}-{stage}-api/*",
                    f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{project}-{stage}-frontend/*",
                ],
            )
        )

        # 3. Dev Pipeline Runner Role (for run-evolution.yml)
        # MUST NOT have CloudFormation, ECR push, IAM, CDK, or Frontend sync permissions
        pipeline_role_name = f"{project}-{stage}-github-pipeline"
        self.pipeline_role = iam.Role(
            self,
            "GitHubPipelineRole",
            role_name=pipeline_role_name,
            assumed_by=oidc_principal,
            description="GitHub Actions operational role for submitting and verifying evolution pipeline Batch runs",
        )

        # 3a. Batch Job Submission & Observation (SubmitJob strictly scoped to analytics-tei-job only)
        self.pipeline_role.add_to_policy(
            iam.PolicyStatement(
                sid="BatchSubmitEvolution",
                effect=iam.Effect.ALLOW,
                actions=["batch:SubmitJob"],
                resources=[
                    f"arn:{self.partition}:batch:{self.region}:{self.account}:job-queue/{project}-{stage}-queue",
                    f"arn:{self.partition}:batch:{self.region}:{self.account}:job-definition/{project}-{stage}-analytics-tei-job:*",
                ],
            )
        )
        self.pipeline_role.add_to_policy(
            iam.PolicyStatement(
                sid="BatchDescribeJobsEvolution",
                effect=iam.Effect.ALLOW,
                actions=["batch:DescribeJobs", "batch:DescribeJobDefinitions"],
                resources=["*"],
            )
        )

        # 3b. S3 Manifest & Artifact Verification Read
        self.pipeline_role.add_to_policy(
            iam.PolicyStatement(
                sid="StorageBucketManifestRead",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                ],
                resources=[
                    f"arn:{self.partition}:s3:::{project}-{stage}-*-data",
                    f"arn:{self.partition}:s3:::{project}-{stage}-*-data/runs/*",
                    f"arn:{self.partition}:s3:::{project}-{stage}-*-data/reports/*",
                ],
            )
        )

        # 3c. CloudWatch Logs for Job Diagnosis and Run ID discovery
        self.pipeline_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudWatchLogsEvolutionRead",
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:GetLogEvents",
                    "logs:FilterLogEvents",
                    "logs:DescribeLogStreams",
                ],
                resources=[
                    f"arn:{self.partition}:logs:{self.region}:{self.account}:log-group:/aws/batch/job/{project}-{stage}*",
                ],
            )
        )

        # 4. Stack Outputs
        cdk.CfnOutput(
            self,
            "DeployRoleArn",
            value=self.deploy_role.role_arn,
            description="ARN of the dev deployment role for GitHub Actions cd.yml",
        )
        cdk.CfnOutput(
            self,
            "PipelineRoleArn",
            value=self.pipeline_role.role_arn,
            description="ARN of the dev evolution pipeline runner role for GitHub Actions run-evolution.yml",
        )
