from __future__ import annotations

import json
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
