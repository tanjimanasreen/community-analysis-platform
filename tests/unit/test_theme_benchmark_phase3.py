from __future__ import annotations

import pandas as pd
import pytest

from src.themes.benchmark.cache import JsonlResponseCache
from src.themes.benchmark.contracts import ThemeBenchmarkError, read_json, read_jsonl
from src.themes.benchmark.freeze import freeze_dataset
from src.themes.benchmark.phase3 import (
    PHASE3_PROVIDERS,
    REVIEW_SCORE_COLUMNS,
    import_phase3_review,
    prepare_phase3_review,
    prepare_stability_subset,
    summarize_stability,
)
from src.themes.benchmark.dataset import load_requests
from src.themes.theme_inputs import save_theme_inputs
from tests.unit.test_theme_benchmark_freeze import FIXTURE, _config


def _seed_phase3_run(config):
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
    frozen = freeze_dataset(
        config,
        run_id="phase3",
        target_examples=4,
        min_examples=3,
        max_examples=4,
        development_count=2,
        pilot_count=1,
    )
    for provider in PHASE3_PROVIDERS:
        _write_cache(config, "phase3", provider, repetition_index=None)
        if provider.startswith("gemini__"):
            _write_cache(config, "phase3", provider, repetition_index=1)
            _write_cache(config, "phase3", provider, repetition_index=2)
    return frozen


def _write_cache(config, run_id, provider, repetition_index):
    from src.themes.benchmark.dataset import benchmark_root

    root = benchmark_root(config["output_base_path"], run_id)
    cache = JsonlResponseCache(root / "cache" / f"{provider}.jsonl")
    model_id = provider.removeprefix("gemini__").replace("_", "-") if provider.startswith("gemini__") else provider
    parameters = {"temperature": 0}
    if repetition_index is not None:
        parameters["repetition_index"] = repetition_index
    for request in load_requests(config["output_base_path"], run_id):
        if request.keyword_mode != "general":
            continue
        cache_key = cache.cache_key(
            provider_id=provider,
            model_id=model_id,
            request=request,
            parameters=parameters,
        )
        cache.put(
            cache_key,
            {
                "provider_id": provider,
                "model_id": model_id,
                "request_id": __import__("src.themes.benchmark.contracts", fromlist=["stable_hash"]).stable_hash(request.to_dict()),
                "normalized_theme_json": {
                    "themes": [{"name": "Shared civic theme", "keywords": request.keywords[:1]}]
                },
                "benchmark_metadata": {"schema_valid": True, "parsed_successfully": True},
                "latency_ms": 1.0,
                "parameters": parameters,
            },
        )


def test_phase3_review_cohort_is_deterministic_blinded_and_heldout_free(tmp_path):
    config = _config(tmp_path)
    frozen = _seed_phase3_run(config)

    first = prepare_phase3_review(config["output_base_path"], "phase3")
    second = prepare_phase3_review(config["output_base_path"], "phase3")

    assert first["cohort"]["cohort_hash"] == second["cohort"]["cohort_hash"]
    assert first["cohort"]["example_count"] == 3
    heldout = {
        row["example_id"]
        for row in read_jsonl(frozen["output_dir"] / "dataset.jsonl")
        if row["split"] == "heldout"
    }
    assert not heldout.intersection({item["example_id"] for item in first["cohort"]["items"]})
    review_text = (first["review_dir"] / "review_items.csv").read_text(encoding="utf-8").lower()
    for token in ("gemini", "keyword_baseline", "mock", "llm7"):
        assert token not in review_text
    key = read_json(first["review_dir"] / "blinding_key.json")
    aliases = [item["alias_to_provider"] for item in key["items"]]
    assert all(set(mapping) == {"A", "B", "C"} for mapping in aliases)


def test_phase3_review_import_validates_and_summarizes(tmp_path):
    config = _config(tmp_path)
    _seed_phase3_run(config)
    result = prepare_phase3_review(config["output_base_path"], "phase3")
    items = pd.read_csv(result["review_dir"] / "review_items.csv")
    scored = items[["review_item_id"]].copy()
    scored["reviewer_id"] = "reviewer-1"
    scored["preferred_output"] = "A"
    scored["reviewer_confidence"] = "medium"
    for alias in ("A", "B", "C"):
        for column in REVIEW_SCORE_COLUMNS:
            scored[f"{alias}_{column}"] = 4
    path = tmp_path / "scores.csv"
    scored.to_csv(path, index=False)

    imported = import_phase3_review(config["output_base_path"], "phase3", path)

    assert imported["row_count"] == len(items)
    assert imported["summary"]["inter_rater_reliability"] == "unavailable_single_reviewer"

    bad = scored.copy()
    bad.loc[0, "preferred_output"] = "gemini"
    bad_path = tmp_path / "bad.csv"
    bad.to_csv(bad_path, index=False)
    with pytest.raises(ThemeBenchmarkError):
        import_phase3_review(config["output_base_path"], "phase3", bad_path)


def test_stability_subset_and_summary_are_repetition_aware(tmp_path):
    config = _config(tmp_path)
    _seed_phase3_run(config)

    subset = prepare_stability_subset(config["output_base_path"], "phase3", target_examples=2)
    summary = summarize_stability(config["output_base_path"], "phase3")

    assert subset["subset"]["example_count"] == 2
    assert subset["subset"]["subset_hash"]
    assert summary["report"]["completion_status"] == "complete"
    rows = pd.read_csv(subset["path"].parent / "stability_results.csv")
    assert set(rows["available_repetitions"]) == {"0,1,2"}
