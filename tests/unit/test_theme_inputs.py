import json

import pandas as pd
import pytest

from src.themes.theme_inputs import (
    REQUIRED_COLUMNS,
    ThemeInputError,
    build_theme_input_dir,
    load_theme_inputs,
    save_theme_inputs,
)


def _matched_lda_frame():
    return pd.DataFrame(
        {
            "members": ["[1, 2]"],
            "absolute_community": [0],
            "weighted_community": [0],
            "absolute_unigram_keywords": ["['apple']"],
            "absolute_bigram_keywords": ["['big apple']"],
            "weighted_unigram_keywords": ["['orange']"],
            "weighted_bigram_keywords": ["['big orange']"],
        }
    )


def _write_matched_csv(tmp_path, name="03_2017.csv"):
    path = tmp_path / name
    _matched_lda_frame().to_csv(path, index=False)
    return path


def test_theme_input_save_load_round_trip_with_list_columns(tmp_path):
    matched_csv = _write_matched_csv(tmp_path)
    save_theme_inputs(
        matched_lda_csv=matched_csv,
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        month="03",
        year="2017",
    )

    bundle = load_theme_inputs(
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        year="2017",
    )

    frame = bundle.monthly_data["03"]
    assert frame.loc[0, "members"] == [1, 2]
    assert frame.loc[0, "absolute_unigram_keywords"] == ["apple"]
    assert frame.loc[0, "weighted_bigram_keywords"] == ["big orange"]
    assert bundle.manifest["created_by"] == "run-topics"
    assert bundle.manifest["lda"]["num_topics"] == 15


def test_theme_input_missing_manifest_explains_run_topics_first(tmp_path):
    with pytest.raises(ThemeInputError, match="Run run-topics first"):
        load_theme_inputs(
            output_base_path=str(tmp_path),
            data_type="twitter",
            content_type="reply",
            year="2017",
        )


def test_theme_input_manifest_metadata_mismatch_fails(tmp_path):
    matched_csv = _write_matched_csv(tmp_path)
    input_dir = save_theme_inputs(
        matched_lda_csv=matched_csv,
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        month="03",
        year="2017",
    )
    manifest_path = input_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["content_type"] = "retweet"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ThemeInputError, match="metadata does not match"):
        load_theme_inputs(
            output_base_path=str(tmp_path),
            data_type="twitter",
            content_type="reply",
            year="2017",
        )


def test_theme_input_manifest_hash_mismatch_fails(tmp_path):
    matched_csv = _write_matched_csv(tmp_path)
    input_dir = save_theme_inputs(
        matched_lda_csv=matched_csv,
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        month="03",
        year="2017",
    )
    (input_dir / "03_2017.csv").write_text("corrupted\n", encoding="utf-8")

    with pytest.raises(ThemeInputError, match="hash mismatch"):
        load_theme_inputs(
            output_base_path=str(tmp_path),
            data_type="twitter",
            content_type="reply",
            year="2017",
        )


def test_explicit_theme_input_dir_can_load_without_manifest(tmp_path):
    _write_matched_csv(tmp_path, "january_2017.csv")

    bundle = load_theme_inputs(input_dir=tmp_path, year="2017", require_manifest=False)

    assert "january" in bundle.monthly_data
    assert bundle.manifest is None


def test_theme_input_required_columns_are_validated(tmp_path):
    path = tmp_path / "03_2017.csv"
    pd.DataFrame({"members": ["[1]"]}).to_csv(path, index=False)

    missing_columns = [column for column in REQUIRED_COLUMNS if column != "members"]
    with pytest.raises(ThemeInputError, match=missing_columns[0]):
        save_theme_inputs(
            matched_lda_csv=path,
            output_base_path=str(tmp_path),
            data_type="twitter",
            content_type="reply",
            month="03",
            year="2017",
        )


def test_build_theme_input_dir_uses_internal_path(tmp_path):
    assert build_theme_input_dir(
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        year="2017",
    ) == tmp_path / "twitter" / "_intermediate" / "theme_inputs" / "reply" / "2017"
