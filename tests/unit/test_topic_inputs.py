import json

import pandas as pd
import pytest

from src.topics.topic_inputs import (
    MATCHED_COMMUNITY_COLUMNS,
    PARTIAL_MATCHED_COMMUNITY_COLUMNS,
    TopicInputError,
    build_topic_input_dir,
    load_topic_inputs,
    save_topic_inputs,
)


def _save_sample_inputs(tmp_path, *, month="03", year="2017"):
    return save_topic_inputs(
        absolute_community_messages=pd.DataFrame(
            {
                "community_number": [0],
                "messages": [["alpha text", "beta text"]],
                "messages_ids": [[1, 2]],
                "total_messages": [2],
            }
        ),
        weighted_community_messages=pd.DataFrame(
            {
                "community_number": [0],
                "messages": [["weighted text"]],
                "messages_ids": [[3]],
                "total_messages": [1],
            }
        ),
        matched_communities=pd.DataFrame(
            {
                "abs_community": [0],
                "per_community": [0],
                "jaccard_score": [1.0],
                "members": [[10, 20]],
            }
        ),
        partial_matched_communities=pd.DataFrame(columns=PARTIAL_MATCHED_COMMUNITY_COLUMNS),
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        month=month,
        year=year,
    )


def test_topic_input_save_load_round_trip_with_list_columns(tmp_path):
    _save_sample_inputs(tmp_path)

    bundle = load_topic_inputs(
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        month="03",
        year="2017",
    )

    assert bundle.absolute_community_messages.loc[0, "messages"] == ["alpha text", "beta text"]
    assert bundle.absolute_community_messages.loc[0, "messages_ids"] == [1, 2]
    assert bundle.matched_communities.loc[0, "members"] == [10, 20]
    assert bundle.manifest["schema_version"] == 1


def test_empty_partial_matches_round_trip_with_headers(tmp_path):
    _save_sample_inputs(tmp_path)

    bundle = load_topic_inputs(
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        month="03",
        year="2017",
    )

    assert bundle.partial_matched_communities.empty
    assert list(bundle.partial_matched_communities.columns) == PARTIAL_MATCHED_COMMUNITY_COLUMNS


def test_missing_topic_inputs_explain_to_run_social_network_first(tmp_path):
    with pytest.raises(TopicInputError, match="Run run-social-network first"):
        load_topic_inputs(
            output_base_path=str(tmp_path),
            data_type="twitter",
            content_type="reply",
            month="03",
            year="2017",
        )


def test_manifest_mismatch_is_reported(tmp_path):
    topic_dir = _save_sample_inputs(tmp_path)
    manifest_path = topic_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["content_type"] = "retweet"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(TopicInputError, match="metadata does not match"):
        load_topic_inputs(
            output_base_path=str(tmp_path),
            data_type="twitter",
            content_type="reply",
            month="03",
            year="2017",
        )


def test_build_topic_input_dir_uses_internal_additive_path(tmp_path):
    path = build_topic_input_dir(
        {
            "output_base_path": str(tmp_path),
            "data_type": "twitter",
            "content_type": "reply",
            "month": "03",
            "year": "2017",
        }
    )

    assert path == tmp_path / "twitter" / "_intermediate" / "topic_inputs" / "reply" / "03_2017"


def test_required_columns_are_validated(tmp_path):
    topic_dir = _save_sample_inputs(tmp_path)
    pd.DataFrame({"abs_community": [0]}).to_csv(topic_dir / "matched_communities.csv", index=False)

    with pytest.raises(TopicInputError, match="missing required columns"):
        load_topic_inputs(
            output_base_path=str(tmp_path),
            data_type="twitter",
            content_type="reply",
            month="03",
            year="2017",
        )


def test_matched_headers_are_preserved(tmp_path):
    _save_sample_inputs(tmp_path)
    bundle = load_topic_inputs(
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        month="03",
        year="2017",
    )

    assert list(bundle.matched_communities.columns) == MATCHED_COMMUNITY_COLUMNS
