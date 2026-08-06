from __future__ import annotations

import ast
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
import yaml

from src.api.errors import (
    ArtifactNotFoundError,
    ArtifactUnavailableError,
    ArtifactValidationError,
    InvalidManifestError,
    RunNotCompletedError,
)
from src.api.services.run_catalog import RunCatalog
from src.artifacts.models import ArtifactCategory, ArtifactRecord, RunStatus
from src.artifacts.run_manifest import validate_artifact_record


class ArtifactReader:
    """Reads only manifest-listed, checksum-verified run artifacts."""

    def __init__(
        self,
        catalog: RunCatalog,
        *,
        parquet_cache_max_bytes: int = 16 * 1024 * 1024,
    ):
        self.catalog = catalog
        self.parquet_cache_max_bytes = max(0, int(parquet_cache_max_bytes))

    def records(self, run_id: str) -> tuple[ArtifactRecord, ...]:
        return self.catalog.get_manifest(run_id).artifacts

    def get_record(
        self,
        run_id: str,
        artifact_key: str,
        *,
        optional: bool = False,
        completed_only: bool = True,
    ) -> ArtifactRecord:
        manifest = self.catalog.get_manifest(run_id)
        if completed_only and manifest.status is not RunStatus.COMPLETED:
            raise RunNotCompletedError(run_id, manifest.status.value)
        for record in manifest.artifacts:
            if record.key == artifact_key:
                return record
        if optional:
            raise ArtifactUnavailableError(run_id, artifact_key)
        raise ArtifactNotFoundError(run_id, artifact_key)

    def find_records(
        self,
        run_id: str,
        *,
        key_prefix: str | None = None,
        path_contains: str | None = None,
        category: ArtifactCategory | None = None,
        media_type: str | None = None,
        completed_only: bool = True,
    ) -> list[ArtifactRecord]:
        manifest = self.catalog.get_manifest(run_id)
        if completed_only and manifest.status is not RunStatus.COMPLETED:
            raise RunNotCompletedError(run_id, manifest.status.value)
        result = []
        for record in manifest.artifacts:
            if key_prefix is not None and not record.key.startswith(key_prefix):
                continue
            if path_contains is not None and path_contains not in record.path:
                continue
            if category is not None and record.category is not category:
                continue
            if media_type is not None and record.media_type != media_type:
                continue
            result.append(record)
        return result

    def verified_path(self, run_id: str, record: ArtifactRecord) -> Path:
        root = self.catalog.get_run_root(run_id)
        candidate = root / record.path
        try:
            stat = candidate.stat()
            return _validate_artifact_cached(
                str(root),
                record,
                int(stat.st_size),
                int(stat.st_mtime_ns),
            )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message=str(exc),
            ) from exc

    def read_parquet(
        self,
        run_id: str,
        artifact_key: str,
        *,
        columns: list[str] | None = None,
        filters: list[tuple[str, str, Any]] | None = None,
    ) -> pd.DataFrame:
        record = self.get_record(run_id, artifact_key)
        return self.read_parquet_record(
            run_id, record, columns=columns, filters=filters
        )

    def read_parquet_record(
        self,
        run_id: str,
        record: ArtifactRecord,
        *,
        columns: list[str] | None = None,
        filters: list[tuple[str, str, Any]] | None = None,
    ) -> pd.DataFrame:
        path = self.verified_path(run_id, record)
        if path.suffix.lower() != ".parquet":
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message="artifact schema mismatch: expected Parquet",
            )
        if (
            columns is None
            and filters is None
            and record.byte_size is not None
            and record.byte_size <= self.parquet_cache_max_bytes
        ):
            return _read_parquet_cached(str(path), record.sha256).copy(deep=False)
        if columns is None and filters is None:
            return pd.read_parquet(path)
        # Column projection and Parquet predicate pushdown prevent graph API
        # requests from loading unrelated analytical columns into memory.
        return pd.read_parquet(path, columns=columns, filters=filters)

    def read_parquet_record_slice(
        self,
        run_id: str,
        record: ArtifactRecord,
        *,
        offset: int,
        limit: int,
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """Read only the requested Parquet row range using row-group slicing."""
        if offset < 0 or limit < 0:
            raise ValueError("offset and limit must be non-negative")
        path = self.verified_path(run_id, record)
        if path.suffix.lower() != ".parquet":
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message="artifact schema mismatch: expected Parquet",
            )

        import pyarrow as pa
        import pyarrow.parquet as pq

        parquet = pq.ParquetFile(path)
        available_columns = set(parquet.schema_arrow.names)
        selected_columns = (
            [column for column in columns if column in available_columns]
            if columns is not None
            else None
        )
        if limit == 0 or offset >= parquet.metadata.num_rows:
            names = selected_columns or parquet.schema_arrow.names
            return pd.DataFrame(columns=names)

        remaining_offset = offset
        remaining_limit = limit
        tables = []
        for row_group in range(parquet.num_row_groups):
            group_rows = parquet.metadata.row_group(row_group).num_rows
            if remaining_offset >= group_rows:
                remaining_offset -= group_rows
                continue
            table = parquet.read_row_group(row_group, columns=selected_columns)
            if remaining_offset:
                table = table.slice(remaining_offset)
                remaining_offset = 0
            if table.num_rows > remaining_limit:
                table = table.slice(0, remaining_limit)
            tables.append(table)
            remaining_limit -= table.num_rows
            if remaining_limit <= 0:
                break

        if not tables:
            names = selected_columns or parquet.schema_arrow.names
            return pd.DataFrame(columns=names)
        return pa.concat_tables(tables, promote=True).to_pandas()

    def read_parquet_records_page(
        self,
        run_id: str,
        records: Sequence[ArtifactRecord],
        *,
        limit: int,
        offset: int,
        columns: list[str] | None = None,
    ) -> tuple[pd.DataFrame, int]:
        """Page across ordered immutable Parquet artifacts without full reads."""
        ordered = list(records)
        total = sum(self.parquet_row_count(run_id, record) for record in ordered)
        if limit <= 0 or offset >= total:
            return pd.DataFrame(columns=columns or []), total

        remaining_offset = offset
        remaining_limit = limit
        frames: list[pd.DataFrame] = []
        for record in ordered:
            rows = self.parquet_row_count(run_id, record)
            if remaining_offset >= rows:
                remaining_offset -= rows
                continue
            frame = self.read_parquet_record_slice(
                run_id,
                record,
                offset=remaining_offset,
                limit=remaining_limit,
                columns=columns,
            )
            frames.append(frame)
            remaining_limit -= len(frame)
            remaining_offset = 0
            if remaining_limit <= 0:
                break
        if not frames:
            return pd.DataFrame(columns=columns or []), total
        return pd.concat(frames, ignore_index=True), total

    def parquet_row_count(self, run_id: str, record: ArtifactRecord) -> int:
        if record.rows is not None:
            self.verified_path(run_id, record)
            return int(record.rows)
        path = self.verified_path(run_id, record)
        import pyarrow.parquet as pq

        return int(pq.ParquetFile(path).metadata.num_rows)

    def read_json(self, run_id: str, artifact_key: str) -> dict[str, Any]:
        record = self.get_record(run_id, artifact_key)
        path = self.verified_path(run_id, record)
        if path.suffix.lower() != ".json":
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message="artifact schema mismatch: expected JSON",
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message="artifact schema mismatch: expected object",
            )
        return dict(payload)

    def read_safe_config(self, run_id: str) -> dict[str, Any]:
        root = self.catalog.get_run_root(run_id)
        path = root / "resolved_config.yaml"
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise InvalidManifestError(
                run_id, "The resolved run configuration is invalid."
            ) from exc
        if not isinstance(payload, Mapping):
            raise InvalidManifestError(
                run_id, "The resolved run configuration must be an object."
            )
        return dict(payload)

    @staticmethod
    def page(
        frame: pd.DataFrame,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        total = len(frame)
        page = frame.iloc[offset : offset + limit]
        records = [
            {str(key): normalize_value(value) for key, value in row.items()}
            for row in page.to_dict(orient="records")
        ]
        return records, total


@lru_cache(maxsize=512)
def _validate_artifact_cached(
    root: str,
    record: ArtifactRecord,
    byte_size: int,
    modified_ns: int,
) -> Path:
    # Size and mtime are part of the key so an altered file is re-validated.
    del byte_size, modified_ns
    return validate_artifact_record(root, record)


@lru_cache(maxsize=32)
def _read_parquet_cached(path: str, sha256: str) -> pd.DataFrame:
    del sha256  # Included in the cache key so changed artifacts are never reused.
    return pd.read_parquet(path)


def clear_csv_cache() -> None:
    _read_parquet_cached.cache_clear()
    _validate_artifact_cached.cache_clear()


def normalize_value(value: Any) -> Any:
    """Convert pandas/numpy/stringified literals into JSON-compatible values."""
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        return [normalize_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): normalize_value(item) for key, item in value.items()}
    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        missing = False
    if isinstance(missing, bool) and missing:
        return None

    if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
        try:
            return [normalize_value(item) for item in value.tolist()]
        except (TypeError, ValueError, AttributeError):
            pass

    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass

    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped[0] in "[{(" and stripped[-1] in "]})":
            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(stripped)
                except (json.JSONDecodeError, SyntaxError, ValueError):
                    continue
                return normalize_value(parsed)
        return value
    return value


def filter_by_community(
    frame: pd.DataFrame, community_id: str | int | None
) -> pd.DataFrame:
    if community_id is None:
        return frame
    wanted = str(community_id)
    columns = [
        column
        for column in (
            "community_number",
            "absolute_community",
            "weighted_community",
            "start_month_community",
            "end_month_community",
        )
        if column in frame.columns
    ]
    if not columns:
        return frame.iloc[0:0]
    mask = False
    for column in columns:
        current = frame[column].astype(str) == wanted
        mask = current if isinstance(mask, bool) else mask | current
    return frame.loc[mask]


def first_present(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None
