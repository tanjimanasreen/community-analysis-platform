import pytest

pytestmark = pytest.mark.requires_loopback

import shutil
from pathlib import Path
import pytest
import pandas as pd
import json

from prefect.testing.utilities import prefect_test_harness
from src.orchestration.tasks import run_monthly_topic_phase_task
from src.orchestration.models import (
    TopicInputBundle,
    ArtifactReference,
    ValidatedRunConfiguration,
    PipelineRunContext,
)


@pytest.fixture
def run_config():
    return ValidatedRunConfiguration(
        config_digest="dummy",
        output_root="/tmp/dummy",
        raw_config={
            "lda": {"num_topics": 2, "random_state": 100, "passes": 5, "chunksize": 20},
            "preprocessing": {"remove_stopwords": True},
            "matching": {"threshold": 0.1},
            "content_type": "reply",
            "data_type": "twitter",
            "month": "march",
            "year": "2017",
            "output_base_path": "/tmp/dummy",
        },
    )


def test_topic_reproducibility(tmp_path, run_config):
    """
    Topic Reproducibility Guarantee:
    Reproducible inside the validated project environment for identical inputs,
    ordering, configuration, seed, and dependency versions.
    """
    # Create valid mock input artifacts for the domain
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()

    abs_csv = input_dir / "abs.csv"
    pd.DataFrame(
        {
            "community_number": [1, 1, 2, 2],
            "messages": [
                ["apple", "orange", "banana", "apple", "orange", "banana"],
                ["apple", "orange", "apple", "orange", "apple", "orange"],
                ["car", "truck", "bus", "car", "truck", "bus"],
                ["car", "truck", "car", "truck", "car", "truck"],
            ],
            "messages_ids": [["m1"], ["m2"], ["m3"], ["m4"]],
            "total_messages": [6, 6, 6, 6],
            "user_id": [10, 11, 20, 21],
            "created_at": ["2017-03-01", "2017-03-01", "2017-03-01", "2017-03-01"],
        }
    ).to_csv(abs_csv, index=False)

    wgt_csv = input_dir / "wgt.csv"
    shutil.copy(abs_csv, wgt_csv)

    match_csv = input_dir / "match.csv"
    pd.DataFrame(
        {
            "abs_community": [1, 2],
            "per_community": [1, 2],
            "members": ["user1,user2", "user3,user4"],
            "jaccard_score": [1.0, 1.0],
        }
    ).to_csv(match_csv, index=False)

    def make_ref(p):
        import hashlib

        h = hashlib.sha256(p.read_bytes()).hexdigest()
        return ArtifactReference(
            path=str(p), sha256=h, media_type="text/csv", byte_size=p.stat().st_size
        )

    bundle = TopicInputBundle(
        absolute_community_messages=make_ref(abs_csv),
        weighted_community_messages=make_ref(wgt_csv),
        matched_communities=make_ref(match_csv),
        partial_matched_communities=None,
        allowed_input_roots=(str(input_dir),),
    )

    with prefect_test_harness():
        # Override output_root for run 1
        out_dir_1 = tmp_path / "run_1"
        out_dir_1.mkdir()
        rc1 = ValidatedRunConfiguration(
            run_config.config_digest, str(out_dir_1), run_config.raw_config
        )

        ctx1 = PipelineRunContext.create(
            pipeline_run_id="repro_1",
            git_commit="HEAD",
            config_digest=run_config.config_digest,
            output_root=str(out_dir_1),
            datasets=[],
        )

        res_1 = run_monthly_topic_phase_task.fn(bundle, rc1, ctx1)

        # Run 2
        out_dir_2 = tmp_path / "run_2"
        out_dir_2.mkdir()
        rc2 = ValidatedRunConfiguration(
            run_config.config_digest, str(out_dir_2), run_config.raw_config
        )
        ctx2 = PipelineRunContext.create(
            pipeline_run_id="repro_2",
            git_commit="HEAD",
            config_digest=run_config.config_digest,
            output_root=str(out_dir_2),
            datasets=[],
        )

        res_2 = run_monthly_topic_phase_task.fn(bundle, rc2, ctx2)

    # Compare LDA scores
    df1_lda = pd.read_csv(res_1.lda_scores.path)
    df2_lda = pd.read_csv(res_2.lda_scores.path)
    pd.testing.assert_frame_equal(df1_lda, df2_lda)

    # Compare matched communities topics
    if res_1.matched_communities_topics:
        assert res_2.matched_communities_topics is not None
        df1_mch = pd.read_csv(res_1.matched_communities_topics.path)
        df2_mch = pd.read_csv(res_2.matched_communities_topics.path)
        pd.testing.assert_frame_equal(df1_mch, df2_mch)

    if res_1.partial_matched_communities_topics:
        assert res_2.partial_matched_communities_topics is not None
        df1_pmch = pd.read_csv(res_1.partial_matched_communities_topics.path)
        df2_pmch = pd.read_csv(res_2.partial_matched_communities_topics.path)
        pd.testing.assert_frame_equal(df1_pmch, df2_pmch)

    # Compare all theme_inputs (manifest)
    for t1, t2 in zip(res_1.theme_inputs, res_2.theme_inputs):
        if t1.path.endswith(".json"):
            with open(t1.path) as f1, open(t2.path) as f2:
                assert json.load(f1) == json.load(f2)
        else:
            # fallback for csv
            df1_theme = pd.read_csv(t1.path)
            df2_theme = pd.read_csv(t2.path)
            pd.testing.assert_frame_equal(df1_theme, df2_theme)
