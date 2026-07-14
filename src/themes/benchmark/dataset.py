from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from src.config.defaults import default_config
from src.themes.benchmark.contracts import (
    BENCHMARK_SCHEMA_VERSION,
    DATASET_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    ORIGINAL_KEYWORD_FIELDS,
    REQUEST_SCHEMA_VERSION,
    THEME_OUTPUT_JSON_SCHEMA,
    ThemeBenchmarkError,
    ThemeBenchmarkRequest,
    read_jsonl,
    stable_hash,
    write_json,
    write_jsonl,
)
from src.themes.theme_inputs import ThemeInputError, load_theme_inputs


SYSTEM_PROMPT = (
    "You are an expert who can find meaningful themes from a list of keywords, "
    "that may contain specific events, people, locations, or topics."
)
USER_PROMPT_TEMPLATE = (
    "Based on the list of the keywords given below, provide only the exact theme "
    "and the corresponding keywords in a coherent short sentence in a JSON. The "
    "keys of the json should be theme names and values should be corresponding "
    "keywords. There could be one theme or multiple themes for each set of "
    "keywords. Here is the list of keywords: {keywords}"
)

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def benchmark_root(output_base_path: str | Path, run_id: str) -> Path:
    if not RUN_ID_RE.match(str(run_id)) or ".." in Path(str(run_id)).parts:
        raise ThemeBenchmarkError(
            "Benchmark run_id must be a simple name containing only letters, "
            "numbers, '.', '_', or '-'."
        )
    root = Path(output_base_path) / "_experiments" / "theme_model_benchmark"
    path = root / str(run_id)
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ThemeBenchmarkError(f"Benchmark path escapes experiment root: {path}") from exc
    return path


def build_dataset(
    config: Mapping[str, Any],
    *,
    run_id: str,
    limit: int | None = None,
    gpt4o_outputs: str | Path | None = None,
) -> dict[str, Any]:
    params = _params(config)
    output_dir = benchmark_root(params["output_base_path"], run_id)
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
            f"Saved theme-input artifacts are required for theme benchmarks: {exc} "
            "Run run-topics first, or use make run-pipeline-sample for the sample config."
        ) from exc

    examples = examples_from_theme_inputs(
        bundle.monthly_data,
        data_type=params["data_type"],
        content_type=params["content_type"],
        year=params["year"],
        limit=limit,
    )
    dataset_hash = stable_hash(examples)
    requests = build_requests(examples)
    requests_hash = stable_hash([request.to_dict() for request in requests])
    prompt_reference = build_gpt4o_reference_metadata()

    write_jsonl(output_dir / "dataset.jsonl", examples)
    write_jsonl(output_dir / "requests.jsonl", [request.to_dict() for request in requests])
    write_json(output_dir / "reference" / "gpt4o_config.json", prompt_reference)
    if gpt4o_outputs is not None:
        _import_reference_outputs(Path(gpt4o_outputs), output_dir / "reference" / "gpt4o_outputs.jsonl")

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "benchmark_schema_version": BENCHMARK_SCHEMA_VERSION,
        "run_id": run_id,
        "data_type": params["data_type"],
        "content_type": params["content_type"],
        "year": params["year"],
        "limit_requested": limit,
        "example_count": len(examples),
        "request_count": len(requests),
        "dataset_hash": dataset_hash,
        "requests_hash": requests_hash,
        "prompt_hash": prompt_reference["prompt_hash"],
        "providers": [],
        "output_root": str(output_dir),
        "artifacts": {
            "dataset": "dataset.jsonl",
            "requests": "requests.jsonl",
            "gpt4o_config": "reference/gpt4o_config.json",
        },
    }
    write_json(output_dir / "manifest.json", manifest)
    return {
        "output_dir": output_dir,
        "manifest": manifest,
        "examples": examples,
        "requests": requests,
    }


def examples_from_theme_inputs(
    monthly_data: Mapping[str, Any],
    *,
    data_type: str,
    content_type: str,
    year: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for month in sorted(monthly_data.keys(), key=_month_sort_key):
        frame = monthly_data[month]
        for row_index, row in frame.reset_index(drop=True).iterrows():
            original = {field: _as_list(row.get(field, [])) for field in ORIGINAL_KEYWORD_FIELDS}
            keyword_lists = {
                "absolute": _unique_preserve_order(
                    original["absolute_unigram_keywords"] + original["absolute_bigram_keywords"]
                ),
                "weighted": _unique_preserve_order(
                    original["weighted_unigram_keywords"] + original["weighted_bigram_keywords"]
                ),
                "general": _unique_preserve_order(
                    original["absolute_unigram_keywords"]
                    + original["absolute_bigram_keywords"]
                    + original["weighted_unigram_keywords"]
                    + original["weighted_bigram_keywords"]
                ),
            }
            if not any(keyword_lists.values()):
                continue

            base = {
                "schema_version": DATASET_SCHEMA_VERSION,
                "example_id": f"{data_type}_{content_type}_{year}_{month}_row{row_index:04d}",
                "data_type": str(data_type),
                "content_type": str(content_type),
                "year": str(year),
                "month": str(month),
                "source_row_index": int(row_index),
                "absolute_community": _json_safe(row.get("absolute_community")),
                "weighted_community": _json_safe(row.get("weighted_community")),
                "members_count": len(_as_list(row.get("members", []))),
                **original,
                "absolute_keywords": keyword_lists["absolute"],
                "weighted_keywords": keyword_lists["weighted"],
                "general_keywords": keyword_lists["general"],
                "absolute_keyword_text": format_keywords_for_production(keyword_lists["absolute"]),
                "weighted_keyword_text": format_keywords_for_production(keyword_lists["weighted"]),
                "general_keyword_text": format_keywords_for_production(keyword_lists["general"]),
            }
            base["input_hash"] = stable_hash(base)
            examples.append(base)
            if limit is not None and len(examples) >= limit:
                return examples
    return examples


def build_requests(examples: list[Mapping[str, Any]]) -> list[ThemeBenchmarkRequest]:
    requests: list[ThemeBenchmarkRequest] = []
    for example in examples:
        for keyword_mode in ("general", "absolute", "weighted"):
            keyword_text = str(example[f"{keyword_mode}_keyword_text"])
            keywords = list(example[f"{keyword_mode}_keywords"])
            user_prompt = USER_PROMPT_TEMPLATE.format(keywords=keyword_text)
            prompt_hash = stable_hash(
                {
                    "system": SYSTEM_PROMPT,
                    "user_template": USER_PROMPT_TEMPLATE,
                    "user": user_prompt,
                    "keyword_order": keywords,
                    "output_schema": THEME_OUTPUT_JSON_SCHEMA,
                    "generation_settings": {
                        "temperature": 0.0,
                        "response_format": {"type": "json_object"},
                    },
                }
            )
            requests.append(
                ThemeBenchmarkRequest(
                    example_id=str(example["example_id"]),
                    keyword_mode=keyword_mode,
                    keywords=keywords,
                    keyword_text=keyword_text,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    prompt_hash=prompt_hash,
                    input_hash=str(example["input_hash"]),
                )
            )
    return requests


def build_gpt4o_reference_metadata() -> dict[str, Any]:
    template_hash = stable_hash(
        {
            "system": SYSTEM_PROMPT,
            "user_template": USER_PROMPT_TEMPLATE,
            "output_schema": THEME_OUTPUT_JSON_SCHEMA,
            "generation_settings": {
                "temperature": 0.0,
                "seed": 42,
                "response_format": {"type": "json_object"},
            },
        }
    )
    return {
        "schema_version": 1,
        "model_id": "gpt-4o",
        "temperature": 0.0,
        "seed": 42,
        "response_format": {"type": "json_object"},
        "output_schema": THEME_OUTPUT_JSON_SCHEMA,
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt_template": USER_PROMPT_TEMPLATE,
        "prompt_hash": template_hash,
        "output_schema_version": 1,
        "notes": "Reference metadata only; Plan 016A never calls OpenAI.",
    }


def load_dataset(output_base_path: str | Path, run_id: str) -> list[dict[str, Any]]:
    return read_jsonl(benchmark_root(output_base_path, run_id) / "dataset.jsonl")


def load_requests(output_base_path: str | Path, run_id: str) -> list[ThemeBenchmarkRequest]:
    rows = read_jsonl(benchmark_root(output_base_path, run_id) / "requests.jsonl")
    return [ThemeBenchmarkRequest(**row) for row in rows]


def format_keywords_for_production(keywords: list[Any]) -> str:
    return str([str(keyword) for keyword in keywords]).replace("[", "").replace("]", "").replace(" ", "").replace("'", "")


def _params(config: Mapping[str, Any]) -> dict[str, str]:
    return {
        "output_base_path": str(config.get("output_base_path", "results/")),
        "data_type": str(config.get("data_type", "twitter")),
        "content_type": str(config.get("content_type", "reply")),
        "year": str(config.get("year", "2017")),
    }


def _unique_preserve_order(values: list[Any]) -> list[str]:
    unique: dict[str, None] = {}
    for value in values:
        text = str(value)
        if text and text not in unique:
            unique[text] = None
    return list(unique.keys())


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    try:
        import pandas as pd

        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass
    return [value]


def _json_safe(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value


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


def _import_reference_outputs(source: Path, destination: Path) -> None:
    rows = read_jsonl(source)
    write_jsonl(destination, rows)
