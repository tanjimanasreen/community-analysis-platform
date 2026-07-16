import importlib
import sys

import pandas as pd


def test_run_network_phase():
    # Provide a minimal mock df that matches what extract_follower_followee needs
    # Let's just create a small df. Actually, unit testing a pipeline often involves mocking the underlying functions.
    # We will do a basic integration test if possible, or just mock it.
    pass


# We will rely on unit tests of individual components. The pipeline is just orchestration.
# The user's spec focuses on tests around "current behavior before refactoring internals."


def test_social_network_pipeline_import_does_not_import_topic_modules():
    sys.modules.pop("src.pipelines.social_network_pipeline", None)
    sys.modules.pop("src.topics.lda", None)
    sys.modules.pop("src.topics.text_preprocessor", None)
    sys.modules.pop("src.topics.topic_matching", None)

    importlib.import_module("src.pipelines.social_network_pipeline")

    assert "src.topics.lda" not in sys.modules
    assert "src.topics.text_preprocessor" not in sys.modules
    assert "src.topics.topic_matching" not in sys.modules


def _community_messages():
    return pd.DataFrame(
        {
            "community_number": [0],
            "messages": [["message one", "message two"]],
            "messages_ids": [[101, 102]],
            "total_messages": [2],
        }
    )


def _matched_communities():
    return pd.DataFrame(
        {
            "abs_community": [0],
            "per_community": [0],
            "jaccard_score": [1.0],
            "members": [[1, 2, 3]],
        }
    )


def _partial_matched_communities():
    return pd.DataFrame(
        columns=[
            "abs_community",
            "absolute_members",
            "per_community",
            "weighted_members",
            "jaccard_score",
            "common_members",
            "uncommon_members",
        ]
    )


def test_run_full_pipeline_can_skip_topic_phase(monkeypatch, tmp_path):
    pipeline = importlib.import_module("src.pipelines.social_network_pipeline")
    calls = []

    monkeypatch.setattr(
        pipeline,
        "run_network_phase",
        lambda **kwargs: (
            "absolute_graph",
            "weighted_graph",
            pd.DataFrame({"id": [1]}),
            pd.DataFrame({"user_id": [1]}),
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "run_community_phase",
        lambda **kwargs: (
            _community_messages(),
            _community_messages(),
            _matched_communities(),
            _partial_matched_communities(),
        ),
    )

    def fake_topic_phase(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(pipeline, "run_topic_phase", fake_topic_phase)

    assert pipeline.run_full_pipeline(
        pd.DataFrame({"source": [1]}),
        output_dir=str(tmp_path),
        include_topics=False,
    )
    assert calls == []


def test_run_full_pipeline_runs_topic_phase_by_default(monkeypatch, tmp_path):
    pipeline = importlib.import_module("src.pipelines.social_network_pipeline")
    calls = []

    monkeypatch.setattr(
        pipeline,
        "run_network_phase",
        lambda **kwargs: (
            "absolute_graph",
            "weighted_graph",
            pd.DataFrame({"id": [1]}),
            pd.DataFrame({"user_id": [1]}),
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "run_community_phase",
        lambda **kwargs: (
            _community_messages(),
            _community_messages(),
            _matched_communities(),
            _partial_matched_communities(),
        ),
    )

    def fake_topic_phase(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(pipeline, "run_topic_phase", fake_topic_phase)

    assert pipeline.run_full_pipeline(
        pd.DataFrame({"source": [1]}), output_dir=str(tmp_path)
    )
    assert len(calls) == 1


def test_network_community_wrapper_skips_topic_phase(monkeypatch):
    pipeline = importlib.import_module("src.pipelines.social_network_pipeline")
    observed = {}

    def fake_full_pipeline(**kwargs):
        observed.update(kwargs)
        return True

    monkeypatch.setattr(pipeline, "run_full_pipeline", fake_full_pipeline)

    assert pipeline.run_network_community_pipeline(pd.DataFrame({"source": [1]}))
    assert observed["include_topics"] is False


def test_run_topic_phase_writes_theme_input_artifacts(monkeypatch, tmp_path):
    pipeline = importlib.import_module("src.pipelines.social_network_pipeline")

    monkeypatch.setattr(
        "src.topics.text_preprocessor.message_preprocess",
        lambda df: pd.Series(["processed text"] * len(df)),
    )

    class FakeModel:
        def show_topic(self, topic_id, topn=50):
            return [("apple", 0.9), ("orange", 0.8)]

    topic_docs = pd.DataFrame(
        {
            "community_number": [0],
            "dominant_topic": [0],
            "topic_keywords": ["apple, orange"],
            "messages": [["message one"]],
        }
    )
    monkeypatch.setattr(
        "src.topics.lda.get_unigram_lda",
        lambda df: (topic_docs.copy(), FakeModel(), -1.0, 0.5),
    )
    monkeypatch.setattr(
        "src.topics.lda.get_bigram_lda",
        lambda df: (topic_docs.copy(), FakeModel(), -1.0, 0.5),
    )
    monkeypatch.setattr(
        "src.topics.topic_matching.get_matched_topic_df",
        lambda **kwargs: pd.DataFrame(
            {
                "absolute_community": [0],
                "absolute_unigram_topic": [0],
                "absolute_unigram_keywords": [["apple"]],
                "weighted_community": [0],
                "weighted_unigram_topic": [0],
                "weighted_unigram_keywords": [["orange"]],
                "absolute_bigram_topic": [0],
                "absolute_bigram_keywords": [["big apple"]],
                "weighted_bigram_topic": [0],
                "weighted_bigram_keywords": [["big orange"]],
            }
        ),
    )

    pipeline.run_topic_phase(
        abs_community_messages=_community_messages(),
        per_community_messages=_community_messages(),
        matched_df=_matched_communities(),
        partial_matched=_partial_matched_communities(),
        month="03",
        year="2017",
        data_type="twitter",
        content_type="reply",
        output_dir=str(tmp_path),
    )

    public_csv = tmp_path / "twitter" / "LDA" / "matched" / "reply" / "03_2017.csv"
    internal_csv = (
        tmp_path
        / "twitter"
        / "_intermediate"
        / "theme_inputs"
        / "reply"
        / "2017"
        / "03_2017.csv"
    )
    manifest = internal_csv.parent / "manifest.json"

    assert public_csv.exists()
    assert internal_csv.exists()
    assert manifest.exists()
    assert list(pd.read_csv(public_csv).columns) == list(
        pd.read_csv(internal_csv).columns
    )
