from pathlib import Path

from src.reporting.artifact_index import build_artifact_index


def test_build_artifact_index_lists_existing_outputs(tmp_path):
    output_root = tmp_path / "outputs"
    theme_root = tmp_path / "theme"
    output_root.mkdir()
    theme_root.mkdir()
    (output_root / "network.parquet").write_text("x\n", encoding="utf-8")
    (theme_root / "themes.parquet").write_text("y\n", encoding="utf-8")

    report = build_artifact_index(
        {
            "output_base_path": str(output_root),
            "theme": {"output_dir": str(theme_root)},
        },
        str(tmp_path / "artifact-index.md"),
    )

    text = Path(report).read_text(encoding="utf-8")
    assert "network.parquet" in text
    assert "themes.parquet" in text
