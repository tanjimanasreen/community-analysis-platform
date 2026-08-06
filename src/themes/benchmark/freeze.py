from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.themes.benchmark.contracts import (
    BENCHMARK_SCHEMA_VERSION,
    DATASET_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    THEME_OUTPUT_JSON_SCHEMA,
    ThemeBenchmarkError,
    read_json,
    stable_hash,
    write_json,
    write_jsonl,
)
from src.themes.benchmark.dataset import (
    benchmark_root,
    build_gpt4o_reference_metadata,
    build_requests,
    examples_from_theme_inputs,
)
from src.themes.theme_inputs import (
    ThemeInputError,
    build_theme_input_dir,
    load_theme_inputs,
)

INVENTORY_RUN_ID = "artifact-inventory"
FROZEN_DATASET_SCHEMA_VERSION = 1
DEFAULT_FREEZE_SEED = 16016


def inventory_artifacts(
    config: Mapping[str, Any],
    *,
    source_configs: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    configs = list(source_configs or [config])
    sources = _load_unique_sources(configs)
    inventory = _build_inventory(config, sources)
    root = benchmark_root(
        str(config.get("output_base_path", "results/")), INVENTORY_RUN_ID
    )
    write_json(root / "inventory.json", inventory)
    return {"output_dir": root, "inventory": inventory}


def freeze_dataset(
    config: Mapping[str, Any],
    *,
    run_id: str,
    source_configs: Sequence[Mapping[str, Any]] | None = None,
    target_examples: int = 100,
    min_examples: int = 1,
    max_examples: int = 120,
    seed: int = DEFAULT_FREEZE_SEED,
    development_count: int = 0,
    pilot_count: int = 1,
    overwrite: bool = False,
) -> dict[str, Any]:
    if min_examples < 1:
        raise ThemeBenchmarkError("min_examples must be at least 1.")
    if target_examples < min_examples:
        raise ThemeBenchmarkError(
            "target_examples must be greater than or equal to min_examples."
        )
    if max_examples < target_examples:
        raise ThemeBenchmarkError(
            "max_examples must be greater than or equal to target_examples."
        )

    output_dir = benchmark_root(str(config.get("output_base_path", "results/")), run_id)
    configs = list(source_configs or [config])
    sources = _load_unique_sources(configs)
    inventory = _build_inventory(config, sources)
    all_examples = _examples_from_sources(sources)
    available = len(all_examples)
    if available < min_examples:
        raise ThemeBenchmarkError(
            f"Frozen benchmark requires at least {min_examples} valid examples, found {available}."
        )

    selected_count = min(target_examples, max_examples, available)
    selected = _select_stratified(all_examples, selected_count, seed)
    split_assignments = _assign_splits(
        selected,
        seed=seed,
        development_count=development_count,
        pilot_count=pilot_count,
    )
    frozen_examples: list[dict[str, Any]] = []
    for example in sorted(selected, key=_dataset_order_key):
        row = dict(example)
        row["frozen_dataset_schema_version"] = FROZEN_DATASET_SCHEMA_VERSION
        row["split"] = split_assignments[str(row["example_id"])]
        frozen_examples.append(row)

    dataset_hash = stable_hash(frozen_examples)
    split_hash = stable_hash(
        {
            str(row["example_id"]): row["split"]
            for row in sorted(frozen_examples, key=lambda item: str(item["example_id"]))
        }
    )
    requests = build_requests(frozen_examples)
    requests_hash = stable_hash([request.to_dict() for request in requests])
    prompt_reference = build_gpt4o_reference_metadata()
    output_schema_hash = stable_hash(THEME_OUTPUT_JSON_SCHEMA)

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "benchmark_schema_version": BENCHMARK_SCHEMA_VERSION,
        "frozen_dataset_schema_version": FROZEN_DATASET_SCHEMA_VERSION,
        "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "request_schema_version": REQUEST_SCHEMA_VERSION,
        "run_id": run_id,
        "freeze_seed": seed,
        "target_examples": target_examples,
        "min_examples": min_examples,
        "max_examples": max_examples,
        "available_valid_examples": available,
        "example_count": len(frozen_examples),
        "request_count": len(requests),
        "split_counts": _split_counts(frozen_examples),
        "dataset_hash": dataset_hash,
        "split_hash": split_hash,
        "requests_hash": requests_hash,
        "prompt_hash": prompt_reference["prompt_hash"],
        "output_schema_hash": output_schema_hash,
        "providers": [],
        "output_root": str(output_dir),
        "source_inventory_hash": inventory["inventory_hash"],
        "source_artifact_hashes": inventory["source_artifact_hashes"],
        "artifacts": {
            "dataset": "dataset.jsonl",
            "requests": "requests.jsonl",
            "inventory": "inventory.json",
            "gpt4o_config": "reference/gpt4o_config.json",
        },
        "locked_splits": ["heldout"],
        "notes": (
            "Frozen benchmark dataset built from saved theme-input artifacts only. "
            "No provider calls, raw source recomputation, or thesis output changes were performed."
        ),
    }
    _guard_existing_frozen_run(output_dir, manifest, overwrite=overwrite)
    write_jsonl(output_dir / "dataset.jsonl", frozen_examples)
    write_jsonl(
        output_dir / "requests.jsonl", [request.to_dict() for request in requests]
    )
    write_json(output_dir / "reference" / "gpt4o_config.json", prompt_reference)
    write_json(output_dir / "inventory.json", inventory)
    write_json(output_dir / "manifest.json", manifest)
    return {
        "output_dir": output_dir,
        "manifest": manifest,
        "inventory": inventory,
        "examples": frozen_examples,
        "requests": requests,
    }


def _load_unique_sources(configs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen_roots: set[Path] = set()
    for index, config in enumerate(configs):
        params = _params(config)
        input_dir = build_theme_input_dir(
            output_base_path=params["output_base_path"],
            data_type=params["data_type"],
            content_type=params["content_type"],
            year=params["year"],
        )
        try:
            bundle = load_theme_inputs(
                output_base_path=params["output_base_path"],
                data_type=params["data_type"],
                content_type=params["content_type"],
                year=params["year"],
                require_manifest=True,
            )
        except ThemeInputError as exc:
            raise ThemeBenchmarkError(
                f"Saved theme-input artifacts are required for benchmark inventory: {exc}"
            ) from exc
        root = bundle.input_dir.resolve()
        if root in seen_roots:
            continue
        seen_roots.add(root)
        sources.append(
            {
                "source_index": index,
                "params": params,
                "input_dir": input_dir,
                "bundle": bundle,
            }
        )
    if not sources:
        raise ThemeBenchmarkError("No saved theme-input artifact roots were found.")
    return sources


def _guard_existing_frozen_run(
    output_dir: Path,
    new_manifest: Mapping[str, Any],
    *,
    overwrite: bool,
) -> None:
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        return
    existing = read_json(manifest_path)
    compared_fields = (
        "dataset_hash",
        "split_hash",
        "requests_hash",
        "source_inventory_hash",
        "example_count",
        "request_count",
        "split_counts",
        "freeze_seed",
        "target_examples",
        "min_examples",
        "max_examples",
    )
    differences = [
        field
        for field in compared_fields
        if existing.get(field) != new_manifest.get(field)
    ]
    if differences and not overwrite:
        raise ThemeBenchmarkError(
            "Refusing to overwrite existing frozen benchmark run with different "
            f"manifest fields {differences}. Re-run with --overwrite-existing-frozen-run "
            "only after intentionally accepting the replacement."
        )


def _build_inventory(
    base_config: Mapping[str, Any],
    sources: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    source_rows: list[dict[str, Any]] = []
    source_artifact_hashes: dict[str, str] = {}
    total_rows = 0
    total_valid = 0
    for source in sources:
        params = source["params"]
        bundle = source["bundle"]
        manifest = bundle.manifest or {}
        root = bundle.input_dir
        manifest_path = root / "manifest.json"
        manifest_hash = _sha256_file(manifest_path) if manifest_path.exists() else None
        months: list[dict[str, Any]] = []
        for month in sorted(bundle.monthly_data.keys(), key=_month_sort_key):
            frame = bundle.monthly_data[month]
            row_count = int(len(frame))
            examples = examples_from_theme_inputs(
                {month: frame},
                data_type=params["data_type"],
                content_type=params["content_type"],
                year=params["year"],
            )
            valid_count = len(examples)
            filename = str(
                manifest.get("filenames", {}).get(
                    str(month), f"{month}_{params['year']}.csv"
                )
            )
            path = root / filename
            file_hash = _sha256_file(path)
            source_artifact_hashes[str(path)] = file_hash
            months.append(
                {
                    "month": str(month),
                    "filename": filename,
                    "path": str(path),
                    "row_count": row_count,
                    "valid_example_count": valid_count,
                    "rejected_row_count": row_count - valid_count,
                    "sha256": file_hash,
                }
            )
            total_rows += row_count
            total_valid += valid_count
        source_rows.append(
            {
                "schema_version": 1,
                "input_dir": str(root),
                "data_type": params["data_type"],
                "content_type": params["content_type"],
                "year": params["year"],
                "manifest_path": str(manifest_path),
                "manifest_hash": manifest_hash,
                "theme_input_schema_version": manifest.get("schema_version"),
                "months": months,
                "row_count": sum(month["row_count"] for month in months),
                "valid_example_count": sum(
                    month["valid_example_count"] for month in months
                ),
                "rejected_row_count": sum(
                    month["rejected_row_count"] for month in months
                ),
            }
        )

    inventory = {
        "schema_version": 1,
        "benchmark_schema_version": BENCHMARK_SCHEMA_VERSION,
        "output_base_path": str(base_config.get("output_base_path", "results/")),
        "source_count": len(source_rows),
        "row_count": total_rows,
        "valid_example_count": total_valid,
        "rejected_row_count": total_rows - total_valid,
        "sources": source_rows,
        "source_artifact_hashes": source_artifact_hashes,
    }
    inventory["inventory_hash"] = stable_hash(
        {key: value for key, value in inventory.items() if key != "inventory_hash"}
    )
    return inventory


def _examples_from_sources(sources: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in sources:
        params = source["params"]
        bundle = source["bundle"]
        manifest = bundle.manifest or {}
        examples = examples_from_theme_inputs(
            bundle.monthly_data,
            data_type=params["data_type"],
            content_type=params["content_type"],
            year=params["year"],
        )
        for example in examples:
            key = stable_hash(
                {
                    "root": str(bundle.input_dir.resolve()),
                    "example_id": example["example_id"],
                    "input_hash": example["input_hash"],
                }
            )
            if key in seen:
                continue
            seen.add(key)
            row = dict(example)
            filename = manifest.get("filenames", {}).get(str(row["month"]))
            row["source_artifact_root"] = str(bundle.input_dir)
            row["source_artifact_file"] = filename
            row["source_artifact_hash"] = (
                _sha256_file(bundle.input_dir / filename) if filename else None
            )
            rows.append(row)
    return rows


def _select_stratified(
    examples: list[dict[str, Any]], target_count: int, seed: int
) -> list[dict[str, Any]]:
    strata: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for example in examples:
        strata.setdefault(_stratum_key(example), []).append(example)
    for key, values in strata.items():
        values.sort(key=lambda item: _stable_rank(item, seed, f"stratum:{key}"))

    selected: list[dict[str, Any]] = []
    stratum_keys = sorted(strata.keys(), key=lambda key: str(key))
    while len(selected) < target_count:
        progressed = False
        for key in stratum_keys:
            values = strata[key]
            if values:
                selected.append(values.pop(0))
                progressed = True
                if len(selected) >= target_count:
                    break
        if not progressed:
            break
    return selected


def _assign_splits(
    examples: list[dict[str, Any]],
    *,
    seed: int,
    development_count: int,
    pilot_count: int,
) -> dict[str, str]:
    ordered = sorted(examples, key=lambda item: _stable_rank(item, seed, "split"))
    development_cutoff = min(development_count, len(ordered))
    pilot_cutoff = min(development_cutoff + pilot_count, len(ordered))
    assignments: dict[str, str] = {}
    for index, example in enumerate(ordered):
        if index < development_cutoff:
            split = "development"
        elif index < pilot_cutoff:
            split = "pilot"
        else:
            split = "heldout"
        assignments[str(example["example_id"])] = split
    return assignments


def _split_counts(examples: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = {"development": 0, "pilot": 0, "heldout": 0}
    for row in examples:
        split = str(row.get("split"))
        counts[split] = counts.get(split, 0) + 1
    return counts


def _stratum_key(example: Mapping[str, Any]) -> tuple[Any, ...]:
    richness = len(example.get("general_keywords", []))
    if richness < 10:
        richness_bin = "low"
    elif richness < 25:
        richness_bin = "medium"
    else:
        richness_bin = "high"
    members_count = int(example.get("members_count", 0) or 0)
    if members_count < 10:
        member_bin = "small"
    elif members_count < 50:
        member_bin = "medium"
    else:
        member_bin = "large"
    has_absolute = bool(example.get("absolute_keywords"))
    has_weighted = bool(example.get("weighted_keywords"))
    return (
        str(example.get("month")),
        member_bin,
        richness_bin,
        has_absolute,
        has_weighted,
    )


def _stable_rank(example: Mapping[str, Any], seed: int, namespace: str) -> str:
    return stable_hash(
        {
            "seed": seed,
            "namespace": namespace,
            "example_id": example.get("example_id"),
            "input_hash": example.get("input_hash"),
        }
    )


def _dataset_order_key(example: Mapping[str, Any]) -> tuple[int, int, str]:
    return (
        _month_sort_key(str(example.get("month", ""))),
        int(example.get("source_row_index", 0) or 0),
        str(example.get("example_id", "")),
    )


def _params(config: Mapping[str, Any]) -> dict[str, str]:
    return {
        "output_base_path": str(config.get("output_base_path", "results/")),
        "data_type": str(config.get("data_type", "twitter")),
        "content_type": str(config.get("content_type", "reply")),
        "year": str(config.get("year", "2017")),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _month_sort_key(month: str) -> int:
    text = str(month).lower()
    if text.isdigit():
        return int(text)
    order = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    return order.get(text, 99)
