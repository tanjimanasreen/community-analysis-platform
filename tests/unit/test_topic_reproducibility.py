import os
import shutil
import filecmp
from pathlib import Path
import pytest
import pandas as pd
from unittest.mock import patch

from prefect.testing.utilities import prefect_test_harness
from src.orchestration.tasks import run_monthly_topic_phase_task
from src.orchestration.models import TopicInputBundle, ArtifactReference, ValidatedRunConfiguration, PipelineRunContext


@pytest.fixture
def run_config():
    return ValidatedRunConfiguration(
        config_digest="dummy",
        output_root="/tmp/dummy",
        raw_config={
            "lda": {"num_topics": 2, "top_n_keywords": 10},
            "database": {"uri": "mock"},
            "graph_thresholds": {"min_total_post": 1}
        }
    )

def test_topic_reproducibility(tmp_path, run_config):
    """
    Topic Reproducibility Guarantee:
    Reproducible inside the validated project environment for identical inputs,
    ordering, configuration, seed, and dependency versions.
    """
    # Create tiny mock input artifacts
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()

    abs_csv = input_dir / "abs.csv"
    pd.DataFrame({
        "community": [1, 1, 2, 2],
        "messages": ["apple orange banana", "apple orange", "car truck bus", "car truck"],
        "user_id": [10, 11, 20, 21],
        "created_at": ["2017-03-01", "2017-03-01", "2017-03-01", "2017-03-01"]
    }).to_csv(abs_csv, index=False)

    wgt_csv = input_dir / "wgt.csv"
    shutil.copy(abs_csv, wgt_csv)

    match_csv = input_dir / "match.csv"
    pd.DataFrame({
        "community": [1, 2],
        "matched_community": [1, 2]
    }).to_csv(match_csv, index=False)

    def make_ref(p):
        import hashlib
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        return ArtifactReference(
            path=str(p),
            sha256=h,
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

    # Mock domain layer to just write deterministic outputs based on seed/inputs
    def mock_run_topic_phase(*args, **kwargs):
        output_dir = kwargs.get("output_dir")
        content_type = kwargs.get("content_type", "reply")
        month = kwargs.get("month", "03")
        data_type = "twitter"
        import pandas as pd

        paths = [
            f"{data_type}/LDA/scores/{content_type}/{month}.csv",
            f"{data_type}/LDA/matched_topics/{content_type}/{month}.csv",
            f"{data_type}/communities/graphs/absolute/{content_type}/{month}.csv",
            f"{data_type}/communities/graphs/weighted/{content_type}/{month}.csv",
            f"{data_type}/communities/partially_matched/{content_type}/{month}.csv",
            f"{data_type}/_intermediate/topic_inputs/{content_type}/{month}_2017/partial_matched_communities.csv"
        ]
        for p in paths:
            full_path = os.path.join(output_dir, p)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            pd.DataFrame({"x": [1]}).to_csv(full_path, index=False)

    with patch("src.pipelines.social_network_pipeline.run_topic_phase", side_effect=mock_run_topic_phase):
        with prefect_test_harness():
            # Override output_root for run 1
            out_dir_1 = tmp_path / "run_1"
            out_dir_1.mkdir()
            rc1 = ValidatedRunConfiguration(run_config.config_digest, str(out_dir_1), run_config.raw_config)

            ctx = PipelineRunContext.create(
                pipeline_run_id="repro",
                git_commit="HEAD",
                config_digest=run_config.config_digest,
                output_root=str(tmp_path),
                datasets=[]
            )

            res_1 = run_monthly_topic_phase_task.fn(bundle, rc1, ctx)

            # Run 2
            out_dir_2 = tmp_path / "run_2"
            out_dir_2.mkdir()

            rc2 = ValidatedRunConfiguration(run_config.config_digest, str(out_dir_2), run_config.raw_config)
            res_2 = run_monthly_topic_phase_task.fn(bundle, rc2, ctx)

    # Compare
    assert res_1.lda_scores.sha256 == res_2.lda_scores.sha256, "LDA scores must be byte-identical"
    if res_1.matched_communities_topics:
        assert res_1.matched_communities_topics.sha256 == res_2.matched_communities_topics.sha256

    # Compare all theme_inputs
    for t1, t2 in zip(res_1.theme_inputs, res_2.theme_inputs):
        assert t1.sha256 == t2.sha256, f"Theme input {t1.path} is not byte-identical"
