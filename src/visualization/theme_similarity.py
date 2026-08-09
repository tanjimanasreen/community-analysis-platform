import logging

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

from src.themes.theme_similarity import calculate_sentence_similarity

logger = logging.getLogger(__name__)


def draw_theme_similarity_heatmap(
    all_community_theme: dict,
    output_dir: str,
    file_name: str,
    model_name: str = "paraphrase-MiniLM-L6-v2",
    model=None,
):
    if not all_community_theme:
        logger.info(
            "theme_similarity_visualization_skipped file=%s reason=no_themes", file_name
        )
        return

    num_sets = len(all_community_theme)
    cols = 3
    rows = (num_sets + cols - 1) // cols

    fig = make_subplots(
        rows=max(1, rows),
        cols=max(1, cols),
        subplot_titles=[f"Community Set {i}" for i in range(1, num_sets + 1)],
        horizontal_spacing=0.1,
        vertical_spacing=0.1,
    )

    max_similarity = -np.inf
    min_similarity = np.inf

    for communities in all_community_theme.values():
        themes = list(communities.values())
        if not themes:
            continue
        similarity_matrix = calculate_sentence_similarity(
            themes, model_name=model_name, model=model
        )
        max_similarity = max(max_similarity, np.max(similarity_matrix))
        min_similarity = min(min_similarity, np.min(similarity_matrix))

    if min_similarity == np.inf:
        min_similarity, max_similarity = 0, 1

    for index, (community_set_number, communities) in enumerate(
        all_community_theme.items()
    ):
        themes = list(communities.values())
        community_names = list(communities.keys())

        if not themes:
            continue

        similarity_matrix = calculate_sentence_similarity(
            themes, model_name=model_name, model=model
        )

        mask = np.tril(np.ones(similarity_matrix.shape, dtype=bool))
        similarity_matrix = np.where(mask, np.nan, similarity_matrix)

        row = index // cols + 1
        col = index % cols + 1

        fig.add_trace(
            go.Heatmap(
                z=similarity_matrix,
                x=community_names,
                y=community_names,
                colorscale="bluyl",
                zmin=min_similarity,
                zmax=max_similarity,
                showscale=False,
                texttemplate="%{z:.2f}",
                hoverongaps=False,
                zauto=False,
            ),
            row=row,
            col=col,
        )

    fig.update_layout(
        title_text=f"Cosine Similarity Score ({file_name})",
        height=max(360, rows * 360),
        width=max(360, cols * 360),
        coloraxis_colorbar=dict(
            title="Score",
            tickvals=[min_similarity, max_similarity],
            ticktext=[f"{min_similarity:.2f}", f"{max_similarity:.2f}"],
            lenmode="fraction",
            len=0.3,
            yanchor="middle",
            y=0.4,
        ),
    )

    for trace in fig.data:
        trace["coloraxis"] = "coloraxis"

    os.makedirs(output_dir, exist_ok=True)
    html_file = os.path.join(output_dir, f"{file_name}.html")
    fig.write_html(html_file)
    logger.info("theme_similarity_html_saved path=%s", html_file)

    try:
        png_file = os.path.join(output_dir, f"{file_name}.png")
        fig.write_image(png_file, scale=2)
        logger.info("theme_similarity_png_saved path=%s", png_file)
    except Exception as exc:
        logger.warning("theme_similarity_png_skipped error_type=%s", type(exc).__name__)
