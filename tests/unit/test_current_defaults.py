import pytest
from src.config.defaults import DEFAULT_CONFIG


def test_graph_thresholds():
    assert DEFAULT_CONFIG.graph.min_total_post == 10
    assert DEFAULT_CONFIG.graph.min_shared_post == 5
    assert DEFAULT_CONFIG.graph.min_members == 3


def test_louvain_defaults():
    assert DEFAULT_CONFIG.louvain.resolution == 1.0
    assert DEFAULT_CONFIG.louvain.seed == 123


def test_lda_defaults():
    assert DEFAULT_CONFIG.lda.num_topics == 15
    assert DEFAULT_CONFIG.lda.top_n_keywords == 50
    assert DEFAULT_CONFIG.lda.random_state == 100
    assert DEFAULT_CONFIG.lda.iterations == 100
    assert DEFAULT_CONFIG.lda.chunksize == 20
    assert DEFAULT_CONFIG.lda.passes == 80
    assert DEFAULT_CONFIG.lda.alpha == "auto"
    assert DEFAULT_CONFIG.lda.eta == "auto"


def test_theme_provider_defaults():
    assert DEFAULT_CONFIG.theme_provider.primary == "mock"
    assert DEFAULT_CONFIG.theme_provider.fallback is True
    assert DEFAULT_CONFIG.theme_provider.fallback_chain == [
        "llm7:fast",
        "nvidia:meta/llama3-70b-instruct",
    ]


def test_theme_similarity_defaults():
    assert DEFAULT_CONFIG.similarity.embedding_model == "paraphrase-MiniLM-L6-v2"
    assert DEFAULT_CONFIG.similarity.reply_transition_threshold == 0.0
    assert DEFAULT_CONFIG.similarity.default_transition_threshold == 0.5
