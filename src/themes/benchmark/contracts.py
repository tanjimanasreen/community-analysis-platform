from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

BENCHMARK_SCHEMA_VERSION = 1
DATASET_SCHEMA_VERSION = 1
REQUEST_SCHEMA_VERSION = 1
RESULT_SCHEMA_VERSION = 1
OUTPUT_SCHEMA_VERSION = 1
CACHE_SCHEMA_VERSION = 1
REVIEW_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 1

KEYWORD_MODES = ("general", "absolute", "weighted")
ORIGINAL_KEYWORD_FIELDS = (
    "absolute_unigram_keywords",
    "absolute_bigram_keywords",
    "weighted_unigram_keywords",
    "weighted_bigram_keywords",
)

THEME_OUTPUT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name", "keywords"],
            },
        }
    },
    "required": ["themes"],
}


class ThemeBenchmarkError(ValueError):
    """Raised when a benchmark artifact or command is invalid."""


@dataclass(frozen=True)
class ThemeBenchmarkRequest:
    example_id: str
    keyword_mode: str
    keywords: list[str]
    keyword_text: str
    system_prompt: str
    user_prompt: str
    prompt_hash: str
    input_hash: str
    schema_version: int = REQUEST_SCHEMA_VERSION
    output_schema_version: int = OUTPUT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThemeBenchmarkResult:
    provider_id: str
    model_id: str
    request_id: str
    example_id: str
    keyword_mode: str
    input_hash: str
    prompt_hash: str
    cache_key: str
    normalized_theme_json: dict[str, Any]
    latency_ms: float | None = None
    usage: dict[str, Any] | None = None
    estimated_cost: float | None = None
    retries: int = 0
    cache_hit: bool = False
    error: str | None = None
    raw_response_path: str | None = None
    parsed_successfully: bool | None = None
    schema_valid: bool | None = None
    finish_reason: str | None = None
    safety_metadata: dict[str, Any] | None = None
    raw_metadata: dict[str, Any] | None = None
    schema_version: int = RESULT_SCHEMA_VERSION
    output_schema_version: int = OUTPUT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderMetadata:
    provider_id: str
    model_id: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkProviderStats:
    provider_id: str
    request_count: int = 0
    result_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    provider_executions: int = 0
    outbound_requests: int = 0
    failures: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkRunReport:
    request_count: int
    result_count: int
    cache_hits: int
    cache_misses: int
    provider_executions: int
    outbound_requests: int
    failures: int
    providers: dict[str, BenchmarkProviderStats]
    results_by_provider: dict[str, list[dict[str, Any]]]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["providers"] = {
            provider_id: stats.to_dict()
            for provider_id, stats in self.providers.items()
        }
        return data


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_hash(data: Any) -> str:
    return sha256_text(canonical_json(data))


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical_json(dict(row)) + "\n")


def append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(dict(row)) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise ThemeBenchmarkError(
                    f"Invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
    return rows


def ensure_keyword_mode(keyword_mode: str) -> None:
    if keyword_mode not in KEYWORD_MODES:
        raise ThemeBenchmarkError(
            f"Unsupported keyword_mode={keyword_mode!r}; expected one of {KEYWORD_MODES}."
        )
