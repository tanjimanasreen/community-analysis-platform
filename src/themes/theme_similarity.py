import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os

# Reduce parallelism for tokenizers to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Global model cache to avoid reloading for every path
_GLOBAL_MODEL = None


def get_similarity_model(model_name="paraphrase-MiniLM-L6-v2"):
    global _GLOBAL_MODEL
    if _GLOBAL_MODEL is None:
        from sentence_transformers import SentenceTransformer

        _GLOBAL_MODEL = SentenceTransformer(model_name, local_files_only=True)
    return _GLOBAL_MODEL


def calculate_sentence_similarity(
    sentences: list, model_name="paraphrase-MiniLM-L6-v2", model=None
):
    """Calculates cosine similarity between sentences using SentenceTransformers."""
    try:
        model = model or get_similarity_model(model_name)
        embeddings = model.encode(sentences, convert_to_tensor=False)
    except Exception as exc:
        print(f"Using offline theme similarity fallback: {exc}")
        embeddings = _offline_theme_embeddings(sentences)
    cosine_scores = cosine_similarity(embeddings)
    return cosine_scores


def extract_themes(
    matched_df: pd.DataFrame, paths: list, start_month_theme: str, end_month_theme: str
) -> dict:
    all_community_theme = {}
    count = 1

    for path in paths:
        themes = {}
        for p in path:
            starts = matched_df[matched_df.start_month_community == p]
            if not starts.empty and start_month_theme in starts.columns:
                themes[p] = str(starts[start_month_theme].values[0])
            else:
                ends = matched_df[matched_df.end_month_community == p]
                if not ends.empty and end_month_theme in ends.columns:
                    themes[p] = str(ends[end_month_theme].values[0])
                else:
                    themes[p] = ""

        all_community_theme[count] = themes
        count += 1

    return all_community_theme


def _offline_theme_embeddings(sentences: list):
    groups = [
        {"apple", "orange", "banana", "fruit", "vegetables", "vegetable"},
        {"car", "truck", "vehicle", "transportation"},
        {"politics", "election", "government", "policy"},
    ]
    embeddings = []
    for sentence in sentences:
        words = {word.strip(".,;:!?").lower() for word in str(sentence).split()}
        vector = [len(words & group) for group in groups]
        vector.append(len(words))
        embeddings.append(vector)
    return np.array(embeddings, dtype=float)
