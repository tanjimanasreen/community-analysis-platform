from src.visualization.theme_similarity import draw_theme_similarity_heatmap


def test_draw_theme_similarity_heatmap_writes_html_without_kaleido_requirement(tmp_path):
    draw_theme_similarity_heatmap(
        {
            1: {
                "january_0": "Apple orange banana",
                "february_0": "Fruit and vegetables",
            }
        },
        str(tmp_path),
        "general_theme",
    )

    assert (tmp_path / "general_theme.html").exists()
