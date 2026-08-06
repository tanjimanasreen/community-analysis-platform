from __future__ import annotations

import ast
import hashlib
import json
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from src.config.defaults import DEFAULT_CONFIG

SCHEMA_VERSION = 1
MANIFEST_FILE = "manifest.json"

REQUIRED_COLUMNS = [
    "members",
    "absolute_community",
    "weighted_community",
    "absolute_unigram_keywords",
    "absolute_bigram_keywords",
    "weighted_unigram_keywords",
    "weighted_bigram_keywords",
]
LIST_COLUMNS = {
    "members",
    "absolute_unigram_keywords",
    "absolute_bigram_keywords",
    "weighted_unigram_keywords",
    "weighted_bigram_keywords",
}


class ThemeInputError(ValueError):
    """Raised when saved theme-input artifacts are missing or invalid."""


_MANIFEST_LOCK = threading.Lock()


@dataclass(frozen=True)
class ThemeInputBundle:
    monthly_data: dict[str, pd.DataFrame]
    manifest: dict[str, Any] | None
    input_dir: Path


def build_theme_input_dir(
    config_or_params: Mapping[str, Any] | None = None,
    *,
    output_base_path: str | None = None,
    data_type: str | None = None,
    content_type: str | None = None,
    year: str | int | None = None,
) -> Path:
    params = dict(config_or_params or {})
    base = (
        output_base_path
        or params.get("output_base_path")
        or params.get("output_dir")
        or "results/"
    )
    data = data_type or params.get("data_type", "twitter")
    content = content_type or params.get("content_type", "reply")
    year_value = str(year if year is not None else params.get("year", "2017"))
    return (
        Path(base)
        / str(data)
        / "_intermediate"
        / "theme_inputs"
        / str(content)
        / year_value
    )


def save_theme_inputs(
    *,
    matched_lda_csv: str | Path,
    output_base_path: str,
    data_type: str,
    content_type: str,
    month: str | int,
    year: str | int,
) -> Path:
    source_path = Path(matched_lda_csv)
    if not source_path.exists():
        raise ThemeInputError(f"Matched LDA CSV not found: {source_path}")

    if source_path.name.endswith(".parquet"):
        frame = pd.read_parquet(source_path)
    else:
        frame = pd.read_csv(source_path)
    validate_theme_dataframe(frame, source_path.name)

    output_dir = build_theme_input_dir(
        output_base_path=output_base_path,
        data_type=data_type,
        content_type=content_type,
        year=year,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{month}_{year}.parquet"
    destination = output_dir / filename
    frame.to_parquet(destination, index=False)

    manifest_path = output_dir / MANIFEST_FILE

    with _MANIFEST_LOCK:
        existing_manifest = _read_manifest_if_present(manifest_path)
        filenames = dict(existing_manifest.get("filenames", {}))
        hashes = dict(existing_manifest.get("hashes", {}))
        filenames[str(month)] = filename
        hashes[filename] = _sha256_file(destination)
        months = sorted(filenames.keys(), key=_month_sort_key)

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "data_type": str(data_type),
            "content_type": str(content_type),
            "year": str(year),
            "months": months,
            "filenames": {month_key: filenames[month_key] for month_key in months},
            "hashes": hashes,
            "created_by": "run-topics",
            "lda": {
                "num_topics": DEFAULT_CONFIG.lda.num_topics,
                "random_state": DEFAULT_CONFIG.lda.random_state,
                "passes": DEFAULT_CONFIG.lda.passes,
                "iterations": DEFAULT_CONFIG.lda.iterations,
                "chunksize": DEFAULT_CONFIG.lda.chunksize,
            },
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    return output_dir


def load_theme_inputs(
    config_or_params: Mapping[str, Any] | None = None,
    *,
    input_dir: str | Path | None = None,
    output_base_path: str | None = None,
    data_type: str | None = None,
    content_type: str | None = None,
    year: str | int | None = None,
    require_manifest: bool = True,
) -> ThemeInputBundle:
    base = (
        Path(input_dir)
        if input_dir is not None
        else build_theme_input_dir(
            config_or_params,
            output_base_path=output_base_path,
            data_type=data_type,
            content_type=content_type,
            year=year,
        )
    )
    expected = _expected_metadata(
        config_or_params, output_base_path, data_type, content_type, year
    )
    manifest_path = base / MANIFEST_FILE

    if not manifest_path.exists():
        if require_manifest:
            raise ThemeInputError(
                f"Theme input manifest not found at {manifest_path}. "
                "Run run-topics first; for samples run make run-topic-sample first, "
                "or use make run-pipeline-sample."
            )
        monthly_data = _load_csvs_without_manifest(base, expected["year"])
        return ThemeInputBundle(
            monthly_data=monthly_data, manifest=None, input_dir=base
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(manifest, expected, manifest_path)
    monthly_data: dict[str, pd.DataFrame] = {}
    for month in manifest.get("months", []):
        filename = manifest["filenames"][str(month)]
        path = base / filename
        if not path.exists():
            raise ThemeInputError(
                f"Theme input file listed in manifest is missing: {path}"
            )
        expected_hash = manifest.get("hashes", {}).get(filename)
        actual_hash = _sha256_file(path)
        if expected_hash != actual_hash:
            raise ThemeInputError(
                f"Theme input hash mismatch for {path}: expected {expected_hash}, got {actual_hash}"
            )
        frame = pd.read_parquet(path)
        validate_theme_dataframe(frame, filename)
        monthly_data[str(month)] = _parse_list_columns(frame)
    return ThemeInputBundle(
        monthly_data=monthly_data, manifest=manifest, input_dir=base
    )


def validate_theme_inputs(bundle: ThemeInputBundle) -> None:
    for month, frame in bundle.monthly_data.items():
        validate_theme_dataframe(frame, f"{month} theme input")
        for column in LIST_COLUMNS:
            invalid = [
                value for value in frame[column].tolist() if not isinstance(value, list)
            ]
            if invalid:
                raise ThemeInputError(
                    f"{month} column {column!r} must contain list values."
                )


def validate_theme_dataframe(frame: pd.DataFrame, name: str) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ThemeInputError(f"{name} is missing required columns: {missing}")


def _load_csvs_without_manifest(base: Path, year: str) -> dict[str, pd.DataFrame]:
    if not base.exists():
        return {}
    monthly_data: dict[str, pd.DataFrame] = {}
    for path in sorted(
        base.glob(f"*_{year}.parquet"),
        key=lambda item: _month_sort_key(_month_from_filename(item, year)),
    ):
        frame = pd.read_parquet(path)
        validate_theme_dataframe(frame, path.name)
        monthly_data[_month_from_filename(path, year)] = _parse_list_columns(frame)
    return monthly_data


def _parse_list_columns(frame: pd.DataFrame) -> pd.DataFrame:
    parsed = frame.copy()
    for column in LIST_COLUMNS:
        parsed[column] = parsed[column].apply(_parse_list)
    return parsed


def _parse_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if hasattr(value, "tolist"):
        return value.tolist()

    try:
        if pd.isna(value):
            return []
    except ValueError:
        pass

    if isinstance(value, str) and value == "":
        return []
    if isinstance(value, str):
        text = value.strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(text)
            except (SyntaxError, ValueError):
                parsed = [item.strip() for item in text.split(",") if item.strip()]
        return parsed if isinstance(parsed, list) else [parsed]
    return [value]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest_if_present(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _expected_metadata(
    config_or_params: Mapping[str, Any] | None,
    output_base_path: str | None,
    data_type: str | None,
    content_type: str | None,
    year: str | int | None,
) -> dict[str, str]:
    params = dict(config_or_params or {})
    return {
        "data_type": str(data_type or params.get("data_type", "twitter")),
        "content_type": str(content_type or params.get("content_type", "reply")),
        "year": str(year if year is not None else params.get("year", "2017")),
    }


def _validate_manifest(
    manifest: Mapping[str, Any], expected: Mapping[str, str], path: Path
) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ThemeInputError(
            f"{path} has unsupported schema_version={manifest.get('schema_version')!r}; "
            f"expected {SCHEMA_VERSION}."
        )
    mismatches = {
        key: {"expected": value, "actual": str(manifest.get(key))}
        for key, value in expected.items()
        if str(manifest.get(key)) != value
    }
    if mismatches:
        raise ThemeInputError(
            f"{path} metadata does not match requested run: {mismatches}"
        )


def _month_from_filename(path: Path, year: str) -> str:
    suffix = f"_{year}"
    stem = path.stem
    return stem[: -len(suffix)] if stem.endswith(suffix) else stem


def _month_sort_key(month: str) -> int:
    text = str(month).lower()
    if text.isdigit():
        return int(text)
    month_order = {
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
    return month_order.get(text, 99)
