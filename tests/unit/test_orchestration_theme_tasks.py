import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from prefect.testing.utilities import prefect_test_harness
from prefect import flow

from src.orchestration.models import ThemeInputBundle, ThemeOutputBundle, ValidatedRunConfiguration, PipelineRunContext, ArtifactReference
from src.orchestration.tasks import run_monthly_themes_task
from src.orchestration.retry_policy import PipelineError

@pytest.fixture(autouse=True)
def prefect_test_fixture():
    with prefect_test_harness():
        yield

def test_run_monthly_themes_task_validates_inputs(tmp_path):
    """Test that the task explicitly checks for input bundle file existence."""
    context = PipelineRunContext.create(
        pipeline_run_id="run-123",
        git_commit="commit",
        config_digest="digest",
        output_root=str(tmp_path),
        datasets=[]
    )
    config = ValidatedRunConfiguration(
        config_digest="digest",
        output_root=str(tmp_path),
        raw_config={"month": "march", "year": "2017"}
    )

    # Missing file
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "march": ArtifactReference(path="/fake/path.csv", sha256="0"*64, media_type="text/csv")
        }
    )

    with pytest.raises(PipelineError, match="Missing required theme input"):
        run_monthly_themes_task.fn(bundle, config, context)

@patch("src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data")
def test_run_monthly_themes_task_success(mock_run_theme, tmp_path):
    """Test that the task correctly constructs output references after domain logic execution."""
    
    # Setup mock inputs
    march_path = tmp_path / "march.csv"
    march_path.write_text("dummy")

    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "march": ArtifactReference(path=str(march_path), sha256="0"*64, media_type="text/csv")
        }
    )

    context = PipelineRunContext.create(
        pipeline_run_id="run-123",
        git_commit="commit",
        config_digest="digest",
        output_root=str(tmp_path),
        datasets=[]
    )
    config = ValidatedRunConfiguration(
        config_digest="digest",
        output_root=str(tmp_path),
        raw_config={"month": "march", "year": "2017", "data_type": "twitter", "content_type": "reply"}
    )

    # Mock domain function to create expected outputs
    def fake_run_themes(*args, **kwargs):
        out_dir = kwargs["output_dir"]

        # Create theme outputs
        with open(os.path.join(out_dir, "march_2017_with_themes.csv"), "w") as f:
            f.write("themes")

        with open(os.path.join(out_dir, "community_transition.csv"), "w") as f:
            f.write("transitions")

        # Create some visualization files
        sankey_dir = os.path.join(out_dir, "sankey")
        os.makedirs(sankey_dir, exist_ok=True)
        with open(os.path.join(sankey_dir, "test.html"), "w") as f:
            f.write("<html>")

    mock_run_theme.side_effect = fake_run_themes

    # Execute task
    result = run_monthly_themes_task.fn(bundle, config, context)

    assert isinstance(result, ThemeOutputBundle)
    assert len(result.themes) == 1
    assert result.themes[0].asset_key == "themes_march"
    
    assert result.community_transitions is not None
    assert result.community_transitions.asset_key == "community_transitions"

    assert len(result.visualizations) == 1
    assert result.visualizations[0].asset_key == "visualization_sankey_test.html"
    
    assert result.provider_run_summary is not None
    assert result.provider_run_summary.asset_key == "provider_run_summary"
    
    mock_run_theme.assert_called_once()
    # Ensure provider=None is passed (domain logic should initialize it)
    assert mock_run_theme.call_args[1].get("provider") is None
