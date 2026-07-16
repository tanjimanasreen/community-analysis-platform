from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.themes.benchmark.contracts import ThemeBenchmarkError, read_jsonl
from src.themes.benchmark.dataset import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    benchmark_root,
    build_dataset,
    format_keywords_for_production,
)
from src.themes.benchmark.review import export_blinded_review, validate_review_import
from src.themes.benchmark.runner import run_benchmark
from src.themes.theme_inputs import save_theme_inputs

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "theme_benchmark"
    / "matched_lda.csv"
)


def _config(tmp_path):
    return {
        "data_type": "twitter",
        "content_type": "reply",
        "month": "03",
        "year": "2017",
        "input_path": "unused.csv",
        "output_base_path": str(tmp_path / "outputs"),
        "creator_relation": "REPLIED_TO",
        "spreader_relation": "REPLIED_BY",
        "creator_node_column": "target",
        "spreader_node_column": "target",
        "text_node_column": "source",
        "date_column": "created_at",
    }


def _save_theme_fixture(config, *, month="03"):
    return save_theme_inputs(
        matched_lda_csv=FIXTURE,
        output_base_path=config["output_base_path"],
        data_type=config["data_type"],
        content_type=config["content_type"],
        month=month,
        year=config["year"],
    )


def test_build_dataset_preserves_original_keyword_fields_and_is_reproducible(tmp_path):
    config = _config(tmp_path)
    _save_theme_fixture(config)

    first = build_dataset(config, run_id="offline-test", limit=10)
    second = build_dataset(config, run_id="offline-test", limit=10)

    assert first["manifest"]["example_count"] == 2
    assert first["manifest"]["limit_requested"] == 10
    assert first["manifest"]["dataset_hash"] == second["manifest"]["dataset_hash"]

    rows = read_jsonl(first["output_dir"] / "dataset.jsonl")
    assert rows[0]["absolute_unigram_keywords"] == ["apple", "banana", "apple"]
    assert rows[0]["absolute_bigram_keywords"] == ["big apple"]
    assert rows[0]["weighted_unigram_keywords"] == ["orange"]
    assert rows[0]["weighted_bigram_keywords"] == ["big orange"]
    assert rows[0]["absolute_keywords"] == ["apple", "banana", "big apple"]
    assert rows[0]["absolute_keyword_text"] == "apple,banana,bigapple"
    assert rows[0]["general_keyword_text"] == "apple,banana,bigapple,orange,bigorange"
    assert rows[0]["members_count"] == 3


def test_limit_uses_available_examples_without_synthesis(tmp_path):
    config = _config(tmp_path)
    _save_theme_fixture(config)

    limited = build_dataset(config, run_id="limited", limit=1)

    rows = read_jsonl(limited["output_dir"] / "dataset.jsonl")
    assert len(rows) == 1
    assert limited["manifest"]["example_count"] == 1


def test_requests_match_current_production_theme_task(tmp_path):
    config = _config(tmp_path)
    _save_theme_fixture(config)

    result = build_dataset(config, run_id="prompt-check", limit=1)
    request_rows = read_jsonl(result["output_dir"] / "requests.jsonl")

    general = request_rows[0]
    assert general["keyword_mode"] == "general"
    assert general["keyword_text"] == format_keywords_for_production(
        ["apple", "banana", "big apple", "orange", "big orange"]
    )
    assert general["system_prompt"] == SYSTEM_PROMPT
    assert general["user_prompt"] == USER_PROMPT_TEMPLATE.format(
        keywords="apple,banana,bigapple,orange,bigorange"
    )

    reference = json.loads(
        (result["output_dir"] / "reference" / "gpt4o_config.json").read_text()
    )
    assert reference["model_id"] == "gpt-4o"
    assert reference["temperature"] == 0.0
    assert reference["seed"] == 42
    assert reference["response_format"] == {"type": "json_object"}
    assert reference["user_prompt_template"] == USER_PROMPT_TEMPLATE


def test_path_escape_is_rejected(tmp_path):
    with pytest.raises(ThemeBenchmarkError):
        benchmark_root(tmp_path, "../escape")

    with pytest.raises(ThemeBenchmarkError):
        benchmark_root(tmp_path, "/tmp/escape")


def test_missing_saved_theme_inputs_fails_clearly(tmp_path):
    config = _config(tmp_path)

    with pytest.raises(ThemeBenchmarkError, match="Run run-topics first"):
        build_dataset(config, run_id="missing")


def test_benchmark_run_uses_persistent_jsonl_cache(tmp_path):
    config = _config(tmp_path)
    _save_theme_fixture(config)
    result = build_dataset(config, run_id="cache-test", limit=1)

    first = run_benchmark(
        config, run_id="cache-test", provider_ids=["keyword_baseline"]
    )
    generation_path = result["output_dir"] / "generations" / "keyword_baseline.jsonl"
    generation_path.unlink()
    second = run_benchmark(
        config, run_id="cache-test", provider_ids=["keyword_baseline"]
    )

    assert len(first.results_by_provider["keyword_baseline"]) == 3
    assert first.cache_hits == 0
    assert first.cache_misses == 3
    assert first.provider_executions == 3
    assert all(
        not row["cache_hit"] for row in first.results_by_provider["keyword_baseline"]
    )
    assert len(second.results_by_provider["keyword_baseline"]) == 3
    assert second.cache_hits == 3
    assert second.cache_misses == 0
    assert second.provider_executions == 0
    assert all(
        row["cache_hit"] for row in second.results_by_provider["keyword_baseline"]
    )
    assert (result["output_dir"] / "cache" / "keyword_baseline.jsonl").exists()


def test_benchmark_run_reports_mixed_provider_cache_stats(tmp_path):
    config = _config(tmp_path)
    _save_theme_fixture(config)
    build_dataset(config, run_id="mixed-cache-test", limit=1)

    first = run_benchmark(
        config, run_id="mixed-cache-test", provider_ids=["keyword_baseline", "mock"]
    )
    second = run_benchmark(
        config, run_id="mixed-cache-test", provider_ids=["keyword_baseline", "mock"]
    )

    assert first.request_count == 6
    assert first.result_count == 6
    assert first.cache_hits == 0
    assert first.cache_misses == 6
    assert first.provider_executions == 6
    assert first.failures == 0
    assert second.request_count == 6
    assert second.result_count == 6
    assert second.cache_hits == 6
    assert second.cache_misses == 0
    assert second.provider_executions == 0
    assert second.failures == 0
    assert second.providers["keyword_baseline"].cache_hits == 3
    assert second.providers["mock"].cache_hits == 3


def test_benchmark_run_does_not_cache_failed_results(monkeypatch, tmp_path):
    from src.themes.benchmark.contracts import ProviderMetadata
    from src.themes.benchmark import runner

    class FailingProvider:
        metadata = ProviderMetadata(
            provider_id="failing",
            model_id="failing-v1",
            parameters={"temperature": 0},
        )

        def generate(self, request):
            raise RuntimeError("planned failure")

    config = _config(tmp_path)
    _save_theme_fixture(config)
    build_dataset(config, run_id="failure-cache-test", limit=1)
    monkeypatch.setattr(
        runner, "get_provider", lambda *args, **kwargs: FailingProvider()
    )

    first = runner.run_benchmark(
        config, run_id="failure-cache-test", provider_ids=["failing"]
    )
    second = runner.run_benchmark(
        config, run_id="failure-cache-test", provider_ids=["failing"]
    )

    assert first.failures == 3
    assert first.provider_executions == 3
    assert first.cache_hits == 0
    assert second.failures == 3
    assert second.provider_executions == 3
    assert second.cache_hits == 0
    assert not (first.results_by_provider["failing"][0]["cache_hit"])


def test_blinded_review_export_hides_provider_identities(tmp_path):
    config = _config(tmp_path)
    _save_theme_fixture(config)
    build_dataset(config, run_id="review-test", limit=1)
    run_benchmark(
        config, run_id="review-test", provider_ids=["keyword_baseline", "mock"]
    )

    review_path = export_blinded_review(config["output_base_path"], "review-test")

    text = review_path.read_text(encoding="utf-8")
    assert "keyword_baseline" not in text
    assert "mock" not in text.lower()
    assert "deterministic-keyword-baseline" not in text
    assert "provider_01" in text
    assert "provider_02" in text


def test_review_import_validation_requires_score_columns(tmp_path):
    path = tmp_path / "review.csv"
    pd.DataFrame({"review_id": ["abc"], "fidelity": [1]}).to_csv(path, index=False)

    with pytest.raises(ThemeBenchmarkError, match="missing required columns"):
        validate_review_import(path)


def test_no_api_keys_required_for_offline_benchmark(monkeypatch, tmp_path):
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "LLM7_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    config = _config(tmp_path)
    _save_theme_fixture(config)

    build_dataset(config, run_id="offline-no-keys", limit=1)
    results = run_benchmark(config, run_id="offline-no-keys", provider_ids=["mock"])

    assert len(results.results_by_provider["mock"]) == 3
