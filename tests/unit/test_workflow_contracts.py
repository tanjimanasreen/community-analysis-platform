"""Static contract verification tests for GitHub Actions workflows."""

from __future__ import annotations

from pathlib import Path
import yaml


def _load_workflow(filename: str) -> dict:
    path = Path(".github/workflows") / filename
    assert path.is_file(), f"Workflow file {path} does not exist"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_ci_workflow_contract() -> None:
    wf = _load_workflow("ci.yml")

    # 1. Source-validation only permissions (no AWS credentials)
    assert wf.get("permissions") == {"contents": "read"}
    raw_text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "id-token: write" not in raw_text
    assert "aws-actions/configure-aws-credentials" not in raw_text

    # 2. No duplicate make test execution
    assert "make test-unit" in raw_text
    assert "make test-integration" in raw_text
    # Ensure 'make test' alone (full suite duplicate) is not in steps
    assert "run: make test\n" not in raw_text


def test_cd_workflow_contract() -> None:
    wf = _load_workflow("cd.yml")
    raw_text = Path(".github/workflows/cd.yml").read_text(encoding="utf-8")
    triggers = wf.get("on") or wf.get(True) or {}

    # 1. Manual trigger only
    assert "workflow_dispatch" in triggers
    assert "push" not in triggers
    assert "pull_request" not in triggers

    # 2. Environment options restricted to dev
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["environment"]["options"] == ["dev"]

    # 3. Uses Deploy Role via OIDC
    assert "vars.AWS_DEV_DEPLOY_ROLE_ARN" in raw_text
    assert "id-token: write" in raw_text

    # 4. Calls aws_cd.py with required flags
    assert "python scripts/aws_cd.py" in raw_text
    assert "--environment dev" in raw_text
    assert "--acceptance-config" in raw_text
    assert "--acceptance-theme-provider mock" in raw_text

    # 5. Provisions isolated infra/.venv before calling aws_cd.py
    assert "uv venv infra/.venv" in raw_text
    assert "uv pip install" in raw_text
    assert "infra/requirements.txt" in raw_text

    deploy_steps = wf["jobs"]["deploy"]["steps"]
    infra_step_idx = None
    cd_step_idx = None
    for idx, step in enumerate(deploy_steps):
        step_run = step.get("run", "")
        if "uv venv infra/.venv" in step_run and "infra/requirements.txt" in step_run:
            infra_step_idx = idx
        if "python scripts/aws_cd.py" in step_run:
            cd_step_idx = idx

    assert infra_step_idx is not None, "infra/.venv provisioning step missing in deploy job"
    assert cd_step_idx is not None, "scripts/aws_cd.py execution step missing in deploy job"
    assert (
        infra_step_idx < cd_step_idx
    ), "infra/.venv must be provisioned before scripts/aws_cd.py is executed"


def test_run_evolution_workflow_contract() -> None:
    wf = _load_workflow("run-evolution.yml")
    raw_text = Path(".github/workflows/run-evolution.yml").read_text(encoding="utf-8")
    triggers = wf.get("on") or wf.get(True) or {}

    # 1. Manual trigger only
    assert "workflow_dispatch" in triggers
    assert "push" not in triggers
    assert "pull_request" not in triggers

    # 2. Environment options restricted to dev
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["environment"]["options"] == ["dev"]

    # 3. Canonical dataset choices
    dataset_options = inputs["dataset"]["options"]
    assert "telegram-forwarded" in dataset_options
    assert "twitter-reply" in dataset_options
    assert "twitter-retweet-quote" in dataset_options

    # 4. Uses Pipeline Role via OIDC (strictly isolated from deploy role)
    assert "vars.AWS_DEV_PIPELINE_ROLE_ARN" in raw_text
    assert "vars.AWS_DEV_DEPLOY_ROLE_ARN" not in raw_text
    assert "id-token: write" in raw_text

    # 5. Calls aws_run_evolution.py
    assert "python scripts/aws_run_evolution.py" in raw_text
    assert "--environment dev" in raw_text

    # 6. Strictly NO deployment actions
    assert "cdk deploy" not in raw_text
    assert "docker build" not in raw_text
    assert "docker push" not in raw_text
    assert "npm run build" not in raw_text
    assert "aws s3 sync" not in raw_text

    # 7. No operational API verification (CD responsibility only)
    assert "--verify-api" not in raw_text
