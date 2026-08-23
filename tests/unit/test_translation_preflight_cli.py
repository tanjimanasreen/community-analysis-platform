from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pandas as pd

import src.cli as cli


def _community_frame(messages):
    return pd.DataFrame(
        {
            "community_number": [1],
            "messages": [messages],
            "messages_ids": [[f"m{i}" for i in range(len(messages))]],
            "total_messages": [len(messages)],
        }
    )


def test_translation_preflight_runs_network_only_and_reports_cloud_free_plan(
    monkeypatch, tmp_path, capsys
):
    config = {
        "data_type": "telegram",
        "content_type": "forward",
        "year": "2019",
        "output_base_path": str(tmp_path / "output"),
        "creator_relation": "PRODUCED",
        "spreader_relation": "FORWARDED_BY",
        "creator_node_column": "source",
        "spreader_node_column": "target",
        "text_node_column": "target",
        "date_column": "forwarded_date",
        "translation": {
            "enabled": True,
            "provider": "azure",
            "target_language": "en",
            "contract_version": "v1",
            "cache_path": str(tmp_path / "translation.sqlite3"),
        },
        "longitudinal_datasets": [
            {"month": "01", "input_path": "/data/january.csv"},
            {"month": "02", "input_path": "/data/february.csv"},
        ],
    }
    monkeypatch.setattr(cli, "validate_config", lambda _path: config)
    monkeypatch.setattr(cli, "validate_run_config", lambda _config: None)

    calls = []

    def fake_run_monthly_analysis_flow(**kwargs):
        assert kwargs["run_topics"] is False
        assert kwargs["run_themes"] is False
        calls.append(kwargs)
        month = str(kwargs["config"]["month"])
        return SimpleNamespace(
            context=SimpleNamespace(
                output_root=str(tmp_path / "output"),
                pipeline_run_id=f"network-only-{month}",
            )
        )

    fake_composition = types.ModuleType("src.orchestration.composition_flow")
    fake_composition.run_monthly_analysis_flow = fake_run_monthly_analysis_flow
    monkeypatch.setitem(
        sys.modules, "src.orchestration.composition_flow", fake_composition
    )

    import src.topics.topic_inputs as topic_inputs

    def fake_load_topic_inputs(**kwargs):
        month = str(kwargs["month"])
        if month == "01":
            absolute = _community_frame(["hello", "olá"])
            weighted = _community_frame(["hello"])
        else:
            absolute = _community_frame(["olá", "مرحبا"])
            weighted = _community_frame([])
        return SimpleNamespace(
            absolute_community_messages=absolute,
            weighted_community_messages=weighted,
        )

    monkeypatch.setattr(topic_inputs, "load_topic_inputs", fake_load_topic_inputs)

    cli._run_translation_preflight_command("fake.yml")

    output = capsys.readouterr().out
    assert len(calls) == 2
    assert (
        "Translation preflight (no cloud detection/translation calls made):" in output
    )
    assert "datasets_prepared: 2" in output
    assert "message_occurrences: 5" in output
    assert "unique_messages: 3" in output
    assert "translation_cache_hits: 0" in output
    assert "translation_cache_misses: 3" in output
    assert "language_detection_requests: 1" in output
    assert (tmp_path / "translation.sqlite3").exists() is False


def test_translation_detect_reports_exact_post_detection_workload(
    monkeypatch, tmp_path, capsys
):
    from src.text.translation import TranslationDetectionIssue, TranslationDetectionPlan

    config = {
        "data_type": "telegram",
        "content_type": "forward",
        "year": "2019",
        "output_base_path": str(tmp_path / "output"),
        "creator_relation": "PRODUCED",
        "spreader_relation": "FORWARDED_BY",
        "creator_node_column": "source",
        "spreader_node_column": "target",
        "text_node_column": "target",
        "date_column": "forwarded_date",
        "translation": {
            "enabled": True,
            "provider": "azure",
            "target_language": "en",
            "contract_version": "v1",
            "cache_path": str(tmp_path / "translation.sqlite3"),
        },
        "longitudinal_datasets": [
            {"month": "01", "input_path": "/data/january.csv"},
        ],
    }
    monkeypatch.setattr(cli, "validate_config", lambda _path: config)
    monkeypatch.setattr(cli, "validate_run_config", lambda _config: None)

    def fake_run_monthly_analysis_flow(**kwargs):
        assert kwargs["run_topics"] is False
        assert kwargs["run_themes"] is False
        return SimpleNamespace(
            context=SimpleNamespace(
                output_root=str(tmp_path / "output"),
                pipeline_run_id="network-only-01",
            )
        )

    fake_composition = types.ModuleType("src.orchestration.composition_flow")
    fake_composition.run_monthly_analysis_flow = fake_run_monthly_analysis_flow
    monkeypatch.setitem(
        sys.modules, "src.orchestration.composition_flow", fake_composition
    )

    import src.topics.topic_inputs as topic_inputs
    import src.text.translation as translation

    monkeypatch.setattr(
        topic_inputs,
        "load_topic_inputs",
        lambda **_kwargs: SimpleNamespace(
            absolute_community_messages=_community_frame(["hello", "olá"]),
            weighted_community_messages=_community_frame([]),
        ),
    )

    seen = {}

    def fake_detect(texts, *, options):
        seen["texts"] = list(texts)
        seen["provider"] = options.provider
        return TranslationDetectionPlan(
            provider="azure",
            target_language="en",
            contract_version="v1",
            total_message_occurrences=2,
            unique_message_count=2,
            translation_cache_hit_count=0,
            detection_cache_hit_count=0,
            newly_detected_count=2,
            language_detection_request_count=1,
            target_language_count=1,
            translation_candidate_count=1,
            translation_candidate_character_count=3,
            exact_translation_request_count=1,
            unsupported_translation_count=1,
            potential_item_limit_count=0,
            language_counts={"bn-latn": 1, "en": 1},
            azure_auto_detect_fallback_count=1,
            azure_auto_detect_fallback_request_count=1,
            issues=(
                TranslationDetectionIssue(
                    source_text="olá",
                    source_hash="abc123",
                    detected_language="bn-latn",
                    language_confidence=0.7,
                    character_count=3,
                    reason="detected_language_not_translation_supported",
                    fallback_strategy="azure_translate_auto_detect",
                    blocks_full_run=False,
                ),
            ),
        )

    monkeypatch.setattr(translation, "detect_texts_with_cache", fake_detect)

    cli._run_translation_detect_command("fake.yml")

    output = capsys.readouterr().out
    assert seen["provider"] == "azure"
    assert seen["texts"] == ["hello", "olá"]
    assert "language detection only; no translation calls made" in output
    assert "language_detection_requests_made: 1" in output
    assert "messages_requiring_translation: 1" in output
    assert "exact_translation_requests: 1" in output
    assert "en: 1" in output
    assert "bn-latn: 1" in output
    assert "azure_auto_detect_fallback_messages: 1" in output
    assert "azure_auto_detect_fallback_requests: 1" in output
    assert "source-language auto-detection" in output
    audit = (
        tmp_path / "output" / "_preflight" / "translation_detection_issues_all.jsonl"
    )
    assert audit.is_file()
    assert '"original_text": "olá"' in audit.read_text(encoding="utf-8")
