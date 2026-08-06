from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from src.themes.benchmark.contracts import (
    REVIEW_SCHEMA_VERSION,
    ThemeBenchmarkError,
    read_jsonl,
    stable_hash,
)
from src.themes.benchmark.dataset import benchmark_root

REVIEW_SCORE_COLUMNS = [
    "fidelity",
    "coherence",
    "specificity",
    "non_redundancy",
    "usefulness",
    "overall_preference",
]


def export_blinded_review(output_base_path: str | Path, run_id: str) -> Path:
    root = benchmark_root(output_base_path, run_id)
    generation_files = sorted((root / "generations").rglob("*.jsonl"))
    rows: list[dict[str, Any]] = []
    provider_labels: dict[str, str] = {}
    for index, path in enumerate(generation_files, start=1):
        provider_id = path.stem
        provider_labels[provider_id] = f"provider_{index:02d}"
        for result in read_jsonl(path):
            rows.append(
                {
                    "schema_version": REVIEW_SCHEMA_VERSION,
                    "review_id": stable_hash(
                        {
                            "run_id": run_id,
                            "provider_label": provider_labels[provider_id],
                            "request_id": result.get("request_id"),
                        }
                    )[:16],
                    "provider_label": provider_labels[provider_id],
                    "example_id": result.get("example_id"),
                    "keyword_mode": result.get("keyword_mode"),
                    "request_keywords": ", ".join(result.get("request_keywords", [])),
                    "theme_json": result.get("normalized_theme_json"),
                    **{column: "" for column in REVIEW_SCORE_COLUMNS},
                }
            )
    out_path = root / "review" / "blinded_export.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out_path, index=False)

    template_path = root / "review" / "review_import_template.parquet"
    pd.DataFrame(columns=["review_id", *REVIEW_SCORE_COLUMNS, "notes"]).to_parquet(
        template_path, index=False
    )
    return out_path


def validate_review_import(path: str | Path) -> None:
    frame = pd.read_parquet(path)
    required = {"review_id", *REVIEW_SCORE_COLUMNS}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ThemeBenchmarkError(
            f"Review import is missing required columns: {missing}"
        )
    if frame["review_id"].duplicated().any():
        raise ThemeBenchmarkError("Review import contains duplicate review_id values.")
    forbidden_columns = {"provider_id", "model_id", "provider", "model"}
    leaked_columns = sorted(forbidden_columns.intersection(frame.columns))
    if leaked_columns:
        raise ThemeBenchmarkError(
            f"Review import must not include provider identity columns: {leaked_columns}"
        )
    provider_tokens = ("keyword_baseline", "gemini", "llm7", "gpt-5-nano", "mock")
    searchable = frame.astype(str).to_string(index=False).lower()
    leaked = [token for token in provider_tokens if token in searchable]
    if leaked:
        raise ThemeBenchmarkError(
            "Review import appears to contain provider identity text."
        )
    for column in REVIEW_SCORE_COLUMNS:
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.isna().any():
            raise ThemeBenchmarkError(
                f"Review import column {column!r} must contain numeric scores."
            )
        invalid = values[(values < 1) | (values > 5)]
        if not invalid.empty:
            raise ThemeBenchmarkError(
                f"Review import column {column!r} must contain scores from 1 to 5."
            )
