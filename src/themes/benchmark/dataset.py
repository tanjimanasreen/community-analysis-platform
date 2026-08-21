from __future__ import annotations

import logging
import re
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

from src.config.defaults import DEFAULT_CONFIG
from src.themes.benchmark.contracts import (
    BENCHMARK_SCHEMA_VERSION,
    DATASET_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    ORIGINAL_KEYWORD_FIELDS,
    OUTPUT_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    THEME_OUTPUT_JSON_SCHEMA,
    THEME_PROMPT_CONTRACT_VERSION,
    build_theme_output_json_schema,
    ThemeBenchmarkError,
    ThemeBenchmarkRequest,
    read_jsonl,
    stable_hash,
    write_json,
    write_jsonl,
)
from src.themes.theme_inputs import ThemeInputError, load_theme_inputs

import json
import jinja2

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
_PROMPT_PACKAGE = "src.themes.benchmark.prompts"


def load_raw_template(name: str) -> str:
    """Load packaged prompt templates in editable and installed environments."""
    template_name = f"{name}.jinja2"
    try:
        return (
            resources.files(_PROMPT_PACKAGE)
            .joinpath(template_name)
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ModuleNotFoundError):
        # Compatibility for source checkouts created before prompts became
        # package data. Installed wheels always use the resource path above.
        path = REPO_ROOT / "configs" / "prompts" / template_name
        if path.exists():
            return path.read_text(encoding="utf-8")
        raise ThemeBenchmarkError(f"Theme prompt template is missing: {template_name}")


def get_jinja_env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.DictLoader(
            {
                "system.jinja2": load_raw_template("system"),
                "user.jinja2": load_raw_template("user"),
            }
        ),
        autoescape=False,
    )


RAW_SYSTEM_TEMPLATE = load_raw_template("system")
RAW_USER_TEMPLATE = load_raw_template("user")


def format_indexed_keywords_for_prompt(keywords: list[Any]) -> str:
    """Render explicit zero-based evidence IDs without changing keyword order."""
    return "\n".join(
        f"[{index}] {json.dumps(str(keyword), ensure_ascii=False)}"
        for index, keyword in enumerate(keywords)
    )


def load_prompt_templates() -> dict[str, str]:
    return {
        "system_prompt": RAW_SYSTEM_TEMPLATE,
        "user_prompt_template": RAW_USER_TEMPLATE,
    }


def register_theme_prompt_to_mlflow(commit_message: str | None = None) -> Any:
    """Registers the loaded Jinja templates to MLflow Prompt Registry for versioning and tuning."""
    try:
        import mlflow
        from src.themes.benchmark.contracts import THEME_OUTPUT_JSON_SCHEMA

        return mlflow.register_prompt(
            name="theme_generation_prompt",
            template=[
                {"role": "system", "content": RAW_SYSTEM_TEMPLATE},
                {"role": "user", "content": RAW_USER_TEMPLATE},
            ],
            response_format=THEME_OUTPUT_JSON_SCHEMA,
            commit_message=commit_message
            or "Automatic registration from theme pipeline",
        )
    except Exception as exc:
        logger.warning(
            "mlflow_prompt_registration_failed error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return None


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
        raise ThemeBenchmarkError(
            f"Benchmark path escapes experiment root: {path}"
        ) from exc
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
    write_jsonl(
        output_dir / "requests.jsonl", [request.to_dict() for request in requests]
    )
    write_json(output_dir / "reference" / "gpt4o_config.json", prompt_reference)
    if gpt4o_outputs is not None:
        _import_reference_outputs(
            Path(gpt4o_outputs), output_dir / "reference" / "gpt4o_outputs.jsonl"
        )

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
        "prompt_contract_version": THEME_PROMPT_CONTRACT_VERSION,
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
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
        frame = monthly_data[month].reset_index(drop=True)
        columns = list(frame.columns)
        positions = {column: index for index, column in enumerate(columns)}

        def value(row: tuple[Any, ...], column: str, default: Any = None) -> Any:
            position = positions.get(column)
            return default if position is None else row[position]

        # ``itertuples`` avoids the Series allocation and dtype coercion of
        # ``iterrows`` when large benchmark inventories are generated.
        for row_index, row in enumerate(frame.itertuples(index=False, name=None)):
            original = {
                field: _as_list(value(row, field, []))
                for field in ORIGINAL_KEYWORD_FIELDS
            }
            keyword_lists = {
                "absolute": _unique_preserve_order(
                    original["absolute_unigram_keywords"]
                    + original["absolute_bigram_keywords"]
                ),
                "weighted": _unique_preserve_order(
                    original["weighted_unigram_keywords"]
                    + original["weighted_bigram_keywords"]
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
                "absolute_community": _json_safe(value(row, "absolute_community")),
                "weighted_community": _json_safe(value(row, "weighted_community")),
                "members_count": len(_as_list(value(row, "members", []))),
                **original,
                "absolute_keywords": keyword_lists["absolute"],
                "weighted_keywords": keyword_lists["weighted"],
                "general_keywords": keyword_lists["general"],
                "absolute_keyword_text": format_keywords_for_production(
                    keyword_lists["absolute"]
                ),
                "weighted_keyword_text": format_keywords_for_production(
                    keyword_lists["weighted"]
                ),
                "general_keyword_text": format_keywords_for_production(
                    keyword_lists["general"]
                ),
            }
            base["input_hash"] = stable_hash(base)
            examples.append(base)
            if limit is not None and len(examples) >= limit:
                return examples
    return examples


def build_requests(examples: list[Mapping[str, Any]]) -> list[ThemeBenchmarkRequest]:
    requests: list[ThemeBenchmarkRequest] = []
    env = get_jinja_env()
    sys_tmpl = env.get_template("system.jinja2")
    user_tmpl = env.get_template("user.jinja2")

    for example in examples:
        for keyword_mode in ("general", "absolute", "weighted"):
            keyword_text = str(example[f"{keyword_mode}_keyword_text"])
            keywords = list(example[f"{keyword_mode}_keywords"])

            output_schema = build_theme_output_json_schema(len(keywords))
            system_prompt = sys_tmpl.render(
                json_schema=json.dumps(output_schema, indent=2)
            )
            user_prompt = user_tmpl.render(
                keywords=format_indexed_keywords_for_prompt(keywords)
            )

            prompt_hash = stable_hash(
                {
                    "system": RAW_SYSTEM_TEMPLATE,
                    "user_template": RAW_USER_TEMPLATE,
                    "user": user_prompt,
                    "keyword_order": keywords,
                    "output_schema": output_schema,
                    "prompt_contract_version": THEME_PROMPT_CONTRACT_VERSION,
                    "generation_settings": {
                        "temperature": 0.0,
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "theme_output",
                                "schema": output_schema,
                                "strict": True,
                            },
                        },
                    },
                }
            )
            requests.append(
                ThemeBenchmarkRequest(
                    example_id=str(example["example_id"]),
                    keyword_mode=keyword_mode,
                    keywords=keywords,
                    keyword_text=keyword_text,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    prompt_hash=prompt_hash,
                    input_hash=str(example["input_hash"]),
                    prompt_contract_version=THEME_PROMPT_CONTRACT_VERSION,
                )
            )
    return requests


def build_gpt4o_reference_metadata() -> dict[str, Any]:
    template_hash = stable_hash(
        {
            "system": RAW_SYSTEM_TEMPLATE,
            "user_template": RAW_USER_TEMPLATE,
            "output_schema": THEME_OUTPUT_JSON_SCHEMA,
            "prompt_contract_version": THEME_PROMPT_CONTRACT_VERSION,
            "generation_settings": {
                "temperature": 0.0,
                "seed": 42,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "theme_output",
                        "schema": THEME_OUTPUT_JSON_SCHEMA,
                        "strict": True,
                    },
                },
            },
        }
    )
    return {
        "schema_version": 1,
        "model_id": "gpt-5-nano",
        "temperature": 0.0,
        "seed": 42,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "theme_output",
                "schema": THEME_OUTPUT_JSON_SCHEMA,
                "strict": True,
            },
        },
        "output_schema": THEME_OUTPUT_JSON_SCHEMA,
        "system_prompt": RAW_SYSTEM_TEMPLATE,
        "user_prompt_template": RAW_USER_TEMPLATE,
        "prompt_hash": template_hash,
        "prompt_contract_version": THEME_PROMPT_CONTRACT_VERSION,
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "notes": "Reference metadata only; Plan 016A never calls OpenAI.",
    }


def load_dataset(output_base_path: str | Path, run_id: str) -> list[dict[str, Any]]:
    return read_jsonl(benchmark_root(output_base_path, run_id) / "dataset.jsonl")


def load_requests(
    output_base_path: str | Path, run_id: str
) -> list[ThemeBenchmarkRequest]:
    rows = read_jsonl(benchmark_root(output_base_path, run_id) / "requests.jsonl")
    return [ThemeBenchmarkRequest(**row) for row in rows]


def format_keywords_for_production(keywords: list[Any]) -> str:
    return (
        str([str(keyword) for keyword in keywords])
        .replace("[", "")
        .replace("]", "")
        .replace(" ", "")
        .replace("'", "")
    )


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
