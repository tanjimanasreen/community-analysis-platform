from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Protocol

from src.themes.benchmark.contracts import ProviderMetadata, ThemeBenchmarkRequest


class ThemeResponseCache(Protocol):
    hit_count: int
    miss_count: int
    write_count: int
    error_count: int

    def get(self, key: str) -> dict | None: ...

    def put(
        self,
        key: str,
        response: dict,
        request: ThemeBenchmarkRequest,
        metadata: ProviderMetadata,
    ) -> None: ...


class NullThemeResponseCache:
    """Disabled cache backend with observable miss metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.hit_count = 0
        self.miss_count = 0
        self.write_count = 0
        self.error_count = 0

    def get(self, key: str) -> dict | None:
        del key
        with self._lock:
            self.miss_count += 1
        return None

    def put(
        self,
        key: str,
        response: dict,
        request: ThemeBenchmarkRequest,
        metadata: ProviderMetadata,
    ) -> None:
        del key, response, request, metadata


class InMemoryThemeResponseCache:
    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}
        self._lock = threading.RLock()
        self.hit_count = 0
        self.miss_count = 0
        self.write_count = 0
        self.error_count = 0

    def get(self, key: str) -> dict | None:
        with self._lock:
            response = self._cache.get(key)
            if response is None:
                self.miss_count += 1
                return None
            self.hit_count += 1
            return json.loads(json.dumps(response))

    def put(
        self,
        key: str,
        response: dict,
        request: ThemeBenchmarkRequest,
        metadata: ProviderMetadata,
    ) -> None:
        del request, metadata
        with self._lock:
            self._cache[key] = json.loads(json.dumps(response))
            self.write_count += 1


class SQLiteThemeResponseCache:
    def __init__(self, path: Path | str, failure_policy: str = "bypass") -> None:
        if failure_policy not in {"bypass", "fail"}:
            raise ValueError("cache failure_policy must be 'bypass' or 'fail'")
        self.path = Path(path).expanduser()
        self.failure_policy = failure_policy
        self._metrics_lock = threading.Lock()
        self.hit_count = 0
        self.miss_count = 0
        self.write_count = 0
        self.error_count = 0

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _increment(self, name: str) -> None:
        with self._metrics_lock:
            setattr(self, name, getattr(self, name) + 1)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _handle_error(self) -> None:
        self._increment("error_count")
        if self.failure_policy == "fail":
            raise

    def _init_db(self) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS theme_cache (
                        cache_key TEXT PRIMARY KEY,
                        provider_id TEXT NOT NULL,
                        model_id TEXT NOT NULL,
                        prompt_hash TEXT NOT NULL,
                        input_hash TEXT NOT NULL,
                        parameters_json TEXT NOT NULL,
                        response_json TEXT NOT NULL,
                        output_schema_version INTEGER NOT NULL,
                        created_at REAL NOT NULL,
                        last_accessed_at REAL NOT NULL,
                        hit_count INTEGER NOT NULL DEFAULT 0
                    )
                    """)
        except Exception:
            self._handle_error()

    def get(self, key: str) -> dict | None:
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT response_json FROM theme_cache WHERE cache_key = ?", (key,)
                ).fetchone()
                if row is not None:
                    try:
                        conn.execute(
                            "UPDATE theme_cache SET hit_count = hit_count + 1, "
                            "last_accessed_at = ? WHERE cache_key = ?",
                            (time.time(), key),
                        )
                    except sqlite3.Error:
                        # Telemetry updates must not turn a cache hit into a failure.
                        self._increment("error_count")
                    self._increment("hit_count")
                    return json.loads(row[0])
        except Exception:
            self._handle_error()
        self._increment("miss_count")
        return None

    def put(
        self,
        key: str,
        response: dict,
        request: ThemeBenchmarkRequest,
        metadata: ProviderMetadata,
    ) -> None:
        try:
            now = time.time()
            with self._get_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    """
                    INSERT INTO theme_cache (
                        cache_key, provider_id, model_id, prompt_hash, input_hash,
                        parameters_json, response_json, output_schema_version,
                        created_at, last_accessed_at, hit_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        response_json = excluded.response_json,
                        last_accessed_at = excluded.last_accessed_at
                    """,
                    (
                        key,
                        metadata.provider_id,
                        metadata.model_id,
                        request.prompt_hash,
                        request.input_hash,
                        json.dumps(
                            metadata.parameters, ensure_ascii=False, sort_keys=True
                        ),
                        json.dumps(response, ensure_ascii=False, sort_keys=True),
                        request.output_schema_version,
                        now,
                        now,
                    ),
                )
                conn.execute("COMMIT")
            self._increment("write_count")
        except Exception:
            self._handle_error()
