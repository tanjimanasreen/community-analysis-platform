from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.themes.benchmark.contracts import (
    BenchmarkProviderStats,
    ThemeBenchmarkError,
    read_json,
    read_jsonl,
    write_json,
)
from src.themes.benchmark.freeze import freeze_dataset, inventory_artifacts
from src.themes.benchmark.integrity import validate_frozen_dataset
from src.themes.benchmark.review import REVIEW_SCORE_COLUMNS, validate_review_import
from src.themes.benchmark.runner import _update_manifest, run_benchmark
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


def _save_two_months(config):
    save_theme_inputs(
        matched_lda_csv=FIXTURE,
        output_base_path=config["output_base_path"],
        data_type=config["data_type"],
        content_type=config["content_type"],
        month="03",
        year=config["year"],
    )
    save_theme_inputs(
        matched_lda_csv=FIXTURE,
        output_base_path=config["output_base_path"],
        data_type=config["data_type"],
        content_type=config["content_type"],
        month="04",
        year=config["year"],
    )


def test_inventory_artifacts_records_saved_theme_input_counts_and_hashes(tmp_path):
    config = _config(tmp_path)
    _save_two_months(config)

    result = inventory_artifacts(config)

    inventory = result["inventory"]
    assert inventory["source_count"] == 1
    assert inventory["row_count"] == 4
    assert inventory["valid_example_count"] == 4
    assert inventory["rejected_row_count"] == 0
    assert inventory["inventory_hash"]
    assert len(inventory["source_artifact_hashes"]) == 2
    assert (result["output_dir"] / "inventory.json").exists()
    written = read_json(result["output_dir"] / "inventory.json")
    assert written["inventory_hash"] == inventory["inventory_hash"]


def test_freeze_dataset_is_deterministic_and_preserves_keyword_fields(tmp_path):
    config = _config(tmp_path)
    _save_two_months(config)

    first = freeze_dataset(
        config,
        run_id="frozen-v1",
        target_examples=4,
        min_examples=3,
        max_examples=4,
        development_count=2,
        pilot_count=1,
    )
    second = freeze_dataset(
        config,
        run_id="frozen-v1",
        target_examples=4,
        min_examples=3,
        max_examples=4,
        development_count=2,
        pilot_count=1,
    )

    assert first["manifest"]["dataset_hash"] == second["manifest"]["dataset_hash"]
    assert first["manifest"]["split_hash"] == second["manifest"]["split_hash"]
    assert first["manifest"]["example_count"] == 4
    assert first["manifest"]["split_counts"] == {
        "development": 2,
        "pilot": 1,
        "heldout": 1,
    }
    rows = read_jsonl(first["output_dir"] / "dataset.jsonl")
    assert {row["split"] for row in rows} == {"development", "pilot", "heldout"}
    assert rows[0]["absolute_unigram_keywords"] == ["apple", "banana", "apple"]
    assert rows[0]["absolute_bigram_keywords"] == ["big apple"]
    assert rows[0]["weighted_unigram_keywords"] == ["orange"]
    assert rows[0]["weighted_bigram_keywords"] == ["big orange"]
    assert rows[0]["frozen_dataset_schema_version"] == 1
    assert rows[0]["source_artifact_hash"]
    assert (first["output_dir"] / "reference" / "gpt4o_config.json").exists()


def test_freeze_dataset_fails_when_saved_artifacts_have_too_few_valid_examples(
    tmp_path,
):
    config = _config(tmp_path)
    save_theme_inputs(
        matched_lda_csv=FIXTURE,
        output_base_path=config["output_base_path"],
        data_type=config["data_type"],
        content_type=config["content_type"],
        month="03",
        year=config["year"],
    )

    with pytest.raises(ThemeBenchmarkError, match="requires at least 3 valid examples"):
        freeze_dataset(config, run_id="too-small", target_examples=3, min_examples=3)


def test_freeze_dataset_rejects_escaping_run_id(tmp_path):
    config = _config(tmp_path)
    _save_two_months(config)

    with pytest.raises(ThemeBenchmarkError):
        freeze_dataset(config, run_id="../escape", target_examples=4, min_examples=3)


def test_freeze_dataset_refuses_different_existing_manifest_without_overwrite(tmp_path):
    config = _config(tmp_path)
    _save_two_months(config)
    freeze_dataset(
        config,
        run_id="overwrite-guard",
        target_examples=4,
        min_examples=3,
        max_examples=4,
        development_count=2,
        pilot_count=1,
    )

    with pytest.raises(ThemeBenchmarkError, match="Refusing to overwrite"):
        freeze_dataset(
            config,
            run_id="overwrite-guard",
            target_examples=3,
            min_examples=3,
            max_examples=4,
            development_count=1,
            pilot_count=1,
        )

    replaced = freeze_dataset(
        config,
        run_id="overwrite-guard",
        target_examples=3,
        min_examples=3,
        max_examples=4,
        development_count=1,
        pilot_count=1,
        overwrite=True,
    )
    assert replaced["manifest"]["example_count"] == 3


def test_validate_frozen_dataset_writes_split_distribution_report(tmp_path):
    config = _config(tmp_path)
    _save_two_months(config)
    frozen = freeze_dataset(
        config,
        run_id="integrity",
        target_examples=4,
        min_examples=3,
        max_examples=4,
        development_count=2,
        pilot_count=1,
    )

    report = validate_frozen_dataset(
        config["output_base_path"],
        "integrity",
        expected_dataset_hash=frozen["manifest"]["dataset_hash"],
        expected_split_hash=frozen["manifest"]["split_hash"],
    )

    assert report["example_count"] == 4
    assert report["split_counts"] == {"development": 2, "pilot": 1, "heldout": 1}
    assert report["limited_to_single_data_type"] is True
    assert report["limited_to_single_content_type"] is True
    assert report["limited_to_single_year"] is True
    assert "month" in report["dimensions"]
    assert (frozen["output_dir"] / "reports" / "split_distribution.json").exists()


def test_benchmark_manifest_records_parquet_score_paths(tmp_path):
    root = tmp_path / "benchmark"
    write_json(root / "manifest.json", {"providers": [], "artifacts": {}})
    stats = BenchmarkProviderStats(provider_id="keyword_baseline")

    _update_manifest(
        root,
        ["keyword_baseline"],
        {"keyword_baseline": stats},
        {"keyword_baseline": {}},
        split="development",
    )
    split_manifest = read_json(root / "manifest.json")
    assert (
        split_manifest["artifacts"]["development_scores"]
        == "scores/development_summary.parquet"
    )

    _update_manifest(
        root,
        ["keyword_baseline"],
        {"keyword_baseline": stats},
        {"keyword_baseline": {}},
    )
    manifest = read_json(root / "manifest.json")
    assert manifest["artifacts"]["scores"] == "scores/summary.parquet"


def test_split_aware_benchmark_run_executes_only_requested_split(tmp_path):
    config = _config(tmp_path)
    _save_two_months(config)
    frozen = freeze_dataset(
        config,
        run_id="split-run",
        target_examples=4,
        min_examples=3,
        max_examples=4,
        development_count=2,
        pilot_count=1,
    )

    first = run_benchmark(
        config,
        run_id="split-run",
        provider_ids=["keyword_baseline"],
        keyword_modes=["general"],
        split="development",
    )
    second = run_benchmark(
        config,
        run_id="split-run",
        provider_ids=["keyword_baseline"],
        keyword_modes=["general"],
        split="development",
    )

    assert first.request_count == 2
    assert first.result_count == 2
    assert first.cache_misses == 2
    assert first.provider_executions == 2
    assert second.request_count == 2
    assert second.cache_hits == 2
    assert second.provider_executions == 0
    result_ids = {
        row["example_id"] for row in second.results_by_provider["keyword_baseline"]
    }
    development_ids = {
        row["example_id"]
        for row in read_jsonl(frozen["output_dir"] / "dataset.jsonl")
        if row["split"] == "development"
    }
    assert result_ids == development_ids
    assert (
        frozen["output_dir"] / "generations" / "development" / "keyword_baseline.jsonl"
    ).exists()
    assert (frozen["output_dir"] / "scores" / "development_summary.parquet").exists()


def test_resume_unresolved_runs_only_uncached_failed_requests(monkeypatch, tmp_path):
    from src.themes.benchmark.contracts import ProviderMetadata
    from src.themes.benchmark import runner

    class PartiallyFailingProvider:
        metadata = ProviderMetadata(
            provider_id="partial",
            model_id="partial-v1",
            parameters={"temperature": 0},
        )
        calls = 0

        def generate(self, request):
            type(self).calls += 1
            if type(self).calls == 1:
                raise RuntimeError("planned quota failure")
            return {
                "themes": [
                    {"name": "Recovered theme", "keywords": request.keywords[:1]},
                ]
            }

    class SuccessfulProvider(PartiallyFailingProvider):
        def generate(self, request):
            type(self).calls += 1
            return {
                "themes": [
                    {"name": "Recovered theme", "keywords": request.keywords[:1]},
                ]
            }

    config = _config(tmp_path)
    _save_two_months(config)
    freeze_dataset(
        config,
        run_id="resume-unresolved",
        target_examples=4,
        min_examples=3,
        max_examples=4,
        development_count=2,
        pilot_count=1,
    )
    monkeypatch.setattr(
        runner, "get_provider", lambda *args, **kwargs: PartiallyFailingProvider()
    )
    first = runner.run_benchmark(
        config,
        run_id="resume-unresolved",
        provider_ids=["partial"],
        keyword_modes=["general"],
        split="development",
    )
    assert first.cache_misses == 2
    assert first.failures == 1

    PartiallyFailingProvider.calls = 0
    SuccessfulProvider.calls = 0
    monkeypatch.setattr(
        runner, "get_provider", lambda *args, **kwargs: SuccessfulProvider()
    )
    second = runner.run_benchmark(
        config,
        run_id="resume-unresolved",
        provider_ids=["partial"],
        keyword_modes=["general"],
        split="development",
        resume_unresolved=True,
        max_unresolved_examples=1,
    )
    assert second.request_count == 1
    assert second.cache_hits == 0
    assert second.cache_misses == 1
    assert second.provider_executions == 1
    assert second.failures == 0
    assert SuccessfulProvider.calls == 1

    replay = runner.run_benchmark(
        config,
        run_id="resume-unresolved",
        provider_ids=["partial"],
        keyword_modes=["general"],
        split="development",
    )
    assert replay.cache_hits == 2
    assert replay.cache_misses == 0
    assert replay.provider_executions == 0


def test_review_import_validation_rejects_duplicate_ids_and_provider_leaks(tmp_path):
    valid = {
        "review_id": ["r1", "r2"],
        **{column: [1, 5] for column in REVIEW_SCORE_COLUMNS},
    }
    duplicate_path = tmp_path / "duplicate.parquet"
    pd.DataFrame({**valid, "review_id": ["r1", "r1"]}).to_parquet(
        duplicate_path, index=False
    )
    with pytest.raises(ThemeBenchmarkError, match="duplicate review_id"):
        validate_review_import(duplicate_path)

    leaked_path = tmp_path / "leaked.parquet"
    pd.DataFrame({**valid, "provider_id": ["gemini", "mock"]}).to_parquet(
        leaked_path, index=False
    )
    with pytest.raises(ThemeBenchmarkError, match="provider identity"):
        validate_review_import(leaked_path)

    invalid_score_path = tmp_path / "invalid-score.parquet"
    pd.DataFrame({**valid, "fidelity": [0, 6]}).to_parquet(
        invalid_score_path, index=False
    )
    with pytest.raises(ThemeBenchmarkError, match="scores from 1 to 5"):
        validate_review_import(invalid_score_path)
