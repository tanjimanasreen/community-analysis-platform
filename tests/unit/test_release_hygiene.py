from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


CURRENT_OPERATIONAL_DOCS = (
    "README.md",
    "docs/design-docs/pipeline-contract.md",
    "docs/design-docs/output-artifact-contract.md",
    "docs/verification/quality-gates.md",
    "docs/verification/test-matrix.md",
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_documented_make_targets_exist():
    makefile = _read("Makefile")
    targets = set(re.findall(r"^([A-Za-z0-9_.-]+):(?:\s|$)", makefile, re.MULTILINE))

    for path in CURRENT_OPERATIONAL_DOCS:
        documented_targets = re.findall(
            r"^\s*make\s+([A-Za-z0-9_.-]+)\b",
            _read(path),
            re.MULTILINE,
        )
        missing = sorted(set(documented_targets) - targets)
        assert not missing, f"{path} documents missing Make target(s): {missing}"


def test_operational_docs_use_canonical_evolution_targets():
    legacy_commands = {
        "make run-longitudinal-sample",
        "make verify-longitudinal-output-contract",
    }

    for path in CURRENT_OPERATIONAL_DOCS:
        text = _read(path)
        for command in legacy_commands:
            assert command not in text, f"{path} should use canonical evolution targets"


def test_required_make_targets_exist():
    makefile = _read("Makefile")
    targets = {
        "install",
        "install-dev",
        "frontend-install",
        "run-evolution-pipeline-test",
        "run-longitudinal-sample",
        "verify-evolution-output-contract",
        "verify-longitudinal-output-contract",
        "demo",
        "demo-api",
        "demo-frontend",
        "clean-generated",
        "clean-cache",
    }

    for target in targets:
        assert re.search(rf"^{re.escape(target)}:", makefile, re.MULTILINE), target


def test_sample_theme_targets_force_mock_provider_without_global_export():
    makefile = _read("Makefile")

    assert "THEME_PROVIDER := mock" in makefile
    assert "export THEME_PROVIDER" not in makefile
    assert re.search(
        r"^run-theme-sample:\n.*run-theme-analysis --config \$\(SAMPLE_CONFIG\) "
        r"--theme-provider \$\(THEME_PROVIDER\)",
        makefile,
        re.MULTILINE,
    )
    assert re.search(
        r"run-evolution-pipeline --config \$\(TEST_EVOLUTION_CONFIG\) "
        r"--theme-provider \$\(THEME_PROVIDER\)",
        makefile,
    )


def test_provider_settings_load_cwd_dotenv_without_overriding_exported_env(
    monkeypatch, tmp_path
):
    from src.config.settings import get_provider_settings

    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY=dotenv-gemini-placeholder\n"
        "LLM7_API_KEY=dotenv-llm7-placeholder\n"
        "LLM7_BASE_URL=https://dotenv.example/v1\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM7_API_KEY", "exported-llm7-placeholder")

    settings = get_provider_settings()

    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "dotenv-gemini-placeholder"
    assert settings.llm7_api_key is not None
    assert settings.llm7_api_key.get_secret_value() == "exported-llm7-placeholder"
    assert str(settings.llm7_base_url) == "https://dotenv.example/v1"
    assert "GEMINI_API_KEY" not in os.environ


def test_gitignore_protects_generated_files():
    gitignore = _read(".gitignore").splitlines()
    required_patterns = {
        ".venv/",
        "__pycache__/",
        "*.py[cod]",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        "*.egg-info/",
        "build/",
        "dist/",
        "frontend/node_modules/",
        "frontend/dist/",
        ".DS_Store",
    }

    for pattern in required_patterns:
        assert pattern in gitignore


def test_requirements_file_is_small_compatibility_wrapper():
    requirements = _read("requirements.txt")
    non_comment_lines = [
        line.strip()
        for line in requirements.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    assert non_comment_lines == ["-e .[dev]"]
    assert "git+" not in requirements
    assert "http://" not in requirements
    assert "https://" not in requirements
    assert requirements.lower().count("kaleido") <= 1


def test_frontend_lockfile_exists():
    assert (ROOT / "frontend" / "package-lock.json").exists()
