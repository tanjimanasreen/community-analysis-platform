from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.themes.benchmark.contracts import (
    THEME_OUTPUT_JSON_SCHEMA,
    ThemeBenchmarkError,
    build_theme_output_json_schema,
    read_jsonl,
)
from src.themes.benchmark.dataset import (
    RAW_SYSTEM_TEMPLATE,
    RAW_USER_TEMPLATE,
    benchmark_root,
    build_dataset,
    build_gpt4o_reference_metadata,
    format_indexed_keywords_for_prompt,
    format_keywords_for_production,
    get_jinja_env,
)
from src.themes.benchmark.review import export_blinded_review, validate_review_import
from src.themes.benchmark.runner import run_benchmark
from src.themes.theme_inputs import save_theme_inputs

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "theme_benchmark"
    / "matched_lda.parquet"
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
    expected_keywords = ["apple", "banana", "big apple", "orange", "big orange"]
    assert general["keyword_mode"] == "general"
    assert general["keyword_text"] == format_keywords_for_production(
        expected_keywords
    )
    env = get_jinja_env()
    expected_schema = build_theme_output_json_schema(len(expected_keywords))
    assert general["system_prompt"] == env.get_template("system.jinja2").render(
        json_schema=json.dumps(expected_schema, indent=2)
    )
    assert general["user_prompt"] == env.get_template("user.jinja2").render(
        keywords=format_indexed_keywords_for_prompt(expected_keywords)
    )

    reference = json.loads(
        (result["output_dir"] / "reference" / "gpt4o_config.json").read_text()
    )
    assert reference["response_format"]["type"] == "json_schema"
    assert reference["response_format"]["json_schema"]["strict"] is True
    assert reference["system_prompt"] == RAW_SYSTEM_TEMPLATE
    assert reference["user_prompt_template"] == RAW_USER_TEMPLATE


def test_reference_metadata_tracks_current_production_provider_config():
    providers_config = yaml.safe_load(Path("configs/providers.yml").read_text())
    current_primary = providers_config["theme_provider"]["primary"]
    provider_name, current_model = current_primary.split(":", 1)
    reference = build_gpt4o_reference_metadata()

    # The legacy function/artifact name is retained for benchmark compatibility;
    # current-runtime reference metadata follows the configured OpenAI champion.
    assert provider_name == "openai"
    assert reference["model_id"] == current_model
    assert reference["response_format"]["type"] == "json_schema"
    assert reference["response_format"]["json_schema"]["strict"] is True


def test_theme_benchmark_cli_maps_current_reference_option(monkeypatch):
    from src import cli

    captured = {}
    monkeypatch.setattr(cli, "load_config", lambda _path: {})
    monkeypatch.setattr(
        cli,
        "_run_theme_benchmark_command",
        lambda args: captured.update(vars(args)),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "community-analysis",
            "theme-benchmark",
            "build-dataset",
            "--config",
            "tests/configs/test_single_month.yml",
            "--run-id",
            "cli-reference-option",
            "--gpt-5-nano-outputs",
            "prior-outputs.jsonl",
        ],
    )

    cli.main()

    # Internally the dataset builder still accepts the historical gpt4o_outputs
    # parameter so old benchmark artifact plumbing remains compatible.
    assert captured["gpt4o_outputs"] == "prior-outputs.jsonl"


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

    frame = pd.read_parquet(review_path)
    assert "provider_id" not in frame.columns
    assert "model_id" not in frame.columns
    assert set(frame["provider_label"]) == {"provider_01", "provider_02"}
    searchable = frame.astype(str).to_string(index=False).lower()
    assert "keyword_baseline" not in searchable
    assert "mock" not in searchable
    assert "deterministic-keyword-baseline" not in searchable


def test_review_import_validation_requires_score_columns(tmp_path):
    path = tmp_path / "review.parquet"
    pd.DataFrame({"review_id": ["abc"], "fidelity": [1]}).to_parquet(path, index=False)

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
