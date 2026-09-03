from src.themes.theme_similarity import OfflineThemeEmbeddingModel
from src.visualization.theme_similarity import draw_theme_similarity_heatmap


def test_draw_theme_similarity_heatmap_writes_html_without_kaleido_requirement(
    tmp_path,
):
    model = OfflineThemeEmbeddingModel()
    draw_theme_similarity_heatmap(
        {
            1: {
                "january_0": "Apple orange banana",
                "february_0": "Fruit and vegetables",
            }
        },
        str(tmp_path),
        "general_theme",
        model=model,
    )

    html_file = tmp_path / "general_theme.html"
    assert html_file.exists()
    content = html_file.read_text(encoding="utf-8")
    assert "plotly" in content.lower()
