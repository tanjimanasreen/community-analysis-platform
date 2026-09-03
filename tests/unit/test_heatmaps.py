import numpy as np
import pandas as pd
import pytest
from src.themes.heatmaps import calculate_sentence_similarity, extract_themes
from src.themes.theme_similarity import OfflineThemeEmbeddingModel


def test_extract_themes():
    df = pd.DataFrame(
        {
            "general_theme_gpt": [
                "{'Theme A': ['kw1', 'kw2']}",
                "{'Theme B': ['kw3'], 'Theme C': ['kw4']}",
                None,
            ]
        }
    )

    themes = extract_themes(df)
    assert len(themes) == 3
    assert themes[0] == "Theme A"
    assert themes[1] == "Theme B Theme C"
    assert themes[2] == ""


def test_calculate_sentence_similarity():
    themes = [
        "Apple orange banana",
        "Fruit and vegetables",
        "Car and truck",
        "Vehicle transportation",
    ]

    model = OfflineThemeEmbeddingModel()
    embeddings, sim_matrix = calculate_sentence_similarity(themes, model=model)

    assert embeddings is not None
    assert sim_matrix is not None
    assert len(embeddings) == 4
    assert sim_matrix.shape == (4, 4)
    assert np.all(np.isfinite(embeddings))
    assert np.all(np.isfinite(sim_matrix))
    assert np.allclose(sim_matrix, sim_matrix.T, atol=1e-6)
    # The similarity between "Apple orange banana" and "Fruit and vegetables" should be positive and greater than car/fruit
    assert sim_matrix[0][1] > sim_matrix[0][2]
    # Similarity to self is 1.0 (approximately)
    assert round(sim_matrix[0][0], 2) == 1.0
    assert round(sim_matrix[1][1], 2) == 1.0
