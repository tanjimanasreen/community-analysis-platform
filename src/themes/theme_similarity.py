import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging
import os

# Reduce parallelism for tokenizers to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Global model cache to avoid reloading for every path
_GLOBAL_MODEL = None
logger = logging.getLogger(__name__)


def get_similarity_model(model_name="paraphrase-MiniLM-L6-v2"):
    global _GLOBAL_MODEL
    if _GLOBAL_MODEL is None:
        from src.config.settings import get_tei_client_settings
        from src.themes.tei_client import TEIClient

        settings = get_tei_client_settings()
        _GLOBAL_MODEL = TEIClient(
            base_url=str(settings.base_url),
            api_key=settings.api_key.get_secret_value() if settings.api_key else None,
            client_batch_size=settings.client_batch_size,
            timeout_seconds=settings.timeout_seconds,
        )
    return _GLOBAL_MODEL


def calculate_sentence_similarity(
    sentences: list, model_name="paraphrase-MiniLM-L6-v2", model=None
):
    """Calculate cosine similarity with explicit TEI failure semantics."""
    if not sentences:
        return np.empty((0, 0), dtype=float)

    from src.config.settings import get_similarity_settings

    settings = get_similarity_settings()
    if model is None and settings.provider == "mock":
        embeddings = _offline_theme_embeddings(sentences)
    else:
        try:
            model = model or get_similarity_model(model_name)
            embeddings = model.encode(sentences)
        except Exception as exc:
            if settings.failure_policy != "mock":
                raise RuntimeError(
                    "TEI theme-similarity request failed; set "
                    "THEME_SIMILARITY_FAILURE_POLICY=mock only for offline tests"
                ) from exc
            logger.warning("theme_similarity_mock_fallback error=%s", exc)
            embeddings = _offline_theme_embeddings(sentences)
    return cosine_similarity(embeddings)


def extract_themes(
    matched_df: pd.DataFrame, paths: list, start_month_theme: str, end_month_theme: str
) -> dict:
    """Extract path themes with O(rows + path nodes) lookups."""
    start_lookup = {}
    end_lookup = {}
    if not matched_df.empty:
        if {"start_month_community", start_month_theme}.issubset(matched_df.columns):
            start_lookup = (
                matched_df[["start_month_community", start_month_theme]]
                .drop_duplicates("start_month_community", keep="first")
                .set_index("start_month_community")[start_month_theme]
                .to_dict()
            )
        if {"end_month_community", end_month_theme}.issubset(matched_df.columns):
            end_lookup = (
                matched_df[["end_month_community", end_month_theme]]
                .drop_duplicates("end_month_community", keep="first")
                .set_index("end_month_community")[end_month_theme]
                .to_dict()
            )

    all_community_theme = {}
    for count, path in enumerate(paths, start=1):
        themes = {}
        for community in path:
            value = start_lookup.get(community, end_lookup.get(community, ""))
            themes[community] = "" if value is None else str(value)
        all_community_theme[count] = themes
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
