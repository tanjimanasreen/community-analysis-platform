import pandas as pd
import plotly.graph_objects as go
from sklearn.metrics.pairwise import cosine_similarity
import ast
import logging
import numpy as np

from src.config.defaults import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


def calculate_sentence_similarity(themes, model=None, model_name=None):
    if not themes:
        return np.array([]), np.array([])
    model_name = model_name or DEFAULT_CONFIG.similarity.embedding_model
    from src.config.settings import (
        get_similarity_settings,
        get_tei_client_settings,
    )

    similarity_settings = get_similarity_settings()
    if model is None and similarity_settings.provider == "mock":
        embeddings = _offline_theme_embeddings(themes)
    else:
        try:
            if model is None:
                from src.themes.tei_client import TEIClient

                settings = get_tei_client_settings()
                model = TEIClient(
                    base_url=str(settings.base_url),
                    api_key=(
                        settings.api_key.get_secret_value()
                        if settings.api_key
                        else None
                    ),
                    client_batch_size=settings.client_batch_size,
                    timeout_seconds=settings.timeout_seconds,
                )
            embeddings = model.encode(themes)
        except Exception as exc:
            if similarity_settings.failure_policy != "mock":
                raise RuntimeError(
                    "TEI theme-similarity request failed; set "
                    "THEME_SIMILARITY_FAILURE_POLICY=mock only for offline tests"
                ) from exc
            logger.warning("theme_similarity_mock_fallback error=%s", exc)
            embeddings = _offline_theme_embeddings(themes)

    cosine_sim = cosine_similarity(embeddings)
    return embeddings, cosine_sim


def _theme_text(value):
    if value is None or (
        not isinstance(value, (dict, list, tuple, str)) and pd.isna(value)
    ):
        return ""
    if isinstance(value, dict):
        return " ".join(str(key) for key in value)
    try:
        parsed = ast.literal_eval(value) if isinstance(value, str) else value
    except (SyntaxError, ValueError):
        return str(value)
    if isinstance(parsed, dict):
        return " ".join(str(key) for key in parsed)
    return str(parsed)


def extract_themes(df):
    if "general_theme_gpt" not in df.columns:
        return []
    return [_theme_text(value) for value in df["general_theme_gpt"].tolist()]


def draw_theme_similarity_heatmap(themes, sim_matrix):
    if len(themes) == 0 or sim_matrix is None:
        return None

    fig = go.Figure(
        data=go.Heatmap(
            z=sim_matrix, x=themes, y=themes, hoverongaps=False, colorscale="Viridis"
        )
    )

    fig.update_layout(
        title="Theme Similarity Map",
        xaxis_title="Themes",
        yaxis_title="Themes",
    )

    return fig


def _offline_theme_embeddings(themes):
    """Deterministic fallback embeddings for offline unit tests."""
    groups = [
        {"apple", "orange", "banana", "fruit", "vegetables", "vegetable"},
        {"car", "truck", "vehicle", "transportation"},
    ]
    embeddings = []
    for theme in themes:
        words = {word.strip(".,;:!?").lower() for word in str(theme).split()}
        vector = [len(words & group) for group in groups]
        vector.append(len(words))
        embeddings.append(vector)
    return np.array(embeddings, dtype=float)
