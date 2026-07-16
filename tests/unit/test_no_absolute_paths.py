"""Regression guard — zero tolerance for absolute paths in configs/.

If this test fails, a YAML file in configs/ has a hardcoded absolute path.
Replace it with a relative path or ${ENV_VAR} interpolation.
See .env.example for the list of supported env vars.
"""

import re
import yaml
from pathlib import Path

# Regex matching absolute paths that are likely machine-specific
ABSOLUTE_PATH_RE = re.compile(r":\s*(/Users/|/home/|/root/|/Volumes/|C:\\Users\\)")

CONFIGS_ROOT = Path(__file__).resolve().parents[2] / "configs"


def _yaml_files():
    return list(CONFIGS_ROOT.rglob("*.yml")) + list(CONFIGS_ROOT.rglob("*.yaml"))


def test_no_absolute_paths_in_configs():
    """No YAML in configs/ should contain a hardcoded machine-specific absolute path."""
    violations = []
    for yaml_path in _yaml_files():
        text = yaml_path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if ABSOLUTE_PATH_RE.search(line):
                violations.append(
                    f"{yaml_path.relative_to(CONFIGS_ROOT)}:{line_no}  →  {line.strip()}"
                )

    if violations:
        report = "\n".join(violations)
        raise AssertionError(
            f"Machine-specific absolute paths found in {len(violations)} config line(s):\n{report}\n\n"
            "Replace with project-relative paths, valid user-supplied absolute paths, or ${{ENV_VAR}} interpolation."
        )


def test_canonical_paths_used_for_dataset_paths():
    """Committed dataset configs should use ${DATA_ROOT} or data/raw/ for external file paths."""
    dataset_dir = CONFIGS_ROOT / "datasets"
    violations = []
    for yaml_path in dataset_dir.rglob("*.yml"):
        with yaml_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        for ds in config.get("datasets", []):
            input_path = str(ds.get("input_path", "")).strip()
            if not input_path:
                continue

            if not (
                input_path.startswith("${DATA_ROOT}")
                or input_path.startswith("data/raw/")
            ):
                violations.append(
                    f"{yaml_path.relative_to(CONFIGS_ROOT)}: dataset '{ds.get('id', 'unknown')}' "
                    f"has non-canonical input_path '{input_path}'"
                )

    if violations:
        report = "\n".join(violations)
        raise AssertionError(
            f"Non-canonical input_path found in dataset configs:\n{report}\n\n"
            "Committed defaults must use canonical paths like ${{DATA_ROOT}}/... or data/raw/... "
            "for external data file references."
        )


def test_runtime_data_root_override(monkeypatch):
    """Ensure runtime DATA_ROOT securely overrides paths dynamically without modifying configs."""
    from src.config.loader import load_config

    config_path = CONFIGS_ROOT / "datasets" / "retweet_2017.yml"

    # Test default behavior (data/raw)
    monkeypatch.setenv("DATA_ROOT", "data/raw")
    default_config = load_config(config_path)
    for ds in default_config.get("datasets", []):
        assert str(ds.get("input_path")).startswith(
            "data/raw/twitter/retweet_quote/2017/"
        ), f"Default DATA_ROOT did not resolve correctly for {ds.get('id')}"

    # Test override behavior (/mnt/research-data)
    monkeypatch.setenv("DATA_ROOT", "/mnt/research-data")
    override_config = load_config(config_path)
    for ds in override_config.get("datasets", []):
        assert str(ds.get("input_path")).startswith(
            "/mnt/research-data/twitter/retweet_quote/2017/"
        ), f"Overridden DATA_ROOT did not resolve correctly for {ds.get('id')}"
