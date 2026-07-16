import pandas as pd
import pytest

from src.cli import _run_social_pipeline_command
from src.topics.topic_inputs import PARTIAL_MATCHED_COMMUNITY_COLUMNS, save_topic_inputs


def _write_config(tmp_path):
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "data_type: twitter",
                "content_type: reply",
                'month: "03"',
                'year: "2017"',
                "input_path: does-not-exist.csv",
                f"output_base_path: {tmp_path}",
                "creator_relation: REPLIED_TO",
                "spreader_relation: REPLIED_BY",
                "creator_node_column: target",
                "spreader_node_column: target",
                "text_node_column: source",
                "date_column: created_at",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return config_path


def _save_topic_inputs(tmp_path):
    save_topic_inputs(
        absolute_community_messages=pd.DataFrame(
            {
                "community_number": [0],
                "messages": [["hello topic"]],
                "messages_ids": [[1]],
                "total_messages": [1],
            }
        ),
        weighted_community_messages=pd.DataFrame(
            {
                "community_number": [0],
                "messages": [["hello weighted topic"]],
                "messages_ids": [[2]],
                "total_messages": [1],
            }
        ),
        matched_communities=pd.DataFrame(
            {
                "abs_community": [0],
                "per_community": [0],
                "jaccard_score": [1.0],
                "members": [[1, 2]],
            }
        ),
        partial_matched_communities=pd.DataFrame(
            columns=PARTIAL_MATCHED_COMMUNITY_COLUMNS
        ),
        output_base_path=str(tmp_path),
        data_type="twitter",
        content_type="reply",
        month="03",
        year="2017",
    )


def test_run_topics_loads_saved_inputs_without_network_or_raw_csv(
    monkeypatch, tmp_path
):
    config_path = _write_config(tmp_path)
    _save_topic_inputs(tmp_path)

    pipeline = __import__("src.pipelines.social_network_pipeline", fromlist=[""])

    def fail_network(*args, **kwargs):
        raise AssertionError("run-topics must not call network/community functions")

    calls = []
    monkeypatch.setattr(pipeline, "run_network_phase", fail_network)
    monkeypatch.setattr(pipeline, "run_community_phase", fail_network)
    monkeypatch.setattr(
        pipeline, "run_topic_phase", lambda **kwargs: calls.append(kwargs)
    )

    _run_social_pipeline_command("run-topics", str(config_path))

    assert len(calls) == 1
    assert calls[0]["abs_community_messages"].loc[0, "messages"] == ["hello topic"]


def test_run_topics_missing_inputs_exits_with_clear_message(capsys, tmp_path):
    config_path = _write_config(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        _run_social_pipeline_command("run-topics", str(config_path))

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Run run-social-network first" in captured.err
