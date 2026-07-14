from __future__ import annotations

import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Mapping

import pandas as pd

from src.themes.benchmark.contracts import (
    ThemeBenchmarkError,
    read_json,
    read_jsonl,
    stable_hash,
    write_json,
)
from src.themes.benchmark.dataset import benchmark_root, load_requests
from src.themes.benchmark.metrics import _keyword_coverage


PHASE3_PROVIDERS = [
    "keyword_baseline",
    "gemini__gemini-3.1-flash-lite",
    "gemini__gemini-3.5-flash",
]
STABILITY_PROVIDERS = [
    "gemini__gemini-3.1-flash-lite",
    "gemini__gemini-3.5-flash",
]
REVIEW_SCORE_COLUMNS = [
    "fidelity",
    "coherence",
    "specificity",
    "non_redundancy",
    "usefulness",
    "unsupported_content_absence",
    "overall_quality",
]
PREFERENCE_VALUES = {"A", "B", "C", "tie", "none"}
CONFIDENCE_VALUES = {"low", "medium", "high"}


def prepare_phase3_review(
    output_base_path: str | Path,
    run_id: str,
    *,
    cohort_id: str = "phase3-paired-review-v1",
    target_pilot_examples: int = 20,
) -> dict[str, Any]:
    root = benchmark_root(output_base_path, run_id)
    manifest = read_json(root / "manifest.json")
    dataset = read_jsonl(root / "dataset.jsonl")
    requests = load_requests(output_base_path, run_id)
    request_by_example = {
        request.example_id: request
        for request in requests
        if request.keyword_mode == "general"
    }
    cache_by_provider = {provider: _cache_by_example(root, provider, request_by_example) for provider in PHASE3_PROVIDERS}
    complete_by_split = _shared_complete_examples(dataset, cache_by_provider)
    development_examples = sorted(complete_by_split["development"], key=lambda row: row["example_id"])
    pilot_candidates = complete_by_split["pilot"]
    selected_pilot = _select_examples(pilot_candidates, target_pilot_examples, seed="phase3-paired-review-v1")
    selected = development_examples + selected_pilot
    selected_ids = {row["example_id"] for row in selected}

    excluded = []
    for row in dataset:
        example_id = str(row["example_id"])
        split = str(row["split"])
        if split == "heldout":
            excluded.append({"example_id": example_id, "reason": "heldout_sealed"})
        elif split == "pilot" and example_id not in selected_ids:
            reason = "not_shared_complete" if row not in pilot_candidates else "deterministic_pilot_downsample"
            excluded.append({"example_id": example_id, "reason": reason})

    cohort_items = []
    for row in selected:
        example_id = str(row["example_id"])
        request = request_by_example[example_id]
        provider_results = {
            provider: {
                "request_id": stable_hash(request.to_dict()),
                "cache_key": cache_by_provider[provider][example_id]["cache_key"],
            }
            for provider in PHASE3_PROVIDERS
        }
        cohort_items.append(
            {
                "example_id": example_id,
                "source_split": row["split"],
                "provider_results": provider_results,
            }
        )
    cohort = {
        "schema_version": 1,
        "cohort_id": cohort_id,
        "dataset_hash": manifest["dataset_hash"],
        "split_hash": manifest["split_hash"],
        "prompt_hash": manifest["prompt_hash"],
        "schema_versions": {
            "dataset": manifest.get("dataset_schema_version"),
            "request": manifest.get("request_schema_version"),
            "frozen_dataset": manifest.get("frozen_dataset_schema_version"),
        },
        "selection_algorithm": "all shared-complete development plus hash-stratified shared-complete pilot downsample",
        "selection_seed": "phase3-paired-review-v1",
        "providers": PHASE3_PROVIDERS,
        "example_count": len(cohort_items),
        "development_count": len(development_examples),
        "pilot_count": len(selected_pilot),
        "items": cohort_items,
        "excluded_examples": excluded,
    }
    cohort["cohort_hash"] = stable_hash({key: value for key, value in cohort.items() if key != "cohort_hash"})

    review_dir = root / "review" / "phase3"
    review_dir.mkdir(parents=True, exist_ok=True)
    write_json(review_dir / "cohort_manifest.json", cohort)
    review_rows, blinding_rows = _build_review_rows(cohort_items, dataset, request_by_example, cache_by_provider, cohort_id)
    pd.DataFrame(review_rows).to_csv(review_dir / "review_items.csv", index=False)
    write_json(review_dir / "blinding_key.json", {"schema_version": 1, "cohort_id": cohort_id, "items": blinding_rows})
    review_manifest = {
        "schema_version": 1,
        "cohort_id": cohort_id,
        "cohort_hash": cohort["cohort_hash"],
        "review_item_count": len(review_rows),
        "reviewer_facing_artifact": "review_items.csv",
        "private_mapping_artifact": "blinding_key.json",
        "contains_provider_names_in_reviewer_file": _contains_provider_leakage(review_dir / "review_items.csv"),
    }
    write_json(review_dir / "review_manifest.json", review_manifest)
    _write_review_instructions(review_dir / "review_instructions.md")
    if review_manifest["contains_provider_names_in_reviewer_file"]:
        raise ThemeBenchmarkError("Reviewer-facing Phase 3 export contains provider identity leakage.")
    return {"review_dir": review_dir, "cohort": cohort, "review_manifest": review_manifest}


def import_phase3_review(output_base_path: str | Path, run_id: str, scores_path: str | Path) -> dict[str, Any]:
    root = benchmark_root(output_base_path, run_id)
    review_dir = root / "review" / "phase3"
    items = pd.read_csv(review_dir / "review_items.csv")
    known_items = set(items["review_item_id"].astype(str))
    key = read_json(review_dir / "blinding_key.json")
    mapping = {
        (item["review_item_id"], alias): provider
        for item in key["items"]
        for alias, provider in item["alias_to_provider"].items()
    }
    frame = pd.read_csv(scores_path)
    _validate_review_scores(frame, known_items)
    rows = []
    for _, row in frame.iterrows():
        review_item_id = str(row["review_item_id"])
        for alias in ("A", "B", "C"):
            provider = mapping[(review_item_id, alias)]
            rows.append(
                {
                    "reviewer_id": row["reviewer_id"],
                    "review_item_id": review_item_id,
                    "provider_id": provider,
                    "alias": alias,
                    **{column: float(row[f"{alias}_{column}"]) for column in REVIEW_SCORE_COLUMNS},
                    "preferred": str(row["preferred_output"]) == alias,
                }
            )
    unblinded = pd.DataFrame(rows)
    imported_path = review_dir / "review_scores_unblinded.csv"
    unblinded.to_csv(imported_path, index=False)
    summary = _review_summary(unblinded, frame)
    summary_path = review_dir / "review_summary.json"
    write_json(summary_path, summary)
    return {"summary_path": summary_path, "imported_path": imported_path, "row_count": len(frame), "summary": summary}


def prepare_stability_subset(
    output_base_path: str | Path,
    run_id: str,
    *,
    subset_id: str = "phase3-stability-v1",
    target_examples: int = 10,
) -> dict[str, Any]:
    root = benchmark_root(output_base_path, run_id)
    manifest = read_json(root / "manifest.json")
    dataset = read_jsonl(root / "dataset.jsonl")
    requests = load_requests(output_base_path, run_id)
    request_by_example = {request.example_id: request for request in requests if request.keyword_mode == "general"}
    cache_by_provider = {provider: _cache_by_example(root, provider, request_by_example) for provider in STABILITY_PROVIDERS}
    candidates = [
        row for row in dataset
        if row.get("split") == "development"
        and all(row["example_id"] in cache_by_provider[provider] for provider in STABILITY_PROVIDERS)
    ]
    selected = _select_examples(candidates, target_examples, seed=subset_id)
    subset = {
        "schema_version": 1,
        "subset_id": subset_id,
        "dataset_hash": manifest["dataset_hash"],
        "split_hash": manifest["split_hash"],
        "prompt_hash": manifest["prompt_hash"],
        "model_ids": STABILITY_PROVIDERS,
        "selection_policy": "hash-stratified development examples with complete Gemini Phase 2 outputs",
        "selection_seed": subset_id,
        "example_count": len(selected),
        "example_ids": [row["example_id"] for row in selected],
        "source_hashes": manifest.get("source_artifact_hashes", {}),
    }
    subset["subset_hash"] = stable_hash({key: value for key, value in subset.items() if key != "subset_hash"})
    path = root / "scores" / "stability_subset.json"
    write_json(path, subset)
    return {"path": path, "subset": subset}


def summarize_stability(output_base_path: str | Path, run_id: str, *, subset_id: str = "phase3-stability-v1") -> dict[str, Any]:
    root = benchmark_root(output_base_path, run_id)
    subset = read_json(root / "scores" / "stability_subset.json")
    requests = load_requests(output_base_path, run_id)
    request_by_example = {request.example_id: request for request in requests if request.keyword_mode == "general"}
    rows = []
    summary_rows = []
    for provider in STABILITY_PROVIDERS:
        provider_rows = []
        for example_id in subset["example_ids"]:
            reps = {
                rep: _cache_record_for(root, provider, request_by_example[example_id], rep)
                for rep in (0, 1, 2)
            }
            available = {rep: row for rep, row in reps.items() if row is not None}
            metrics = _stability_metrics(available)
            row = {
                "provider_id": provider,
                "example_id": example_id,
                "available_repetitions": ",".join(str(rep) for rep in sorted(available)),
                **metrics,
            }
            rows.append(row)
            provider_rows.append(row)
        complete = [row for row in provider_rows if row["complete_repetitions"]]
        summary_rows.append(
            {
                "provider_id": provider,
                "examples": len(provider_rows),
                "complete_examples": len(complete),
                "mean_exact_json_agreement": _mean([row["exact_json_agreement"] for row in complete]),
                "mean_keyword_jaccard": _mean([row["keyword_jaccard_agreement"] for row in complete]),
                "completion_status": "complete" if len(complete) == len(provider_rows) else "partial",
            }
        )
    scores_dir = root / "scores"
    pd.DataFrame(rows).to_csv(scores_dir / "stability_results.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(scores_dir / "stability_summary.csv", index=False)
    report = {
        "schema_version": 1,
        "subset_id": subset_id,
        "subset_hash": subset["subset_hash"],
        "providers": summary_rows,
        "completion_status": "complete" if all(row["completion_status"] == "complete" for row in summary_rows) else "partial",
        "notes": "Phase 3 stability only; unequal coverage is labeled partial and no winner is selected.",
    }
    report_path = scores_dir / "phase3_stability_report.json"
    write_json(report_path, report)
    return {"report_path": report_path, "report": report}


def _cache_by_example(root: Path, provider: str, request_by_example: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    request_id_to_example = {stable_hash(request.to_dict()): example_id for example_id, request in request_by_example.items()}
    rows = {}
    for record in read_jsonl(root / "cache" / f"{provider}.jsonl"):
        example_id = request_id_to_example.get(record.get("request_id"))
        if example_id and record.get("normalized_theme_json"):
            rows[example_id] = record
    return rows


def _shared_complete_examples(dataset: list[dict[str, Any]], cache_by_provider: Mapping[str, Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_split = {"development": [], "pilot": []}
    for row in dataset:
        split = row.get("split")
        if split not in by_split:
            continue
        example_id = str(row["example_id"])
        if all(example_id in cache_by_provider[provider] for provider in PHASE3_PROVIDERS):
            by_split[str(split)].append(row)
    return by_split


def _select_examples(candidates: list[Mapping[str, Any]], target: int, *, seed: str) -> list[Mapping[str, Any]]:
    strata: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in candidates:
        strata[(_member_bin(row), _keyword_bin(row), str(row.get("month")))].append(row)
    for rows in strata.values():
        rows.sort(key=lambda row: stable_hash({"seed": seed, "example_id": row["example_id"], "input_hash": row["input_hash"]}))
    selected = []
    keys = sorted(strata)
    while len(selected) < min(target, len(candidates)):
        progressed = False
        for key in keys:
            if strata[key]:
                selected.append(strata[key].pop(0))
                progressed = True
                if len(selected) >= target:
                    break
        if not progressed:
            break
    return sorted(selected, key=lambda row: str(row["example_id"]))


def _build_review_rows(cohort_items, dataset, request_by_example, cache_by_provider, cohort_id):
    data_by_id = {row["example_id"]: row for row in dataset}
    review_rows = []
    key_rows = []
    permutations = list(itertools.permutations(PHASE3_PROVIDERS))
    for index, item in enumerate(sorted(cohort_items, key=lambda row: row["example_id"])):
        example_id = item["example_id"]
        aliases = ("A", "B", "C")
        provider_order = permutations[index % len(permutations)]
        alias_to_provider = dict(zip(aliases, provider_order))
        review_item_id = stable_hash({"cohort_id": cohort_id, "example_id": example_id})[:16]
        row = {
            "review_item_id": review_item_id,
            "example_id": example_id,
            "source_split": data_by_id[example_id]["split"],
            "ordered_lda_keywords": ", ".join(request_by_example[example_id].keywords),
        }
        for alias, provider in alias_to_provider.items():
            row[f"output_{alias}"] = json.dumps(cache_by_provider[provider][example_id]["normalized_theme_json"], sort_keys=True)
        for alias in aliases:
            for column in REVIEW_SCORE_COLUMNS:
                row[f"{alias}_{column}"] = ""
        row.update({"preferred_output": "", "reviewer_confidence": "", "reviewer_id": "", "comments": ""})
        review_rows.append(row)
        key_rows.append({"review_item_id": review_item_id, "example_id": example_id, "alias_to_provider": alias_to_provider})
    return review_rows, key_rows


def _write_review_instructions(path: Path) -> None:
    text = """# Phase 3 Review Instructions

Score each output from 1 to 5, where 1 is poor and 5 is strong. For
`unsupported_content_absence`, 1 means severe unsupported or hallucinated content
and 5 means no unsupported content. Do not infer provider identities. Choose
`preferred_output` as A, B, C, tie, or none, and set reviewer confidence to low,
medium, or high.
"""
    path.write_text(text, encoding="utf-8")


def _validate_review_scores(frame: pd.DataFrame, known_items: set[str]) -> None:
    required = {"reviewer_id", "review_item_id", "preferred_output", "reviewer_confidence"}
    for alias in ("A", "B", "C"):
        required.update(f"{alias}_{column}" for column in REVIEW_SCORE_COLUMNS)
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ThemeBenchmarkError(f"Phase 3 review import missing required columns: {missing}")
    if frame[["reviewer_id", "review_item_id"]].duplicated().any():
        raise ThemeBenchmarkError("Duplicate Phase 3 review submission for reviewer/item.")
    provider_tokens = ("keyword_baseline", "gemini", "llm7", "gpt4o", "gpt-4o", "mock")
    if any(token in frame.astype(str).to_string(index=False).lower() for token in provider_tokens):
        raise ThemeBenchmarkError("Phase 3 review import contains provider identity text.")
    for _, row in frame.iterrows():
        if not str(row["reviewer_id"]).strip():
            raise ThemeBenchmarkError("Phase 3 review import has missing reviewer_id.")
        if str(row["review_item_id"]) not in known_items:
            raise ThemeBenchmarkError(f"Unknown Phase 3 review item: {row['review_item_id']}")
        if str(row["preferred_output"]) not in PREFERENCE_VALUES:
            raise ThemeBenchmarkError("Invalid preferred_output value.")
        if str(row["reviewer_confidence"]) not in CONFIDENCE_VALUES:
            raise ThemeBenchmarkError("Invalid reviewer_confidence value.")
    for alias in ("A", "B", "C"):
        for column in REVIEW_SCORE_COLUMNS:
            values = pd.to_numeric(frame[f"{alias}_{column}"], errors="coerce")
            if values.isna().any():
                raise ThemeBenchmarkError("Partial Phase 3 reviews are not accepted by this importer.")
            if ((values < 1) | (values > 5)).any():
                raise ThemeBenchmarkError(f"Phase 3 score column {alias}_{column} must contain values from 1 to 5.")


def _review_summary(unblinded: pd.DataFrame, raw: pd.DataFrame) -> dict[str, Any]:
    provider_summary = {}
    for provider, group in unblinded.groupby("provider_id"):
        provider_summary[provider] = {
            column: {"mean": float(group[column].mean()), "median": float(group[column].median())}
            for column in REVIEW_SCORE_COLUMNS
        }
    reviewers = sorted(raw["reviewer_id"].astype(str).unique())
    preferred = Counter(unblinded[unblinded["preferred"]]["provider_id"])
    return {
        "schema_version": 1,
        "reviewer_count": len(reviewers),
        "reviewers": reviewers,
        "provider_summary": provider_summary,
        "preferred_provider_counts": dict(preferred),
        "inter_rater_reliability": "unavailable_single_reviewer" if len(reviewers) == 1 else "not_implemented_for_phase3_closeout",
        "bootstrap_95ci_method": "deterministic placeholder; compute after real complete reviews",
    }


def _cache_record_for(root: Path, provider: str, request, repetition_index: int) -> dict[str, Any] | None:
    request_id = stable_hash(request.to_dict())
    matches = []
    for record in read_jsonl(root / "cache" / f"{provider}.jsonl"):
        if record.get("request_id") != request_id:
            continue
        params = record.get("parameters", {})
        if repetition_index == 0 and "repetition_index" not in params:
            matches.append(record)
        elif params.get("repetition_index") == repetition_index:
            matches.append(record)
    return matches[-1] if matches else None


def _stability_metrics(reps: Mapping[int, Mapping[str, Any]]) -> dict[str, Any]:
    values = [json.dumps(row.get("normalized_theme_json", {}), sort_keys=True) for row in reps.values()]
    complete = set(reps) == {0, 1, 2}
    exact = 1.0 if complete and len(set(values)) == 1 else 0.0 if complete else None
    keyword_sets = [_keywords(row.get("normalized_theme_json", {})) for row in reps.values()]
    jaccards = []
    for left, right in itertools.combinations(keyword_sets, 2):
        jaccards.append(len(left & right) / len(left | right) if left or right else 1.0)
    counts = [len((row.get("normalized_theme_json", {}) or {}).get("themes", [])) for row in reps.values()]
    return {
        "complete_repetitions": complete,
        "exact_json_agreement": exact,
        "keyword_jaccard_agreement": _mean(jaccards),
        "theme_count_variance": _variance(counts),
    }


def _keywords(value: Mapping[str, Any]) -> set[str]:
    keywords = set()
    for theme in (value or {}).get("themes", []):
        keywords.update(str(keyword) for keyword in theme.get("keywords", []))
    return keywords


def _member_bin(row: Mapping[str, Any]) -> str:
    count = int(row.get("members_count", 0) or 0)
    return "small" if count < 10 else "medium" if count < 50 else "large"


def _keyword_bin(row: Mapping[str, Any]) -> str:
    count = len(row.get("general_keywords", []) or [])
    return "low" if count < 10 else "medium" if count < 25 else "high"


def _mean(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def _variance(values):
    if not values:
        return None
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def _contains_provider_leakage(path: Path) -> bool:
    text = path.read_text(encoding="utf-8").lower()
    return any(token in text for token in ("keyword_baseline", "gemini", "llm7", "gpt4o", "gpt-4o", "mock"))
