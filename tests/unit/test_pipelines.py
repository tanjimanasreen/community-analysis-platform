import importlib
import sys

import networkx as nx
import pandas as pd
import pytest


def _telegram_forward_relationships():
    rows = []
    for message_id, spreader_id in (("m1", "u2"), ("m2", "u2"), ("m3", "u1")):
        message = (
            "{"
            f"'unique_id': '{message_id}', "
            f"'text': 'message {message_id}', "
            "'forwarded_date': '(2019, 9, 1, 10, 0, 0)'"
            "}"
        )
        rows.extend(
            [
                {
                    "source": "{'user_id': 'u1', 'username': 'creator'}",
                    "target": message,
                    "relation": "PRODUCED",
                },
                {
                    "source": message,
                    "target": (
                        "{" f"'user_id': '{spreader_id}', 'username': 'spreader'" "}"
                    ),
                    "relation": "FORWARDED_BY",
                },
            ]
        )
    return pd.DataFrame(rows)


def _run_telegram_network_phase(monkeypatch, pipeline, frame):
    observed = {}

    monkeypatch.setattr(
        pipeline, "save_parquet_to_directory", lambda *args, **kwargs: None
    )

    def fake_get_network_graph(interactions, **kwargs):
        observed["interactions"] = interactions.copy()
        observed["graph_kwargs"] = kwargs
        return nx.MultiDiGraph(), nx.MultiDiGraph()

    monkeypatch.setattr(pipeline, "get_network_graph", fake_get_network_graph)

    graphs = pipeline.run_network_phase(
        df_data=frame,
        content_type="forward",
        creator_relation="PRODUCED",
        spreader_relation="FORWARDED_BY",
        creator_node_column="source",
        spreader_node_column="target",
        text_node_column_creator_df="target",
        data_type="telegram",
        month="09",
        year="2019",
        output_dir="unused",
        min_total_post=1,
        min_shared_post=1,
    )
    return (*graphs, observed)


def test_run_network_phase_normalizes_raw_telegram_before_existing_metrics(
    monkeypatch,
):
    pipeline = importlib.import_module("src.pipelines.social_network_pipeline")

    _, _, network, users, observed = _run_telegram_network_phase(
        monkeypatch, pipeline, _telegram_forward_relationships()
    )

    pairs = list(
        network[["from_id", "forwarder_id"]].itertuples(index=False, name=None)
    )
    assert pairs == [("u1", "u2"), ("u1", "u2"), ("u1", "u1")]
    assert set(users["user_id"]) == {"u1", "u2"}

    interactions = observed["interactions"]
    assert len(interactions) == 1
    row = interactions.iloc[0]
    assert row["source"] == "u1"
    assert row["target"] == "u2"
    assert row["shared_post"] == 2
    assert row["total_post"] == 3
    assert row["weighted_post"] == pytest.approx(2 / 3)
    assert observed["graph_kwargs"] == {
        "min_total_post": 1,
        "min_shared_post": 1,
    }


def test_run_network_phase_preserves_already_normalized_telegram_input(monkeypatch):
    pipeline = importlib.import_module("src.pipelines.social_network_pipeline")
    normalized = pd.DataFrame(
        {
            "from_id": ["u1", "u1", "u1"],
            "forwarder_id": ["u2", "u2", "u1"],
            "text": ["m1", "m2", "m3"],
            "forwarded_date": ["2019-09-01"] * 3,
        }
    )

    _, _, network, _, observed = _run_telegram_network_phase(
        monkeypatch, pipeline, normalized
    )

    pd.testing.assert_frame_equal(network, normalized)
    assert network is not normalized
    row = observed["interactions"].iloc[0]
    assert row["shared_post"] == 2
    assert row["total_post"] == 3
    assert row["weighted_post"] == pytest.approx(2 / 3)


def test_run_network_phase_rejects_unknown_telegram_input_shape(monkeypatch):
    pipeline = importlib.import_module("src.pipelines.social_network_pipeline")
    monkeypatch.setattr(
        pipeline, "save_parquet_to_directory", lambda *args, **kwargs: None
    )

    with pytest.raises(
        ValueError,
        match=(
            "Telegram network input must contain either normalized "
            "from_id/forwarder_id columns or legacy source/target/relation columns"
        ),
    ):
        pipeline.run_network_phase(
            df_data=pd.DataFrame({"foo": [1], "bar": [2]}),
            content_type="forward",
            creator_relation="PRODUCED",
            spreader_relation="FORWARDED_BY",
            creator_node_column="source",
            spreader_node_column="target",
            text_node_column_creator_df="target",
            data_type="telegram",
            month="09",
            year="2019",
            output_dir="unused",
            min_total_post=1,
            min_shared_post=1,
        )


# We rely on unit tests of individual components while protecting the shared
# pipeline boundaries that select those components.


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

    public_parquet = (
        tmp_path / "twitter" / "LDA" / "matched" / "reply" / "03_2017.parquet"
    )
    internal_parquet = (
        tmp_path
        / "twitter"
        / "_intermediate"
        / "theme_inputs"
        / "reply"
        / "2017"
        / "03_2017.parquet"
    )
    manifest = internal_parquet.parent / "manifest.json"

    assert public_parquet.exists()
    assert internal_parquet.exists()
    assert manifest.exists()
    assert list(pd.read_parquet(public_parquet).columns) == list(
        pd.read_parquet(internal_parquet).columns
    )
