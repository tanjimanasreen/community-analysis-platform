"""Unit tests for GitHub Actions OIDC identity stack (CicdStack)."""

from __future__ import annotations

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from community_analysis_infra.cicd_stack import (
    LEGACY_GITHUB_DEV_SUBJECT,
    CicdStack,
    validate_oidc_subject,
)
from community_analysis_infra.config import get_stage_config


@pytest.fixture
def dev_cicd_template() -> Template:
    app = cdk.App()
    stage_config = get_stage_config("dev")
    env = cdk.Environment(account="123456789012", region="us-east-1")
    stack = CicdStack(
        app,
        stage_config.format_stack_name("cicd"),
        stage_config=stage_config,
        github_oidc_subject=LEGACY_GITHUB_DEV_SUBJECT,
        env=env,
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)
    return Template.from_stack(stack)


def test_cicd_stack_rejects_non_dev() -> None:
    app = cdk.App()
    stage_config = get_stage_config("prod")
    env = cdk.Environment(account="123456789012", region="us-east-1")
    with pytest.raises(ValueError, match="CicdStack currently supports 'dev' only"):
        CicdStack(
            app,
            stage_config.format_stack_name("cicd"),
            stage_config=stage_config,
            github_oidc_subject=LEGACY_GITHUB_DEV_SUBJECT,
            env=env,
        )


def test_cicd_stack_fails_closed_when_subject_missing() -> None:
    app = cdk.App()
    stage_config = get_stage_config("dev")
    env = cdk.Environment(account="123456789012", region="us-east-1")
    with pytest.raises(ValueError, match="github_oidc_subject is required for CI/CD bootstrap synthesis"):
        CicdStack(
            app,
            stage_config.format_stack_name("cicd"),
            stage_config=stage_config,
            github_oidc_subject=None,
            env=env,
        )


def test_oidc_provider_creation_without_static_thumbprints(dev_cicd_template: Template) -> None:
    dev_cicd_template.has_resource_properties(
        "Custom::AWSCDKOpenIdConnectProvider",
        {
            "Url": "https://token.actions.githubusercontent.com",
            "ClientIDList": ["sts.amazonaws.com"],
        },
    )
    # Ensure no hardcoded ThumbprintList is passed
    template_dict = dev_cicd_template.to_json()
    for res in template_dict.get("Resources", {}).values():
        if res.get("Type") == "Custom::AWSCDKOpenIdConnectProvider":
            assert "ThumbprintList" not in res.get("Properties", {})


def test_oidc_provider_import_reference() -> None:
    app = cdk.App()
    stage_config = get_stage_config("dev")
    env = cdk.Environment(account="123456789012", region="us-east-1")
    custom_arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
    stack = CicdStack(
        app,
        stage_config.format_stack_name("cicd"),
        stage_config=stage_config,
        use_existing_oidc_provider=True,
        oidc_provider_arn=custom_arn,
        github_oidc_subject=LEGACY_GITHUB_DEV_SUBJECT,
        env=env,
    )
    template = Template.from_stack(stack)
    template.resource_count_is("Custom::AWSCDKOpenIdConnectProvider", 0)
    assert stack.oidc_provider_arn == custom_arn


def test_validate_oidc_subject() -> None:
    # 1. Legacy exact dev subject accepted
    legacy = "repo:tanjimanasreen/community-analysis-platform:ref:refs/heads/dev"
    assert validate_oidc_subject(legacy) == legacy

    # 2. Immutable exact dev subject accepted (numeric IDs)
    immutable_numeric = "repo:tanjimanasreen@123456/community-analysis-platform@789012:ref:refs/heads/dev"
    assert validate_oidc_subject(immutable_numeric) == immutable_numeric

    # 3. Immutable exact dev subject accepted (alphanumeric/hyphen IDs)
    immutable_alpha = "repo:tanjimanasreen@owner-id_1/community-analysis-platform@repo-id_2:ref:refs/heads/dev"
    assert validate_oidc_subject(immutable_alpha) == immutable_alpha

    # 4. Missing / None / empty string fails closed
    with pytest.raises(ValueError, match="github_oidc_subject is required for CI/CD bootstrap synthesis"):
        validate_oidc_subject(None)
    with pytest.raises(ValueError, match="github_oidc_subject is required for CI/CD bootstrap synthesis"):
        validate_oidc_subject("")
    with pytest.raises(ValueError, match="github_oidc_subject is required for CI/CD bootstrap synthesis"):
        validate_oidc_subject("   ")

    # 5. Rejects wildcards
    with pytest.raises(ValueError, match="wildcard patterns are strictly forbidden"):
        validate_oidc_subject("repo:tanjimanasreen/community-analysis-platform:*")
    with pytest.raises(ValueError, match="wildcard patterns are strictly forbidden"):
        validate_oidc_subject("*")
    with pytest.raises(ValueError, match="wildcard patterns are strictly forbidden"):
        validate_oidc_subject("repo:tanjimanasreen@*/community-analysis-platform@*:ref:refs/heads/dev")

    # 6. Rejects main branch (both legacy and immutable)
    with pytest.raises(ValueError, match="trust for 'main' branch is forbidden in Plan 097"):
        validate_oidc_subject("repo:tanjimanasreen/community-analysis-platform:ref:refs/heads/main")
    with pytest.raises(ValueError, match="trust for 'main' branch is forbidden in Plan 097"):
        validate_oidc_subject("repo:tanjimanasreen@123/community-analysis-platform@456:ref:refs/heads/main")

    # 7. Rejects other branches
    with pytest.raises(ValueError, match="Must strictly match either legacy dev form"):
        validate_oidc_subject("repo:tanjimanasreen/community-analysis-platform:ref:refs/heads/staging")
    with pytest.raises(ValueError, match="Must strictly match either legacy dev form"):
        validate_oidc_subject("repo:tanjimanasreen@123/community-analysis-platform@456:ref:refs/heads/feature")

    # 8. Rejects other repositories
    with pytest.raises(ValueError, match="Must strictly match either legacy dev form"):
        validate_oidc_subject("repo:tanjimanasreen/other-repo:ref:refs/heads/dev")
    with pytest.raises(ValueError, match="Must strictly match either legacy dev form"):
        validate_oidc_subject("repo:tanjimanasreen@123/other-repo@456:ref:refs/heads/dev")

    # 9. Rejects other owners
    with pytest.raises(ValueError, match="Must strictly match either legacy dev form"):
        validate_oidc_subject("repo:otherowner/community-analysis-platform:ref:refs/heads/dev")
    with pytest.raises(ValueError, match="Must strictly match either legacy dev form"):
        validate_oidc_subject("repo:otherowner@123/community-analysis-platform@456:ref:refs/heads/dev")

    # 10. Rejects pull_request subjects
    with pytest.raises(ValueError, match="pull_request subjects are forbidden"):
        validate_oidc_subject("repo:tanjimanasreen/community-analysis-platform:pull_request")

    # 11. Rejects environment subjects
    with pytest.raises(ValueError, match="environment subjects are forbidden in Plan 097"):
        validate_oidc_subject("repo:tanjimanasreen/community-analysis-platform:environment:dev")


def test_trust_policy_exact_string_equals() -> None:
    app = cdk.App()
    stage_config = get_stage_config("dev")
    env = cdk.Environment(account="123456789012", region="us-east-1")
    immutable_sub = "repo:tanjimanasreen@123456/community-analysis-platform@789012:ref:refs/heads/dev"
    stack = CicdStack(
        app,
        stage_config.format_stack_name("cicd"),
        stage_config=stage_config,
        github_oidc_subject=immutable_sub,
        env=env,
    )
    template = Template.from_stack(stack)
    template_dict = template.to_json()
    stack_roles = [
        v for k, v in template_dict.get("Resources", {}).items()
        if v.get("Type") == "AWS::IAM::Role" and not k.startswith("CustomAWSCDK")
    ]
    assert len(stack_roles) == 2
    for role in stack_roles:
        assume_doc = role.get("Properties", {}).get("AssumeRolePolicyDocument", {})
        stmt = assume_doc["Statement"][0]
        # Verify StringEquals is used, NOT StringLike
        conditions = stmt["Condition"]
        assert "StringEquals" in conditions
        assert "StringLike" not in conditions
        sub = conditions["StringEquals"]["token.actions.githubusercontent.com:sub"]
        assert sub == immutable_sub
        aud = conditions["StringEquals"]["token.actions.githubusercontent.com:aud"]
        assert aud == "sts.amazonaws.com"


def test_deploy_role_tei_only_batch_submit_and_narrowed_bootstrap_roles(dev_cicd_template: Template) -> None:
    template_dict = dev_cicd_template.to_json()
    policies = [res for res in template_dict.get("Resources", {}).values() if res.get("Type") == "AWS::IAM::Policy"]

    deploy_policies = []
    for policy in policies:
        roles = policy.get("Properties", {}).get("Roles", [])
        for role_ref in roles:
            if isinstance(role_ref, dict) and "Deploy" in role_ref.get("Ref", ""):
                deploy_policies.append(policy)

    all_statements = []
    for p in deploy_policies:
        all_statements.extend(p.get("Properties", {}).get("PolicyDocument", {}).get("Statement", []))

    all_actions = []
    assume_resources = []
    submit_resources = []
    describe_resources = []
    describe_def_resources = []
    for s in all_statements:
        actions = s.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        all_actions.extend(actions)
        if "sts:AssumeRole" in actions:
            res = s.get("Resource", [])
            assume_resources.extend(res if isinstance(res, list) else [res])
        if "batch:SubmitJob" in actions:
            r = s.get("Resource", [])
            submit_resources.extend(r if isinstance(r, list) else [r])
        if "batch:DescribeJobs" in actions:
            r = s.get("Resource", [])
            describe_resources.extend(r if isinstance(r, list) else [r])
        if "batch:DescribeJobDefinitions" in actions:
            r = s.get("Resource", [])
            describe_def_resources.extend(r if isinstance(r, list) else [r])

    # 1. No batch:TerminateJob
    assert "batch:TerminateJob" not in all_actions
    assert "batch:SubmitJob" in all_actions
    assert "batch:DescribeJobs" in all_actions
    assert "batch:DescribeJobDefinitions" in all_actions
    assert "batch:*" not in all_actions

    # 2. SubmitJob restricted strictly to queue and analytics-tei-job (Remediation 2)
    assert len(submit_resources) == 2
    assert any("community-analysis-dev-queue" in str(r) for r in submit_resources)
    assert any("analytics-tei-job" in str(r) for r in submit_resources)
    # Plain analytics-job MUST NOT be present
    for r in submit_resources:
        r_str = str(r)
        assert "analytics-job" not in r_str
        assert "community-analysis-dev-*" not in r_str

    # 3. DescribeJobs and DescribeJobDefinitions use Resource: "*"
    assert describe_resources == ["*"]
    assert describe_def_resources == ["*"]

    # 4. Narrowed bootstrap role assumption (NO *-role-* wildcard, NO cfn-exec-role)
    assert len(assume_resources) == 4
    for r in assume_resources:
        r_str = str(r)
        assert "*-role-" not in r_str
        assert "cfn-exec-role" not in r_str

    assert any("deploy-role" in str(r) for r in assume_resources)
    assert any("file-publishing-role" in str(r) for r in assume_resources)
    assert any("image-publishing-role" in str(r) for r in assume_resources)
    assert any("lookup-role" in str(r) for r in assume_resources)

    # 5. No admin actions
    assert "*" not in all_actions
    assert "iam:*" not in all_actions
    assert "cloudformation:*" not in all_actions


def test_pipeline_role_strict_scoping_and_no_terminate_job(dev_cicd_template: Template) -> None:
    template_dict = dev_cicd_template.to_json()
    policies = [res for res in template_dict.get("Resources", {}).values() if res.get("Type") == "AWS::IAM::Policy"]

    pipeline_policies = []
    for policy in policies:
        roles = policy.get("Properties", {}).get("Roles", [])
        for role_ref in roles:
            if isinstance(role_ref, dict) and "Pipeline" in role_ref.get("Ref", ""):
                pipeline_policies.append(policy)

    all_statements = []
    for p in pipeline_policies:
        all_statements.extend(p.get("Properties", {}).get("PolicyDocument", {}).get("Statement", []))

    all_actions = []
    submit_resources = []
    describe_resources = []
    describe_def_resources = []
    for s in all_statements:
        actions = s.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        all_actions.extend(actions)
        if "batch:SubmitJob" in actions:
            r = s.get("Resource", [])
            submit_resources.extend(r if isinstance(r, list) else [r])
        if "batch:DescribeJobs" in actions:
            r = s.get("Resource", [])
            describe_resources.extend(r if isinstance(r, list) else [r])
        if "batch:DescribeJobDefinitions" in actions:
            r = s.get("Resource", [])
            describe_def_resources.extend(r if isinstance(r, list) else [r])

    # 1. No batch:TerminateJob
    assert "batch:TerminateJob" not in all_actions
    assert "batch:SubmitJob" in all_actions
    assert "batch:DescribeJobs" in all_actions
    assert "batch:DescribeJobDefinitions" in all_actions
    assert "batch:*" not in all_actions

    # 2. SubmitJob strictly limited to queue and analytics-tei-job
    assert len(submit_resources) == 2
    assert any("community-analysis-dev-queue" in str(r) for r in submit_resources)
    assert any("analytics-tei-job" in str(r) for r in submit_resources)
    for r in submit_resources:
        r_str = str(r)
        assert "analytics-job" not in r_str
        assert "community-analysis-dev-*" not in r_str

    # 3. DescribeJobs and DescribeJobDefinitions use Resource: "*"
    assert describe_resources == ["*"]
    assert describe_def_resources == ["*"]

    # 4. Forbidden actions for pipeline role
    assert "ecr:PutImage" not in all_actions
    assert "s3:PutObject" not in all_actions
    assert "cloudfront:CreateInvalidation" not in all_actions
    assert "sts:AssumeRole" not in all_actions
    assert "cognito-idp:AdminCreateUser" not in all_actions
    assert not any("cloudformation" in act.lower() for act in all_actions)


def test_deploy_role_cloudformation_describe_stacks_narrowly_scoped(dev_cicd_template: Template) -> None:
    """Verify DeployRole has cloudformation:DescribeStacks for API and frontend stacks only."""
    template_dict = dev_cicd_template.to_json()
    policies = [res for res in template_dict.get("Resources", {}).values() if res.get("Type") == "AWS::IAM::Policy"]

    deploy_policies = []
    pipeline_policies = []
    for policy in policies:
        roles = policy.get("Properties", {}).get("Roles", [])
        for role_ref in roles:
            if isinstance(role_ref, dict):
                ref = role_ref.get("Ref", "")
                if "Deploy" in ref:
                    deploy_policies.append(policy)
                elif "Pipeline" in ref:
                    pipeline_policies.append(policy)

    all_statements = []
    for p in deploy_policies:
        all_statements.extend(p.get("Properties", {}).get("PolicyDocument", {}).get("Statement", []))

    cfn_statements = []
    for s in all_statements:
        actions = s.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        if any("cloudformation" in a.lower() for a in actions):
            cfn_statements.append(s)

    # 1. Exactly one CloudFormation statement in DeployRole
    assert len(cfn_statements) == 1
    cfn_stmt = cfn_statements[0]

    # 2. Action is exactly cloudformation:DescribeStacks
    actions = cfn_stmt.get("Action", [])
    if isinstance(actions, str):
        actions = [actions]
    assert actions == ["cloudformation:DescribeStacks"]

    # 3. No mutation actions in any statement of DeployRole
    all_actions = []
    for s in all_statements:
        act = s.get("Action", [])
        all_actions.extend([act] if isinstance(act, str) else act)

    forbidden_cfn_actions = [
        "cloudformation:*",
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:ExecuteChangeSet",
        "cloudformation:CreateChangeSet",
        "cloudformation:DeleteChangeSet",
    ]
    for forbidden in forbidden_cfn_actions:
        assert forbidden not in all_actions

    # 4. Resources include exactly community-analysis-dev-api/* and community-analysis-dev-frontend/*
    resources = cfn_stmt.get("Resource", [])
    if isinstance(resources, str):
        resources = [resources]
    assert len(resources) == 2
    res_str = [str(r) for r in resources]

    assert any("stack/community-analysis-dev-api/*" in r for r in res_str)
    assert any("stack/community-analysis-dev-frontend/*" in r for r in res_str)

    # 5. Resources do NOT include wildcard '*' or other stacks
    assert "*" not in res_str
    assert not any("community-analysis-dev-cicd" in r for r in res_str)
    assert not any("community-analysis-dev-batch" in r for r in res_str)
    assert not any("community-analysis-dev-storage" in r for r in res_str)
    assert not any("community-analysis-dev-registry" in r for r in res_str)

    # 6. PipelineRole has zero CloudFormation actions
    pipeline_statements = []
    for p in pipeline_policies:
        pipeline_statements.extend(p.get("Properties", {}).get("PolicyDocument", {}).get("Statement", []))

    pipeline_actions = []
    for s in pipeline_statements:
        act = s.get("Action", [])
        pipeline_actions.extend([act] if isinstance(act, str) else act)

    assert not any("cloudformation" in a.lower() for a in pipeline_actions)


def test_cicd_stack_outputs(dev_cicd_template: Template) -> None:
    dev_cicd_template.has_output(
        "DeployRoleArn",
        {
            "Description": "ARN of the dev deployment role for GitHub Actions cd.yml",
        },
    )
    dev_cicd_template.has_output(
        "PipelineRoleArn",
        {
            "Description": "ARN of the dev evolution pipeline runner role for GitHub Actions run-evolution.yml",
        },
    )


def test_pipeline_role_max_session_duration(dev_cicd_template: Template) -> None:
    """Verify PipelineRole has 4-hour (14400s) MaxSessionDuration while DeployRole does not."""
    dev_cicd_template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "RoleName": "community-analysis-dev-github-pipeline",
            "MaxSessionDuration": 14400,
        },
    )

    template_dict = dev_cicd_template.to_json()
    roles = {
        v.get("Properties", {}).get("RoleName"): v.get("Properties", {}).get("MaxSessionDuration")
        for v in template_dict.get("Resources", {}).values()
        if v.get("Type") == "AWS::IAM::Role" and not v.get("Properties", {}).get("RoleName", "").startswith("Custom")
    }
    assert roles.get("community-analysis-dev-github-pipeline") == 14400
    assert roles.get("community-analysis-dev-github-deploy") is None
