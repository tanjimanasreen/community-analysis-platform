import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import os

from prefect.testing.utilities import prefect_test_harness
from prefect import flow

from src.orchestration.models import TopicInputBundle, TopicOutputBundle, ValidatedRunConfiguration, PipelineRunContext, ArtifactReference
from src.orchestration.tasks import run_monthly_topic_phase_task
from src.orchestration.retry_policy import PipelineError

@pytest.fixture(autouse=True)
def prefect_test_fixture():
    with prefect_test_harness():
        yield

def test_run_monthly_topic_phase_task_validates_inputs(tmp_path):
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
    
    # Missing input paths
    bundle = TopicInputBundle(
        absolute_community_messages=ArtifactReference(path="/fake/abs.csv", sha256="0"*64, media_type="text/csv"),
        weighted_community_messages=ArtifactReference(path="/fake/per.csv", sha256="0"*64, media_type="text/csv"),
        matched_communities=ArtifactReference(path="/fake/match.csv", sha256="0"*64, media_type="text/csv"),
        partial_matched_communities=None
    )
    
    with pytest.raises(PipelineError, match="Missing absolute community messages"):
        run_monthly_topic_phase_task.fn(bundle, config, context)

@patch("src.pipelines.social_network_pipeline.run_topic_phase")
def test_run_monthly_topic_phase_task_success(mock_run_topic_phase, tmp_path):
    """Test that the task correctly constructs output references after domain logic execution."""
    
    # Setup mock inputs
    abs_path = tmp_path / "abs.csv"
    per_path = tmp_path / "per.csv"
    match_path = tmp_path / "match.csv"
    for p in [abs_path, per_path, match_path]:
        p.write_text("dummy")
        
    bundle = TopicInputBundle(
        absolute_community_messages=ArtifactReference(path=str(abs_path), sha256="0"*64, media_type="text/csv"),
        weighted_community_messages=ArtifactReference(path=str(per_path), sha256="0"*64, media_type="text/csv"),
        matched_communities=ArtifactReference(path=str(match_path), sha256="0"*64, media_type="text/csv"),
        partial_matched_communities=None
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

    # Mock domain function to create the expected outputs
    def fake_run_topic_phase(*args, **kwargs):
        out_dir = kwargs["output_dir"]
        
        # Create lda_scores
        scores_dir = os.path.join(out_dir, "twitter", "LDA", "scores", "reply")
        os.makedirs(scores_dir, exist_ok=True)
        with open(os.path.join(scores_dir, "march.csv"), "w") as f:
            f.write("scores")
            
        # Create matched
        matched_dir = os.path.join(out_dir, "twitter", "LDA", "matched", "reply")
        os.makedirs(matched_dir, exist_ok=True)
        with open(os.path.join(matched_dir, "march_2017.csv"), "w") as f:
            f.write("matched")
            
        # Create manifest
        manifest_dir = os.path.join(out_dir, "twitter", "_intermediate", "theme_inputs", "reply", "march_2017")
        os.makedirs(manifest_dir, exist_ok=True)
        with open(os.path.join(manifest_dir, "manifest.json"), "w") as f:
            f.write("{}")

    mock_run_topic_phase.side_effect = fake_run_topic_phase

    # Execute task
    result = run_monthly_topic_phase_task.fn(bundle, config, context)
    
    assert isinstance(result, TopicOutputBundle)
    assert result.lda_scores.asset_key == "lda_scores"
    assert result.matched_communities_topics is not None
    assert result.matched_communities_topics.asset_key == "matched_communities_topics"
    assert result.partial_matched_communities_topics is None
    
    assert len(result.theme_inputs) == 1
    assert result.theme_inputs[0].asset_key == "theme_manifest"
