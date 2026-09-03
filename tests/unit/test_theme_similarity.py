import numpy as np
import pandas as pd
import pytest
from src.themes.heatmaps import calculate_sentence_similarity, extract_themes
from src.themes.theme_similarity import OfflineThemeEmbeddingModel


def test_extract_themes_formats():
    df = pd.DataFrame(
        {
            "general_theme_gpt": [
                "{'Test Theme': ['keyword1', 'keyword2']}",
                "{'Another Theme': ['kw'], 'Second Theme': ['kw2']}",
                "{'Bad Format': []}",
                None,
            ]
        }
    )
    themes = extract_themes(df)
    assert len(themes) == 4
    assert themes[0] == "Test Theme"
    assert themes[1] == "Another Theme Second Theme"
    assert themes[2] == "Bad Format"
    assert themes[3] == ""


def test_calculate_sentence_similarity_matrix():
    themes = ["Apple and orange", "Fruit like apple", "Car and truck", "Vehicle"]
    model = OfflineThemeEmbeddingModel()
    embeddings, matrix = calculate_sentence_similarity(themes, model=model)

    assert embeddings is not None
    assert matrix is not None
    assert len(embeddings) == 4
    assert matrix.shape == (4, 4)
    assert np.all(np.isfinite(matrix))
    assert np.allclose(matrix, matrix.T, atol=1e-6)

    # Self-similarity should be ~1.0
    assert abs(matrix[0][0] - 1.0) < 1e-4
    assert abs(matrix[1][1] - 1.0) < 1e-4

    # Semantic similarity: 0 and 1 should be more similar than 0 and 2
    assert matrix[0][1] > matrix[0][2]


def test_calculate_sentence_similarity_empty():
    embeddings, matrix = calculate_sentence_similarity([])
    # Expected behavior for empty list: returns empty arrays/matrices
    assert len(embeddings) == 0
    assert len(matrix) == 0
