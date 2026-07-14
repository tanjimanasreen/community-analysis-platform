from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from src.themes.benchmark.contracts import (
    ORIGINAL_KEYWORD_FIELDS,
    ThemeBenchmarkError,
    read_json,
    read_jsonl,
    stable_hash,
    write_json,
)
from src.themes.benchmark.dataset import benchmark_root


VALID_SPLITS = ("development", "pilot", "heldout")
EXPECTED_PHASE1_DATASET_HASH = "6b553bc95a601620d752b7763a5f7caea82b50ac2329279da4f22b17e9278951"
EXPECTED_PHASE1_SPLIT_HASH = "5065183328ace9fddd39df8d588e8f065c1b99d34373f905ec1f97d857424200"


def validate_frozen_dataset(
    output_base_path: str | Path,
    run_id: str,
    *,
    expected_dataset_hash: str | None = None,
    expected_split_hash: str | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    root = benchmark_root(output_base_path, run_id)
    manifest = read_json(root / "manifest.json")
    examples = read_jsonl(root / "dataset.jsonl")
    requests = read_jsonl(root / "requests.jsonl")

    dataset_hash = stable_hash(examples)
    split_hash = _split_hash(examples)
    expected_dataset_hash = expected_dataset_hash or manifest.get("dataset_hash")
    expected_split_hash = expected_split_hash or manifest.get("split_hash")
    if expected_dataset_hash and dataset_hash != expected_dataset_hash:
        raise ThemeBenchmarkError(
            f"Frozen dataset hash mismatch: expected {expected_dataset_hash}, got {dataset_hash}."
        )
    if expected_split_hash and split_hash != expected_split_hash:
        raise ThemeBenchmarkError(
            f"Frozen split hash mismatch: expected {expected_split_hash}, got {split_hash}."
        )
    if manifest.get("dataset_hash") != dataset_hash:
        raise ThemeBenchmarkError("Frozen dataset hash does not match manifest.")
    if manifest.get("split_hash") != split_hash:
        raise ThemeBenchmarkError("Frozen split hash does not match manifest.")

    example_ids = [str(row.get("example_id")) for row in examples]
    duplicates = sorted(item for item, count in Counter(example_ids).items() if count > 1)
    if duplicates:
        raise ThemeBenchmarkError(f"Frozen dataset contains duplicate example IDs: {duplicates[:5]}")

    split_by_example: dict[str, str] = {}
    for row in examples:
        example_id = str(row.get("example_id"))
        split = str(row.get("split"))
        if split not in VALID_SPLITS:
            raise ThemeBenchmarkError(f"Example {example_id} has unsupported split {split!r}.")
        existing = split_by_example.get(example_id)
        if existing is not None and existing != split:
            raise ThemeBenchmarkError(f"Example {example_id} appears in multiple splits.")
        split_by_example[example_id] = split
        for field in ORIGINAL_KEYWORD_FIELDS:
            if field not in row:
                raise ThemeBenchmarkError(f"Example {example_id} is missing original keyword field {field}.")
        if not row.get("general_keywords") or not row.get("general_keyword_text"):
            raise ThemeBenchmarkError(f"Example {example_id} is missing production-equivalent general keywords.")
        _reject_nonstandard_json(row, f"dataset example {example_id}")

    split_counts = Counter(split_by_example.values())
    expected_counts = {"development": 20, "pilot": 30, "heldout": 50}
    if len(examples) == 100:
        for split, expected_count in expected_counts.items():
            actual = split_counts.get(split, 0)
            if actual != expected_count:
                raise ThemeBenchmarkError(
                    f"Frozen split {split!r} expected {expected_count} examples, found {actual}."
                )
    manifest_counts = dict(manifest.get("split_counts", {}))
    actual_counts = {split: split_counts.get(split, 0) for split in set(manifest_counts) | set(split_counts)}
    if manifest_counts != actual_counts:
        raise ThemeBenchmarkError("Frozen split counts do not match manifest.")

    general_request_ids = {
        str(row.get("example_id"))
        for row in requests
        if row.get("keyword_mode") == "general"
    }
    missing_general = sorted(set(example_ids).difference(general_request_ids))
    if missing_general:
        raise ThemeBenchmarkError(
            f"Frozen requests are missing general-mode requests for examples: {missing_general[:5]}"
        )
    for request in requests:
        _reject_nonstandard_json(request, f"request {request.get('example_id')}")

    source_report = _validate_source_artifacts(manifest, examples)
    report = _distribution_report(
        examples,
        manifest=manifest,
        dataset_hash=dataset_hash,
        split_hash=split_hash,
        source_report=source_report,
    )
    if write_report:
        write_json(root / "reports" / "split_distribution.json", report)
    return report


def filter_examples_by_split(example_ids: list[str], dataset_rows: list[Mapping[str, Any]], split: str | None) -> set[str] | None:
    if split is None:
        return None
    if split not in VALID_SPLITS:
        raise ThemeBenchmarkError(f"Unsupported benchmark split {split!r}; expected one of {VALID_SPLITS}.")
    split_ids = {str(row["example_id"]) for row in dataset_rows if row.get("split") == split}
    known_ids = set(example_ids)
    missing = sorted(split_ids.difference(known_ids))
    if missing:
        raise ThemeBenchmarkError(f"Split {split!r} references examples missing from requests: {missing[:5]}")
    return split_ids


def _validate_source_artifacts(manifest: Mapping[str, Any], examples: list[Mapping[str, Any]]) -> dict[str, Any]:
    source_hashes = dict(manifest.get("source_artifact_hashes", {}))
    for path_text, expected_hash in source_hashes.items():
        path = Path(path_text)
        if not path.exists():
            raise ThemeBenchmarkError(f"Frozen source artifact is missing: {path}")
        actual_hash = _sha256_file(path)
        if actual_hash != expected_hash:
            raise ThemeBenchmarkError(
                f"Frozen source artifact hash mismatch for {path}: expected {expected_hash}, got {actual_hash}."
            )

    source_rows: dict[str, int] = {}
    for path_text in source_hashes:
        source_rows[path_text] = _csv_data_row_count(Path(path_text))

    for row in examples:
        example_id = str(row.get("example_id"))
        root = row.get("source_artifact_root")
        filename = row.get("source_artifact_file")
        if not root or not filename:
            raise ThemeBenchmarkError(f"Example {example_id} is missing source artifact metadata.")
        source_path = str(Path(str(root)) / str(filename))
        if source_path not in source_rows:
            raise ThemeBenchmarkError(f"Example {example_id} references unknown source artifact {source_path}.")
        index = int(row.get("source_row_index", -1))
        if index < 0 or index >= source_rows[source_path]:
            raise ThemeBenchmarkError(f"Example {example_id} references invalid source row {index}.")

    inventory_path = Path(str(manifest.get("output_root", ""))) / "inventory.json"
    manifest_reports = []
    if inventory_path.exists():
        inventory = read_json(inventory_path)
        for source in inventory.get("sources", []):
            manifest_path = Path(str(source.get("manifest_path", "")))
            expected = source.get("manifest_hash")
            if expected and manifest_path.exists():
                actual = _sha256_file(manifest_path)
                if actual != expected:
                    raise ThemeBenchmarkError(
                        f"Theme-input manifest hash mismatch for {manifest_path}: expected {expected}, got {actual}."
                    )
                manifest_reports.append({"path": str(manifest_path), "sha256": actual})
    return {
        "source_artifacts": source_hashes,
        "source_row_counts": source_rows,
        "source_manifests": manifest_reports,
    }


def _distribution_report(
    examples: list[Mapping[str, Any]],
    *,
    manifest: Mapping[str, Any],
    dataset_hash: str,
    split_hash: str,
    source_report: Mapping[str, Any],
) -> dict[str, Any]:
    by_split = {split: [row for row in examples if row.get("split") == split] for split in VALID_SPLITS}
    dimensions: dict[str, dict[str, dict[str, int]]] = {
        "month": {},
        "community_size_bin": {},
        "keyword_richness_bin": {},
        "absolute_community_coverage": {},
        "weighted_community_coverage": {},
        "source_artifact_root": {},
    }
    for split, rows in by_split.items():
        dimensions["month"][split] = dict(Counter(str(row.get("month")) for row in rows))
        dimensions["community_size_bin"][split] = dict(Counter(_member_bin(row) for row in rows))
        dimensions["keyword_richness_bin"][split] = dict(Counter(_keyword_bin(row) for row in rows))
        dimensions["absolute_community_coverage"][split] = dict(
            Counter("present" if row.get("absolute_community") not in (None, "") else "missing" for row in rows)
        )
        dimensions["weighted_community_coverage"][split] = dict(
            Counter("present" if row.get("weighted_community") not in (None, "") else "missing" for row in rows)
        )
        dimensions["source_artifact_root"][split] = dict(Counter(str(row.get("source_artifact_root")) for row in rows))

    data_types = sorted({str(row.get("data_type")) for row in examples})
    content_types = sorted({str(row.get("content_type")) for row in examples})
    years = sorted({str(row.get("year")) for row in examples})
    rejected_by_source = {}
    inventory_path = Path(str(manifest.get("output_root", ""))) / "inventory.json"
    if inventory_path.exists():
        inventory = read_json(inventory_path)
        for source in inventory.get("sources", []):
            rejected_by_source[str(source.get("input_dir"))] = int(source.get("rejected_row_count", 0) or 0)

    return {
        "schema_version": 1,
        "dataset_hash": dataset_hash,
        "split_hash": split_hash,
        "example_count": len(examples),
        "split_counts": {split: len(rows) for split, rows in by_split.items()},
        "dimensions": dimensions,
        "rejected_row_counts": rejected_by_source,
        "source_report": source_report,
        "limited_to_single_data_type": len(data_types) == 1,
        "limited_to_single_content_type": len(content_types) == 1,
        "limited_to_single_year": len(years) == 1,
        "data_types": data_types,
        "content_types": content_types,
        "years": years,
    }


def _split_hash(examples: list[Mapping[str, Any]]) -> str:
    return stable_hash(
        {
            str(row["example_id"]): row["split"]
            for row in sorted(examples, key=lambda item: str(item["example_id"]))
        }
    )


def _reject_nonstandard_json(value: Any, label: str) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except ValueError as exc:
        raise ThemeBenchmarkError(f"Non-standard JSON value found in {label}: {exc}") from exc
    if isinstance(value, float) and not math.isfinite(value):
        raise ThemeBenchmarkError(f"Non-standard JSON float found in {label}.")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_nonstandard_json(item, f"{label}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_nonstandard_json(item, f"{label}[{index}]")


def _member_bin(row: Mapping[str, Any]) -> str:
    count = int(row.get("members_count", 0) or 0)
    if count < 10:
        return "small"
    if count < 50:
        return "medium"
    return "large"


def _keyword_bin(row: Mapping[str, Any]) -> str:
    count = len(row.get("general_keywords", []) or [])
    if count < 10:
        return "low"
    if count < 25:
        return "medium"
    return "high"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_data_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)
