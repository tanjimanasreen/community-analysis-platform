from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_required_make_targets_exist():
    makefile = _read("Makefile")
    targets = {
        "install",
        "install-dev",
        "frontend-install",
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

    assert "OFFLINE_LLM_PROVIDER := mock" in makefile
    assert "export LLM_PROVIDER" not in makefile
    assert re.search(
        r"^run-theme-sample:\n\tLLM_PROVIDER=\$\(OFFLINE_LLM_PROVIDER\).*run-theme-analysis",
        makefile,
        re.MULTILINE,
    )
    assert re.search(
        r"\n\tLLM_PROVIDER=\$\(OFFLINE_LLM_PROVIDER\).*run-theme-analysis --config \$\(LONGITUDINAL_CONFIG_04\)",
        makefile,
    )


def test_theme_benchmark_dotenv_loader_uses_cwd_env_without_overwrite(
    monkeypatch, tmp_path
):
    from src.cli import _load_benchmark_dotenv

    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY=dotenv-gemini-placeholder\n"
        "LLM7_API_KEY=dotenv-llm7-placeholder\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM7_API_KEY", "exported-llm7-placeholder")

    _load_benchmark_dotenv()

    assert os.environ["GEMINI_API_KEY"] == "dotenv-gemini-placeholder"
    assert os.environ["LLM7_API_KEY"] == "exported-llm7-placeholder"


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


def test_frontend_lockfile_exists_and_unused_libraries_removed():
    package = json.loads(_read("frontend/package.json"))
    dependencies = package.get("dependencies", {})

    removed_libraries = {"react-force-graph-2d", "react-router-dom", "recharts"}
    assert (ROOT / "frontend" / "package-lock.json").exists()
    assert removed_libraries.isdisjoint(dependencies)
