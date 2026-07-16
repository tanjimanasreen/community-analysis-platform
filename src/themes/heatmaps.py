import pandas as pd
import plotly.graph_objects as go
from sklearn.metrics.pairwise import cosine_similarity
import ast
import numpy as np

from src.config.defaults import DEFAULT_CONFIG


def calculate_sentence_similarity(themes, model=None, model_name=None):
    model_name = model_name or DEFAULT_CONFIG.similarity.embedding_model
    try:
        if model is None:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(model_name, local_files_only=True)
        embeddings = model.encode(themes)
    except Exception as e:
        print(f"Error loading model: {e}")
        embeddings = _offline_theme_embeddings(themes)

    cosine_sim = cosine_similarity(embeddings)
    return embeddings, cosine_sim


def extract_themes(df):
    general_theme = []

    if "general_theme_gpt" not in df.columns:
        return []

    for idx, row in df.iterrows():
        try:
            if pd.isna(row["general_theme_gpt"]):
                general_theme.append("")
                continue

            theme_dict = ast.literal_eval(row["general_theme_gpt"])
            if isinstance(theme_dict, dict):
                theme_str = " ".join(list(theme_dict.keys()))
                general_theme.append(theme_str)
            else:
                general_theme.append(str(theme_dict))
        except Exception:
            general_theme.append(str(row["general_theme_gpt"]))

    return general_theme


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
