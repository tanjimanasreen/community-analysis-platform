from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pandas as pd


KEYWORD_COLUMNS = (
    "absolute_unigram_keywords",
    "absolute_bigram_keywords",
    "weighted_unigram_keywords",
    "weighted_bigram_keywords",
)

MONTH_ORDER = {
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


def load_prepare_data(input_dir: str, year: str) -> dict[str, pd.DataFrame]:
    """Load monthly matched LDA CSVs and parse keyword list columns."""
    base = Path(input_dir)
    if not base.exists():
        return {}

    monthly_files = sorted(
        base.glob(f"*_{year}.csv"),
        key=lambda path: _month_sort_key(_month_from_filename(path, year)),
    )

    monthly_data: dict[str, pd.DataFrame] = {}
    for path in monthly_files:
        month = _month_from_filename(path, year)
        df = pd.read_csv(path)
        for column in KEYWORD_COLUMNS:
            if column not in df.columns:
                df[column] = [[] for _ in range(len(df))]
            else:
                df[column] = df[column].apply(_parse_keyword_list)
        monthly_data[month] = df
    return monthly_data


def _parse_keyword_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if pd.isna(value):
        return []
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            parsed = ast.literal_eval(text)
            return parsed if isinstance(parsed, list) else [parsed]
        if text == "":
            return []
        return [item.strip() for item in text.split(",") if item.strip()]
    return [value]


def _month_from_filename(path: Path, year: str) -> str:
    suffix = f"_{year}"
    stem = path.stem
    if stem.endswith(suffix):
        return stem[: -len(suffix)]
    return stem


def _month_sort_key(month: str) -> int:
    normalized = month.lower()
    if normalized.isdigit():
        return int(normalized)
    return MONTH_ORDER.get(normalized, 99)
