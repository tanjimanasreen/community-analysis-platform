import importlib

import pandas as pd

import src.topics.lda as lda


class FakeLdaModel:
    calls: list[dict] = []

    def __init__(self, **kwargs):
        self.calls.append(kwargs)


def test_lda_runtime_config_reaches_ldamulticore(monkeypatch):
    FakeLdaModel.calls = []
    monkeypatch.setattr(lda, "LdaMulticore", FakeLdaModel)

    lda.get_lda(
        dictionary={"alpha": 0},
        corpus=[[(0, 1)]],
        lda_config={
            "implementation": "ldamulticore",
            "num_topics": 7,
            "random_state": 321,
            "iterations": 44,
            "chunksize": 9,
            "passes": 6,
            "alpha": "asymmetric",
            "eta": 0.25,
            "workers": 2,
        },
    )

    assert FakeLdaModel.calls == [
        {
            "corpus": [[(0, 1)]],
            "id2word": {"alpha": 0},
            "num_topics": 7,
            "random_state": 321,
            "iterations": 44,
            "chunksize": 9,
            "passes": 6,
            "alpha": "asymmetric",
            "eta": 0.25,
            "workers": 2,
        }
    ]


def test_full_pipeline_forwards_louvain_and_lda_config(monkeypatch, tmp_path):
    pipeline = importlib.import_module("src.pipelines.social_network_pipeline")
    observed: dict[str, dict] = {}

    monkeypatch.setattr(
        pipeline,
        "run_network_phase",
        lambda **_kwargs: (
            "absolute_graph",
            "weighted_graph",
            pd.DataFrame({"id": [1]}),
            pd.DataFrame({"user_id": [1]}),
        ),
    )

    def fake_community_phase(**kwargs):
        observed["community"] = kwargs
        empty_messages = pd.DataFrame()
        return empty_messages, empty_messages, pd.DataFrame(), pd.DataFrame()

    monkeypatch.setattr(pipeline, "run_community_phase", fake_community_phase)
    monkeypatch.setattr(pipeline, "save_pipeline_topic_inputs", lambda **_kwargs: None)

    def fake_topics(**kwargs):
        observed["topics"] = kwargs

    monkeypatch.setattr(pipeline, "run_topic_phase_from_saved_inputs", fake_topics)

    lda_config = {"num_topics": 9, "passes": 4}
    assert pipeline.run_full_pipeline(
        pd.DataFrame({"source": [1]}),
        output_dir=str(tmp_path),
        louvain_resolution=1.75,
        louvain_seed=456,
        lda_config=lda_config,
    )

    assert observed["community"]["louvain_resolution"] == 1.75
    assert observed["community"]["louvain_seed"] == 456
    assert observed["topics"]["lda_config"] == lda_config


def test_phraser_optimization_preserves_legacy_bigram_trigram_sequence(monkeypatch):
    from gensim.models import Phrases

    documents = [["new", "york", "city", "new", "york", "city"] for _ in range(8)]
    frame = pd.DataFrame(
        {"messages_processed": [" ".join(tokens) for tokens in documents]}
    )
    monkeypatch.setattr(lda, "lemmatization", lambda values: [list(v) for v in values])

    legacy = [list(tokens) for tokens in documents]
    bigram = Phrases(legacy, min_count=5)
    trigram = Phrases(bigram[legacy])
    for tokens in legacy:
        tokens.extend(token for token in bigram[tokens] if "_" in token)
        tokens.extend(token for token in trigram[tokens] if "_" in token)

    assert lda.get_bigrams_tokens(frame) == legacy
