import pandas as pd

from src.cli import _run_theme_analysis_command
from src.themes.theme_inputs import save_theme_inputs


def _write_config(tmp_path, *, explicit_input_dir=None):
    lines = [
        "data_type: twitter",
        "content_type: reply",
        'month: "03"',
        'year: "2017"',
        "input_path: does-not-matter.csv",
        f"output_base_path: {tmp_path}",
        "creator_relation: REPLIED_TO",
        "spreader_relation: REPLIED_BY",
        "creator_node_column: target",
        "spreader_node_column: target",
        "text_node_column: source",
        "date_column: created_at",
        "theme:",
        f"  output_dir: {tmp_path / 'theme-output'}",
        '  year: "2017"',
        "  render_visuals: false",
    ]
    if explicit_input_dir:
        lines.append(f"  input_dir: {explicit_input_dir}")
        lines.append("  content_type: mixed")
    path = tmp_path / "config.yml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_matched_lda(path):
    pd.DataFrame(
        {
            "members": ["[1, 2]"],
            "absolute_community": [0],
            "weighted_community": [0],
            "absolute_unigram_keywords": ["['apple']"],
            "absolute_bigram_keywords": ["['big apple']"],
            "weighted_unigram_keywords": ["['orange']"],
            "weighted_bigram_keywords": ["['big orange']"],
        }
    ).to_csv(path, index=False)


def test_run_theme_analysis_loads_saved_inputs_without_network_topic(
    monkeypatch, tmp_path
):
    matched_csv = tmp_path / "03_2017.csv"
    _write_matched_lda(matched_csv)
    save_theme_inputs(
        matched_lda_csv=matched_csv,
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        month="03",
        year="2017",
    )
    config_path = _write_config(tmp_path)

    social_pipeline = __import__("src.pipelines.social_network_pipeline", fromlist=[""])

    def fail(*args, **kwargs):
        raise AssertionError(
            "theme-only execution must not call network/community/topic stages"
        )

    monkeypatch.setattr(social_pipeline, "run_network_phase", fail)
    monkeypatch.setattr(social_pipeline, "run_community_phase", fail)
    monkeypatch.setattr(social_pipeline, "run_topic_phase", fail)
    monkeypatch.setattr(social_pipeline, "run_full_pipeline", fail)

    theme_pipeline = __import__("src.pipelines.theme_pipeline", fromlist=[""])
    calls = []
    monkeypatch.setattr(
        theme_pipeline,
        "run_theme_pipeline_from_bundle",
        lambda bundle, **kwargs: calls.append((bundle, kwargs)),
    )

    _run_theme_analysis_command(str(config_path))

    assert len(calls) == 1
    assert calls[0][0].monthly_data["03"].loc[0, "members"] == [1, 2]
    assert calls[0][1]["content_type"] == "reply"


def test_run_theme_analysis_explicit_input_dir_keeps_legacy_fixture_mode(
    monkeypatch, tmp_path
):
    fixture_dir = tmp_path / "fixture-lda"
    fixture_dir.mkdir()
    _write_matched_lda(fixture_dir / "january_2017.csv")
    config_path = _write_config(tmp_path, explicit_input_dir=fixture_dir)

    theme_pipeline = __import__("src.pipelines.theme_pipeline", fromlist=[""])
    calls = []
    monkeypatch.setattr(
        theme_pipeline,
        "run_theme_pipeline",
        lambda **kwargs: calls.append(kwargs),
    )

    _run_theme_analysis_command(str(config_path))

    assert len(calls) == 1
    assert calls[0]["input_dir"] == str(fixture_dir)
    assert calls[0]["content_type"] == "mixed"


def test_run_theme_analysis_missing_inputs_exits_clearly(capsys, tmp_path):
    config_path = _write_config(tmp_path)

    try:
        _run_theme_analysis_command(str(config_path))
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("Expected SystemExit")

    captured = capsys.readouterr()
    assert "make run-topic-sample first" in captured.err
    assert "make run-pipeline-sample" in captured.err
