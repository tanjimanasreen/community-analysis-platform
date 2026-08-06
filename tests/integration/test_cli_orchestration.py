import pytest
from unittest.mock import patch
from pathlib import Path
import yaml
import sys
from src.cli import main


@pytest.fixture
def sample_config_path(tmp_path):
    orig_path = "tests/configs/test_single_month.yml"
    with open(orig_path, "r") as f:
        config = yaml.safe_load(f)
    config["output_base_path"] = str(tmp_path / "output")
    new_path = tmp_path / "test_config.yml"
    with open(new_path, "w") as f:
        yaml.dump(config, f)
    return str(new_path)


def test_cli_defaults_to_prefect(sample_config_path, monkeypatch, capsys):
    """
    Test that running the CLI without --debug triggers Prefect
    and initializes MLflow tracking correctly.
    """
    monkeypatch.setattr(
        sys, "argv", ["cli.py", "run-all", "--config", sample_config_path]
    )

    from prefect.testing.utilities import prefect_test_harness

    with (
        patch(
            "src.orchestration.composition_flow.run_monthly_analysis_flow"
        ) as mock_flow,
        prefect_test_harness(),
    ):
        main()

        mock_flow.assert_called_once()

    captured = capsys.readouterr()
    assert "Running run-all via Prefect orchestrator..." in captured.out
    assert "Prefect flow finished successfully!" in captured.out


def test_cli_debug_mode(sample_config_path, monkeypatch, capsys):
    """
    Test that running the CLI with --debug bypasses Prefect
    and executes the raw pipeline directly.
    """
    monkeypatch.setattr(
        sys, "argv", ["cli.py", "run-all", "--config", sample_config_path, "--debug"]
    )

    from prefect.testing.utilities import prefect_test_harness

    with (
        patch(
            "src.pipelines.social_network_pipeline.run_full_pipeline"
        ) as mock_pipeline,
        prefect_test_harness(),
    ):
        main()

        mock_pipeline.assert_called_once()

    captured = capsys.readouterr()
    assert "Running run-all in local DEBUG mode (no Prefect)" in captured.out
    assert "Running run-all via Prefect orchestrator..." not in captured.out
    assert "Running full network/community/topic pipeline..." in captured.out
