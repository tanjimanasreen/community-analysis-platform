from __future__ import annotations

import numpy as np

from src.themes.embedding_store import EmbeddingContract, RecordingEmbeddingModel
from src.themes.theme_similarity import (
    OfflineThemeEmbeddingModel,
    build_similarity_embedder,
    calculate_sentence_similarity,
)


def test_mock_similarity_profile_has_explicit_reproducible_contract(monkeypatch):
    monkeypatch.setenv("THEME_SIMILARITY_PROVIDER", "mock")

    model, model_id, revision, dimensions = build_similarity_embedder(
        {}, "paraphrase-MiniLM-L6-v2"
    )
    values = model.encode(["policy", "policy and election"])

    assert model_id == "mock:theme-similarity"
    assert revision == "deterministic-mock-v1"
    assert dimensions == 4
    assert values.shape == (2, 4)
    assert values.dtype == np.float32


def test_similarity_recorder_deduplicates_inference_without_changing_matrix_shape():
    recorder = RecordingEmbeddingModel(
        OfflineThemeEmbeddingModel(),
        EmbeddingContract(
            profile="theme_similarity",
            provider="mock",
            model_id="mock:theme-similarity",
            model_revision="deterministic-mock-v1",
            normalized=False,
            dimensions=4,
        ),
    )

    matrix = calculate_sentence_similarity(
        ["election policy", "election policy", "car vehicle"],
        model=recorder,
    )

    assert matrix.shape == (3, 3)
    assert recorder.record_count == 2
    assert np.isclose(matrix[0, 1], 1.0)
