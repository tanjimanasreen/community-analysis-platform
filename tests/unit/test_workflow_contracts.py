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

    # 2. Unified CI validation gate (single source of truth with no duplicate test execution)
    assert "make ci-validate" in raw_text
    assert "make test-unit" not in raw_text
    assert "make test-integration" not in raw_text


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

    # 4. Calls scripts.aws_cd in module mode with required flags
    assert "python -m scripts.aws_cd" in raw_text
    assert "python scripts/aws_cd.py" not in raw_text
    assert "--environment dev" in raw_text
    assert "--acceptance-config" in raw_text
    assert "--acceptance-theme-provider mock" in raw_text

    # 5. Provisions isolated infra/.venv before calling scripts.aws_cd
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
        if "python -m scripts.aws_cd" in step_run:
            cd_step_idx = idx

    assert infra_step_idx is not None, "infra/.venv provisioning step missing in deploy job"
    assert cd_step_idx is not None, "scripts.aws_cd module execution step missing in deploy job"
    assert (
        infra_step_idx < cd_step_idx
    ), "infra/.venv must be provisioned before scripts.aws_cd is executed"


def test_cd_module_imports() -> None:
    """Verify scripts.aws_cd and scripts.aws_run_evolution can be imported as modules from repo root."""
    import scripts.aws_cd
    import scripts.aws_run_evolution

    assert scripts.aws_cd is not None
    assert scripts.aws_run_evolution is not None


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

    # 8. Theme mode input contract (constrained to canonical and mock only)
    assert "theme_mode" in inputs
    theme_mode_input = inputs["theme_mode"]
    assert theme_mode_input.get("type") == "choice"
    assert theme_mode_input.get("required") is True
    assert theme_mode_input.get("default") == "canonical"
    assert theme_mode_input.get("options") == ["canonical", "mock"]
    assert set(inputs.keys()) == {"environment", "dataset", "theme_mode"}

    # 9. Passes theme mode to scripts/aws_run_evolution.py
    assert '--theme-mode "${{ inputs.theme_mode }}"' in raw_text

    # 10. No arbitrary provider/model or TEI overrides exposed in workflow
    assert "openai" not in raw_text
    assert "gemini" not in raw_text
    assert "mistral" not in raw_text
    assert "llm7" not in raw_text
    assert "nvidia" not in raw_text
    assert "THEME_SIMILARITY_PROVIDER" not in raw_text
    assert "THEME_CLUSTERING_PROVIDER" not in raw_text
    assert "TEI_SIMILARITY_BASE_URL" not in raw_text
    assert "TEI_CLUSTERING_BASE_URL" not in raw_text

    # 11. Role session duration contract (4 hours / 14400s covering the 235-minute job timeout)
    assert "role-duration-seconds: 14400" in raw_text
    run_job = wf["jobs"]["run-evolution"]
    timeout_minutes = run_job.get("timeout-minutes")
    assert timeout_minutes == 235
    assert 14400 >= timeout_minutes * 60

    oidc_steps = [
        s for s in run_job["steps"]
        if "aws-actions/configure-aws-credentials" in s.get("uses", "")
    ]
    assert len(oidc_steps) == 1
    assert oidc_steps[0]["with"]["role-duration-seconds"] == 14400


def test_evolution_timeout_hierarchy_contract() -> None:
    """Verify timeout hierarchy: runner (13200s / 220m) < GitHub (235m / 14100s) < OIDC (14400s / 240m),
    and Batch attempt timeout (7200s) with 2 retry attempts.
    """
    import inspect
    from scripts.aws_run_evolution import wait_for_batch_job

    # 1. Workflow timeout = 235 minutes (14100 seconds)
    wf = _load_workflow("run-evolution.yml")
    workflow_timeout_minutes = wf["jobs"]["run-evolution"]["timeout-minutes"]
    assert workflow_timeout_minutes == 235
    workflow_timeout_seconds = workflow_timeout_minutes * 60

    # 2. GitHub OIDC role duration remains 14400 seconds (240 minutes)
    oidc_steps = [
        s for s in wf["jobs"]["run-evolution"]["steps"]
        if "aws-actions/configure-aws-credentials" in s.get("uses", "")
    ]
    assert len(oidc_steps) == 1
    oidc_duration_seconds = oidc_steps[0]["with"]["role-duration-seconds"]
    assert oidc_duration_seconds == 14400

    # 3. Runner default timeout = 13200 seconds (220 minutes)
    runner_default_timeout = inspect.signature(wait_for_batch_job).parameters["timeout_seconds"].default
    assert runner_default_timeout == 13200.0

    # Hierarchy verification: runner 220 min < GitHub 235 min < OIDC 240 min
    assert runner_default_timeout < workflow_timeout_seconds < oidc_duration_seconds
    assert runner_default_timeout == 220 * 60
    assert workflow_timeout_seconds == 235 * 60
    assert oidc_duration_seconds == 240 * 60

    # 4. Batch attempt timeout remains 7200 seconds
    # 5. Batch retry attempts remain 2
    batch_stack_text = Path("infra/community_analysis_infra/batch_stack.py").read_text(encoding="utf-8")
    assert "attempt_duration_seconds=7200" in batch_stack_text
    assert "attempts=2" in batch_stack_text
    assert "timeout=cdk.Duration.seconds(7200)" in batch_stack_text
    assert "retry_attempts=2" in batch_stack_text



def test_makefile_cd_preflight_contract() -> None:
    """Verify Makefile defines cd-preflight and runs all required local CD checks."""
    makefile_text = Path("Makefile").read_text(encoding="utf-8")
    assert "cd-preflight:" in makefile_text
    assert "cd-preflight" in makefile_text
    assert "import aws_cdk" in makefile_text
    assert "import scripts.aws_cd; import scripts.aws_run_evolution" in makefile_text
    assert "test_workflow_contracts.py" in makefile_text
    assert "test_aws_cd.py" in makefile_text


def test_makefile_ci_validate_contract() -> None:
    """Verify Makefile defines ci-validate reproducing all CI gates."""
    makefile_text = Path("Makefile").read_text(encoding="utf-8")
    assert "ci-validate:" in makefile_text
    assert "lock --check" in makefile_text
    assert "sync --frozen" in makefile_text
    assert "$(MAKE) lint" in makefile_text or "make lint" in makefile_text or "pre-commit" in makefile_text
    assert "$(MAKE) test" in makefile_text or "make test" in makefile_text
    assert "cd-preflight" in makefile_text
    assert "git diff --check" in makefile_text
