"""Unit tests for RegistryStack and ECR repository security and configuration."""

import json
import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Match, Template
from community_analysis_infra.config import get_stage_config
from community_analysis_infra.registry_stack import RegistryStack


@pytest.fixture
def dev_registry_template() -> Template:
    app = cdk.App(context={"stage": "dev"})
    stage_config = get_stage_config("dev")
    stack = RegistryStack(
        app,
        stage_config.format_stack_name("registry"),
        stage_config=stage_config,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)
    return Template.from_stack(stack)


@pytest.fixture
def prod_registry_template() -> Template:
    app = cdk.App(context={"stage": "prod"})
    stage_config = get_stage_config("prod")
    stack = RegistryStack(
        app,
        stage_config.format_stack_name("registry"),
        stage_config=stage_config,
        env=cdk.Environment(account="123456789012", region="us-east-1"),
    )
    for key, value in stage_config.tags.items():
        cdk.Tags.of(app).add(key, value)
    return Template.from_stack(stack)


def test_registry_stack_resource_counts(dev_registry_template: Template) -> None:
    # Exactly one ECR repository, 0 KMS keys, 0 IAM roles
    dev_registry_template.resource_count_is("AWS::ECR::Repository", 1)
    dev_registry_template.resource_count_is("AWS::KMS::Key", 0)
    dev_registry_template.resource_count_is("AWS::IAM::Role", 0)


def test_ecr_repository_name(dev_registry_template: Template, prod_registry_template: Template) -> None:
    dev_registry_template.has_resource_properties(
        "AWS::ECR::Repository",
        {"RepositoryName": "community-analysis-dev-api"},
    )
    prod_registry_template.has_resource_properties(
        "AWS::ECR::Repository",
        {"RepositoryName": "community-analysis-prod-api"},
    )


def test_ecr_repository_immutable_tags(dev_registry_template: Template) -> None:
    dev_registry_template.has_resource_properties(
        "AWS::ECR::Repository",
        {"ImageTagMutability": "IMMUTABLE"},
    )


def test_ecr_repository_encryption_is_default_aes256(
    dev_registry_template: Template, prod_registry_template: Template
) -> None:
    # ECR defaults to AES-256 server-side encryption without requiring a customer KMS key
    for template in [dev_registry_template, prod_registry_template]:
        template.resource_count_is("AWS::KMS::Key", 0)
        template_dict = template.to_json()
        repos = [
            res for res in template_dict.get("Resources", {}).values()
            if res.get("Type") == "AWS::ECR::Repository"
        ]
        assert len(repos) == 1
        encryption_config = repos[0].get("Properties", {}).get("EncryptionConfiguration")
        if encryption_config is not None:
            assert encryption_config.get("EncryptionType") == "AES256"
            assert "KmsKey" not in encryption_config


def test_ecr_repository_lifecycle_policy_structured(dev_registry_template: Template) -> None:
    template_dict = dev_registry_template.to_json()
    repos = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::ECR::Repository"
    ]
    assert len(repos) == 1
    lifecycle = repos[0].get("Properties", {}).get("LifecyclePolicy", {})
    policy_text = lifecycle.get("LifecyclePolicyText", "")
    assert policy_text, "LifecyclePolicyText must be non-empty"

    policy_json = json.loads(policy_text)
    rules = policy_json.get("rules", [])
    assert len(rules) == 1, f"Expected exactly 1 lifecycle rule, got {len(rules)}"

    rule = rules[0]
    selection = rule.get("selection", {})
    action = rule.get("action", {})

    assert selection.get("tagStatus") == "untagged"
    assert selection.get("countType") == "sinceImagePushed"
    assert selection.get("countUnit") == "days"
    assert selection.get("countNumber") == 1
    assert action.get("type") == "expire"

    # Confirm NO tagged image expiration rule exists in Plan 091
    tagged_rules = [r for r in rules if r.get("selection", {}).get("tagStatus") == "tagged"]
    assert len(tagged_rules) == 0, "No tagged image expiration rule should exist in Plan 091"

    # Confirm NO count-based image capping rule exists in Plan 091
    count_rules = [r for r in rules if r.get("selection", {}).get("countType") == "imageCountMoreThan"]
    assert len(count_rules) == 0, "No imageCountMoreThan rule should exist in Plan 091"


def test_ecr_repository_empty_on_delete_and_removal_policy_dev(dev_registry_template: Template) -> None:
    dev_registry_template.has_resource_properties(
        "AWS::ECR::Repository",
        {"EmptyOnDelete": True},
    )
    template_dict = dev_registry_template.to_json()
    repos = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::ECR::Repository"
    ]
    assert len(repos) == 1
    assert repos[0].get("DeletionPolicy") == "Delete"
    assert repos[0].get("UpdateReplacePolicy") == "Delete"


def test_ecr_repository_empty_on_delete_and_removal_policy_prod(prod_registry_template: Template) -> None:
    prod_registry_template.has_resource_properties(
        "AWS::ECR::Repository",
        {"EmptyOnDelete": False},
    )
    template_dict = prod_registry_template.to_json()
    repos = [
        res for res in template_dict.get("Resources", {}).values()
        if res.get("Type") == "AWS::ECR::Repository"
    ]
    assert len(repos) == 1
    assert repos[0].get("DeletionPolicy") == "Retain"
    assert repos[0].get("UpdateReplacePolicy") == "Retain"


def test_ecr_repository_scan_on_push_is_absent(
    dev_registry_template: Template, prod_registry_template: Template
) -> None:
    # Repository-level scan on push is deprecated and should NOT be configured in the template
    for template in [dev_registry_template, prod_registry_template]:
        template_dict = template.to_json()
        repos = [
            res for res in template_dict.get("Resources", {}).values()
            if res.get("Type") == "AWS::ECR::Repository"
        ]
        assert len(repos) == 1
        props = repos[0].get("Properties", {})
        assert "ImageScanningConfiguration" not in props


def test_ecr_repository_outputs(dev_registry_template: Template) -> None:
    dev_registry_template.has_output(
        "RepositoryName",
        {"Description": "Name of the API container repository"},
    )
    dev_registry_template.has_output(
        "RepositoryArn",
        {"Description": "ARN of the API container repository"},
    )
    dev_registry_template.has_output(
        "RepositoryUri",
        {"Description": "URI of the API container repository"},
    )


def test_ecr_repository_standard_tags(dev_registry_template: Template) -> None:
    dev_registry_template.has_resource_properties(
        "AWS::ECR::Repository",
        {
            "Tags": Match.array_with(
                [
                    {"Key": "Environment", "Value": "dev"},
                    {"Key": "ManagedBy", "Value": "aws-cdk"},
                    {"Key": "Project", "Value": "community-analysis"},
                ]
            )
        },
    )
