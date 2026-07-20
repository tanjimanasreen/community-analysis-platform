from gensim.models import CoherenceModel, LdaModel
from gensim.models import Phrases
import pandas as pd
import gensim
import re

from src.config.defaults import DEFAULT_CONFIG

# Default LDA constants
NUM_TOPICS = DEFAULT_CONFIG.lda.num_topics
TOP_N_KEYWORDS = DEFAULT_CONFIG.lda.top_n_keywords
RANDOM_STATE = DEFAULT_CONFIG.lda.random_state
ITERATIONS = DEFAULT_CONFIG.lda.iterations
CHUNKSIZE = DEFAULT_CONFIG.lda.chunksize
PASSES = DEFAULT_CONFIG.lda.passes
ALPHA = DEFAULT_CONFIG.lda.alpha
ETA = DEFAULT_CONFIG.lda.eta
SPACY_MODEL = "en_core_web_sm"
SPACY_MAX_LENGTH = 5000000
TOKEN_RE = re.compile(r"\w+")

_nlp = None


import logging

_log = logging.getLogger(__name__)

def get_nlp():
    """Load the thesis spaCy model lazily, with an offline fallback for tests."""
    global _nlp
    if _nlp is None:
        import spacy

        try:
            _nlp = spacy.load(SPACY_MODEL, disable=["parser", "ner"])
        except OSError:
            _log.warning(
                "spaCy model '%s' is not installed; falling back to spacy.blank('en'). "
                "Lemmatization will use raw tokens instead of morphological forms, "
                "which may produce different LDA results from the thesis baseline. "
                "Install the model with: python -m spacy download %s",
                SPACY_MODEL, SPACY_MODEL,
            )
            _nlp = spacy.blank("en")
        _nlp.max_length = SPACY_MAX_LENGTH
    return _nlp


def lemmatization(texts, allowed_postags=None):
    if allowed_postags is None:
        allowed_postags = ["NOUN", "ADJ", "VERB", "ADV"]

    texts_out = []
    nlp = get_nlp()
    for sent in texts:
        doc = nlp(" ".join(sent))
        texts_out.append([token.lemma_ or token.text for token in doc])
    return texts_out


def get_lda(dictionary, corpus, num_topics=NUM_TOPICS):
    lda_model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=num_topics,
        random_state=RANDOM_STATE,
        iterations=ITERATIONS,
        chunksize=CHUNKSIZE,
        passes=PASSES,
        alpha=ALPHA,
        eta=ETA,
    )
    return lda_model


def get_lda_stat(lda_model, corpus, id2word, lemmatized_tokens):
    perplexity_lda = lda_model.log_perplexity(corpus)
    coherence_model_lda = CoherenceModel(
        model=lda_model,
        texts=lemmatized_tokens,
        dictionary=id2word,
        coherence="c_v",
        processes=1,
    )
    coherence_lda = coherence_model_lda.get_coherence()
    return perplexity_lda, coherence_lda


def get_topic_keywords(lda_model, topic_id, id2word, topn):
    top_words = lda_model.get_topic_terms(topic_id, topn=topn)
    top_keywords = [id2word[word_id] for word_id, prob in top_words]
    return ", ".join(top_keywords)


def assign_dominant_topic(lda_model, corpus, id2word, data, topn_keywords):
    dominant_topics = []
    topic_keywords = []

    for doc_bow in corpus:
        if not doc_bow:
            dominant_topics.append(-1)
            topic_keywords.append("")
            continue

        topic_distribution = lda_model.get_document_topics(doc_bow)
        topic_distribution = sorted(
            topic_distribution, key=lambda x: x[1], reverse=True
        )
        dominant_topic = topic_distribution[0][0]
        dominant_topics.append(dominant_topic)
        keywords = get_topic_keywords(
            lda_model, dominant_topic, id2word, topn=topn_keywords
        )
        topic_keywords.append(keywords)

    data["dominant_topic"] = dominant_topics
    data["topic_keywords"] = topic_keywords

    return data[["community_number", "dominant_topic", "topic_keywords", "messages"]]


# Unigram Model
def get_unigram_tokens(text_df):
    data_tokens = [TOKEN_RE.findall(text) for text in text_df["messages_processed"]]
    return data_tokens


def get_unigram_lda(text_df):
    data_tokens = get_unigram_tokens(text_df)
    lemmatized_tokens = lemmatization(data_tokens)

    id2word = gensim.corpora.Dictionary(lemmatized_tokens)
    corpus = [id2word.doc2bow(doc) for doc in lemmatized_tokens]

    optimal_model = get_lda(id2word, corpus)
    perplexity, coherence = get_lda_stat(
        optimal_model, corpus, id2word, lemmatized_tokens
    )

    data = text_df.copy()
    document_topics = assign_dominant_topic(
        optimal_model, corpus, id2word, data, topn_keywords=TOP_N_KEYWORDS
    )

    return document_topics, optimal_model, perplexity, coherence


# Bigram Model
def get_bigrams_tokens(text_df):
    data_tokens = [TOKEN_RE.findall(text) for text in text_df["messages_processed"]]
    bigrams_tokens = lemmatization(data_tokens)

    bigram = Phrases(bigrams_tokens, min_count=5)
    trigram = Phrases(bigram[bigrams_tokens])

    for idx in range(len(bigrams_tokens)):
        for token in bigram[bigrams_tokens[idx]]:
            if "_" in token:
                bigrams_tokens[idx].append(token)
        for token in trigram[bigrams_tokens[idx]]:
            if "_" in token:
                bigrams_tokens[idx].append(token)

    return bigrams_tokens


def get_bigram_lda(text_df):
    bigrams_tokens = get_bigrams_tokens(text_df)
    id2word = gensim.corpora.Dictionary(bigrams_tokens)
    corpus = [id2word.doc2bow(doc) for doc in bigrams_tokens]

    optimal_model = get_lda(id2word, corpus)
    perplexity, coherence = get_lda_stat(optimal_model, corpus, id2word, bigrams_tokens)

    data = text_df.copy()
    document_topics = assign_dominant_topic(
        optimal_model, corpus, id2word, data, topn_keywords=TOP_N_KEYWORDS
    )

    return document_topics, optimal_model, perplexity, coherence
