import pandas as pd

import src.topics.lda as lda
from src.config.defaults import default_config
from src.topics.topic_matching import get_matched_topic_df


class FakeLdaModel:
    calls = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls.append(kwargs)


class FakeTopicModel:
    def show_topic(self, topic_id, topn=50):
        return [("alpha", 0.5), ("beta", 0.2), ("gamma", 0.05)]


class FakeCoherenceModel:
    calls = []

    def __init__(self, **kwargs):
        self.calls.append(kwargs)

    def get_coherence(self):
        return 0.75


class FakePerplexityModel:
    def log_perplexity(self, corpus):
        return -1.25


def test_lda_defaults_are_passed_to_model(monkeypatch):
    FakeLdaModel.calls = []
    monkeypatch.setattr(lda, "LdaModel", FakeLdaModel)

    model = lda.get_lda(dictionary={"alpha": 0}, corpus=[[(0, 1)]])

    assert isinstance(model, FakeLdaModel)
    call = FakeLdaModel.calls[0]
    assert call["num_topics"] == default_config.lda.num_topics
    assert call["random_state"] == default_config.lda.random_state
    assert call["iterations"] == default_config.lda.iterations
    assert call["chunksize"] == default_config.lda.chunksize
    assert call["passes"] == default_config.lda.passes
    assert call["alpha"] == default_config.lda.alpha
    assert call["eta"] == default_config.lda.eta


def test_unigram_and_bigram_tokenizers_do_not_require_nltk():
    df = pd.DataFrame({"messages_processed": ["alpha beta beta", "gamma"]})

    assert lda.get_unigram_tokens(df) == [["alpha", "beta", "beta"], ["gamma"]]
    assert lda.lemmatization([["alpha", "beta"]]) == [["alpha", "beta"]]


def test_lda_stat_uses_cv_coherence_without_worker_spawning(monkeypatch):
    FakeCoherenceModel.calls = []
    monkeypatch.setattr(lda, "CoherenceModel", FakeCoherenceModel)

    perplexity, coherence = lda.get_lda_stat(
        FakePerplexityModel(),
        corpus=[[(0, 1)]],
        id2word={0: "alpha"},
        lemmatized_tokens=[["alpha"]],
    )

    call = FakeCoherenceModel.calls[0]
    assert perplexity == -1.25
    assert coherence == 0.75
    assert call["coherence"] == "c_v"
    assert call["processes"] == 1


def test_spacy_model_fallback_preserves_max_length(monkeypatch):
    lda._nlp = None

    def raise_missing_model(*_args, **_kwargs):
        raise OSError("missing model")

    import spacy

    monkeypatch.setattr(spacy, "load", raise_missing_model)
    nlp = lda.get_nlp()

    assert nlp.lang == "en"
    assert nlp.max_length == 5000000


def test_matched_topic_df_outputs_expected_columns():
    dfs = [
        pd.DataFrame({"community_number": [0], "dominant_topic": [1]}),
        pd.DataFrame({"community_number": [2], "dominant_topic": [3]}),
        pd.DataFrame({"community_number": [0], "dominant_topic": [-1]}),
        pd.DataFrame({"community_number": [2], "dominant_topic": [4]}),
    ]

    result = get_matched_topic_df(
        lda_models=[FakeTopicModel(), FakeTopicModel(), FakeTopicModel(), FakeTopicModel()],
        dfs=dfs,
        community_id_pairs=[(0, 2)],
    )

    assert list(result.columns) == [
        "absolute_community",
        "absolute_unigram_topic",
        "absolute_unigram_keywords",
        "weighted_community",
        "weighted_unigram_topic",
        "weighted_unigram_keywords",
        "absolute_bigram_topic",
        "absolute_bigram_keywords",
        "weighted_bigram_topic",
        "weighted_bigram_keywords",
    ]
    assert result.loc[0, "absolute_community"] == 0
    assert result.loc[0, "weighted_community"] == 2
    assert result.loc[0, "absolute_bigram_keywords"] == []
