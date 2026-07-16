from __future__ import annotations

from pathlib import Path
from typing import Any

from src.themes.benchmark.contracts import (
    CACHE_SCHEMA_VERSION,
    OUTPUT_SCHEMA_VERSION,
    ThemeBenchmarkRequest,
    append_jsonl,
    read_jsonl,
    stable_hash,
)


class JsonlResponseCache:
    def __init__(self, path: Path):
        self.path = path
        self.records = {record["cache_key"]: record for record in read_jsonl(path)}

    def cache_key(
        self,
        *,
        provider_id: str,
        model_id: str,
        request: ThemeBenchmarkRequest,
        parameters: dict[str, Any],
    ) -> str:
        return stable_hash(
            {
                "schema_version": CACHE_SCHEMA_VERSION,
                "provider_id": provider_id,
                "model_id": model_id,
                "prompt_hash": request.prompt_hash,
                "input_hash": request.input_hash,
                "request_schema_version": request.schema_version,
                "output_schema_version": OUTPUT_SCHEMA_VERSION,
                "keyword_mode": request.keyword_mode,
                "parameters": parameters,
            }
        )

    def get(self, cache_key: str) -> dict[str, Any] | None:
        return self.records.get(cache_key)

    def put(self, cache_key: str, record: dict[str, Any]) -> None:
        stored = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "cache_key": cache_key,
            **record,
        }
        self.records[cache_key] = stored
        append_jsonl(self.path, stored)
