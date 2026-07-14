import os
import pytest
import pandas as pd
from unittest.mock import patch
from pathlib import Path

from prefect.testing.utilities import prefect_test_harness
from src.orchestration.models import (
    TopicInputBundle,
    ThemeInputBundle,
    ValidatedRunConfiguration,
    PipelineRunContext,
    ArtifactReference
)
from src.orchestration.tasks import (
    run_monthly_topic_phase_task,
    run_monthly_themes_task,
)

@pytest.fixture(autouse=True, scope="module")
def prefect_test_fixture():
    with prefect_test_harness():
        yield

@pytest.fixture
def run_config(tmp_path):
    return ValidatedRunConfiguration(
        config_digest="dummy",
        output_root=str(tmp_path),
        raw_config={
            "lda": {"num_topics": 2, "top_n_keywords": 10},
            "database": {"uri": "mock"},
            "graph_thresholds": {"min_total_post": 1},
            "data_type": "twitter",
            "content_type": "reply",
            "month": "03",
            "year": "2017",
            "render_visuals": True
        }
    )

@pytest.fixture
def context(tmp_path):
    return PipelineRunContext.create(
        pipeline_run_id="smoke",
        git_commit="HEAD",
        config_digest="dummy",
        output_root=str(tmp_path),
        datasets=[]
    )

def test_smoke_topic_phase_alone(tmp_path, run_config, context):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()

    abs_csv = input_dir / "abs.csv"
    pd.DataFrame({"community": [1], "messages": ["hello"]}).to_csv(abs_csv, index=False)

    wgt_csv = input_dir / "wgt.csv"
    pd.DataFrame({"community": [1], "messages": ["hello"]}).to_csv(wgt_csv, index=False)

    match_csv = input_dir / "match.csv"
    pd.DataFrame({"community": [1], "matched_community": [1]}).to_csv(match_csv, index=False)

    def make_ref(p):
        import hashlib
        return ArtifactReference(
            path=str(p),
            sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            media_type="text/csv",
            byte_size=p.stat().st_size
        )

    bundle = TopicInputBundle(
        absolute_community_messages=make_ref(abs_csv),
        weighted_community_messages=make_ref(wgt_csv),
        matched_communities=make_ref(match_csv),
        partial_matched_communities=None,
        allowed_input_roots=(str(input_dir),)
    )

    def mock_domain(*args, **kwargs):
        out_dir = kwargs.get("output_dir")
        paths = [
            "twitter/LDA/scores/reply/03.csv",
            "twitter/LDA/matched/reply/03_2017.csv",
            "twitter/LDA/partial_matched/reply/03_2017.csv",
            "twitter/_intermediate/theme_inputs/reply/03_2017/manifest.json"
        ]
        for p in paths:
            full_path = os.path.join(out_dir, p)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            if p.endswith(".json"):
                with open(full_path, "w") as f:
                    f.write("{}")
            else:
                pd.DataFrame({"x": [1]}).to_csv(full_path, index=False)

    with patch("src.pipelines.social_network_pipeline.run_topic_phase", side_effect=mock_domain):
        res = run_monthly_topic_phase_task.fn(bundle, run_config, context)
        assert res.lda_scores is not None
        assert res.matched_communities_topics is not None
        assert len(res.theme_inputs) == 1

def test_smoke_theme_phase_alone(tmp_path, run_config, context):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()

    csv_path = input_dir / "topic_output.csv"
    pd.DataFrame({"x": [1]}).to_csv(csv_path, index=False)

    import hashlib
    ref = ArtifactReference(
        path=str(csv_path),
        sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        media_type="text/csv",
        byte_size=csv_path.stat().st_size
    )

    bundle = ThemeInputBundle(
        monthly_topic_outputs={"03": ref},
        allowed_input_roots=(str(input_dir),)
    )

    def mock_domain(*args, **kwargs):
        out_dir = kwargs.get("output_dir")
        pd.DataFrame({"x": [1]}).to_csv(os.path.join(out_dir, "03_2017_with_themes.csv"), index=False)
        pd.DataFrame({"x": [1]}).to_csv(os.path.join(out_dir, "community_transition.csv"), index=False)

        # visualizations
        sankey_dir = os.path.join(out_dir, "sankey")
        os.makedirs(sankey_dir, exist_ok=True)
        Path(os.path.join(sankey_dir, "test.png")).write_bytes(b"pngdata")

    with patch("src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data", side_effect=mock_domain):
        res = run_monthly_themes_task.fn(bundle, run_config, context)
        assert res.community_transitions is not None
        assert len(res.themes) == 1
        assert len(res.visualizations) == 1
        assert res.provider_run_summary is not None

def test_smoke_composition_topic_and_theme(tmp_path, run_config, context):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()

    abs_csv = input_dir / "abs.csv"
    pd.DataFrame({"community": [1], "messages": ["hello"]}).to_csv(abs_csv, index=False)

    wgt_csv = input_dir / "wgt.csv"
    pd.DataFrame({"community": [1], "messages": ["hello"]}).to_csv(wgt_csv, index=False)

    match_csv = input_dir / "match.csv"
    pd.DataFrame({"community": [1], "matched_community": [1]}).to_csv(match_csv, index=False)

    def make_ref(p):
        import hashlib
        return ArtifactReference(
            path=str(p),
            sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            media_type="text/csv",
            byte_size=p.stat().st_size
        )

    topic_bundle = TopicInputBundle(
        absolute_community_messages=make_ref(abs_csv),
        weighted_community_messages=make_ref(wgt_csv),
        matched_communities=make_ref(match_csv),
        partial_matched_communities=None,
        allowed_input_roots=(str(input_dir),)
    )

    def mock_topic_domain(*args, **kwargs):
        out_dir = kwargs.get("output_dir")
        paths = [
            "twitter/LDA/scores/reply/03.csv",
            "twitter/LDA/matched/reply/03_2017.csv",
            "twitter/LDA/partial_matched/reply/03_2017.csv",
            "twitter/_intermediate/theme_inputs/reply/03_2017/manifest.json"
        ]
        for p in paths:
            full_path = os.path.join(out_dir, p)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            if p.endswith(".json"):
                with open(full_path, "w") as f:
                    f.write("{}")
            else:
                pd.DataFrame({"x": [1]}).to_csv(full_path, index=False)

    def mock_theme_domain(*args, **kwargs):
        out_dir = kwargs.get("output_dir")
        pd.DataFrame({"x": [1]}).to_csv(os.path.join(out_dir, "03_2017_with_themes.csv"), index=False)
        pd.DataFrame({"x": [1]}).to_csv(os.path.join(out_dir, "community_transition.csv"), index=False)

    with patch("src.pipelines.social_network_pipeline.run_topic_phase", side_effect=mock_topic_domain):
        topic_res = run_monthly_topic_phase_task.fn(topic_bundle, run_config, context)

    theme_bundle = ThemeInputBundle(
        monthly_topic_outputs={"03": topic_res.matched_communities_topics},
        allowed_input_roots=(context.output_root,)
    )

    with patch("src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data", side_effect=mock_theme_domain):
        theme_res = run_monthly_themes_task.fn(theme_bundle, run_config, context)

    assert theme_res.themes[0].path.endswith("03_2017_with_themes.csv")

def test_result_boundary_isolation():
    """
    Ensure the TopicOutputBundle completely insulates the ThemeInputBundle structurally,
    so Theme tasks cannot accidentally load DataFrames serialized by the Topic layer.
    """
    from src.orchestration.models import TopicOutputBundle, ArtifactReference

    # Prove that TopicOutputBundle ONLY contains ArtifactReference or tuple[ArtifactReference]
    # No DataFrames can exist in the bundle.
    fields = TopicOutputBundle.__annotations__
    for field_name, field_type in fields.items():
        assert "DataFrame" not in str(field_type)
        assert "ArtifactReference" in str(field_type) or field_type.__name__ == 'str' or str(field_type).startswith('typing.Optional')

    fields = ThemeInputBundle.__annotations__
    for field_name, field_type in fields.items():
        assert "DataFrame" not in str(field_type)
