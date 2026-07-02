import pytest
from src.config.defaults import default_config

def test_graph_thresholds():
    assert default_config.graph.min_total_post == 10
    assert default_config.graph.min_shared_post == 5
    assert default_config.graph.min_members == 3

def test_louvain_defaults():
    assert default_config.louvain.resolution == 1.0
    assert default_config.louvain.seed == 123

def test_lda_defaults():
    assert default_config.lda.num_topics == 15
    assert default_config.lda.top_n_keywords == 50
    assert default_config.lda.random_state == 100
    assert default_config.lda.iterations == 100
    assert default_config.lda.chunksize == 20
    assert default_config.lda.passes == 80
    assert default_config.lda.alpha == 'auto'
    assert default_config.lda.eta == 'auto'

def test_gpt_theme_defaults():
    assert default_config.gpt.model == 'gpt-4o'
    assert default_config.gpt.seed == 42
    assert default_config.gpt.temperature == 0.0

def test_theme_similarity_defaults():
    assert default_config.similarity.embedding_model == 'paraphrase-MiniLM-L6-v2'
    assert default_config.similarity.reply_transition_threshold == 0.0
    assert default_config.similarity.default_transition_threshold == 0.5
