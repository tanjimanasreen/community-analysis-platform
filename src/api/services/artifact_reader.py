from __future__ import annotations

import ast
import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Iterator, Mapping, Sequence

import yaml

if TYPE_CHECKING:
    import pandas as pd

from src.api.errors import (
    ArtifactNotFoundError,
    ArtifactUnavailableError,
    ArtifactValidationError,
    InvalidManifestError,
    RunNotCompletedError,
)
from src.api.services.run_catalog import RunCatalog
from src.api.storage.base import ArtifactStorage
from src.artifacts.models import ArtifactCategory, ArtifactRecord, RunStatus
from src.artifacts.run_manifest import validate_artifact_record


class ArtifactReader:
    """Reads only manifest-listed, checksum-verified run artifacts."""

    def __init__(
        self,
        catalog: RunCatalog,
        *,
        parquet_cache_max_bytes: int = 16 * 1024 * 1024,
        storage: ArtifactStorage | None = None,
    ):
        self.catalog = catalog
        self.storage: ArtifactStorage = storage or catalog.storage
        self.parquet_cache_max_bytes = max(0, int(parquet_cache_max_bytes))

    def _rel_path(self, run_id: str, record: ArtifactRecord) -> str:
        rel_dir = self.catalog.get_run_rel_dir(run_id)
        return f"{rel_dir}/{record.path}" if rel_dir else record.path

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

    def get_local_path(self, run_id: str, record: ArtifactRecord) -> Path | None:
        rel_path = self._rel_path(run_id, record)
        return self.storage.get_local_path(rel_path)

    def verified_path(self, run_id: str, record: ArtifactRecord) -> Path:
        rel_path = self._rel_path(run_id, record)
        local_path = self.storage.get_local_path(rel_path)
        if local_path is not None:
            try:
                root = self.catalog.get_run_root(run_id)
                stat = local_path.stat()
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

        # Remote storage (S3) verification with full canonical record checks
        try:
            rel_dir = self.catalog.get_run_rel_dir(run_id)
            meta = self.storage.get_metadata(rel_path)
            return _validate_artifact_cached_storage(
                self.storage.root_uri,
                rel_dir,
                record,
                int(meta.size),
                int(meta.mtime_ns) if meta.mtime_ns is not None else 0,
                self.storage,
            )
        except (OSError, ValueError) as exc:
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message=str(exc),
            ) from exc

    def read_bytes(self, run_id: str, record: ArtifactRecord) -> bytes:
        rel_path = self._rel_path(run_id, record)
        return self.storage.read_bytes(rel_path)

    def iter_bytes(
        self, run_id: str, record: ArtifactRecord, chunk_size: int = 65536
    ) -> Iterator[bytes]:
        rel_path = self._rel_path(run_id, record)
        return self.storage.iter_bytes(rel_path, chunk_size=chunk_size)

    def read_text(
        self, run_id: str, record: ArtifactRecord, encoding: str = "utf-8"
    ) -> str:
        rel_path = self._rel_path(run_id, record)
        return self.storage.read_text(rel_path, encoding=encoding)

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
        if not record.path.lower().endswith(".parquet"):
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message="artifact schema mismatch: expected Parquet",
            )
        rel_path = self._rel_path(run_id, record)
        self.verified_path(run_id, record)

        if (
            columns is None
            and filters is None
            and record.byte_size is not None
            and record.byte_size <= self.parquet_cache_max_bytes
        ):
            return _read_parquet_cached(
                self.storage.root_uri, rel_path, record.sha256, self.storage
            ).copy(deep=False)

        return self.storage.read_parquet(rel_path, columns=columns, filters=filters)

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
        if not record.path.lower().endswith(".parquet"):
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message="artifact schema mismatch: expected Parquet",
            )
        rel_path = self._rel_path(run_id, record)
        self.verified_path(run_id, record)
        return self.storage.read_parquet_slice(
            rel_path, offset=offset, limit=limit, columns=columns
        )

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
        import pandas as pd

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
        rel_path = self._rel_path(run_id, record)
        self.verified_path(run_id, record)
        parquet = self.storage.open_parquet(rel_path)
        return int(parquet.metadata.num_rows)

    def read_json(self, run_id: str, artifact_key: str) -> dict[str, Any]:
        record = self.get_record(run_id, artifact_key)
        rel_path = self._rel_path(run_id, record)
        self.verified_path(run_id, record)
        if not record.path.lower().endswith(".json"):
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message="artifact schema mismatch: expected JSON",
            )
        payload = json.loads(self.storage.read_text(rel_path))
        if not isinstance(payload, Mapping):
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message="artifact schema mismatch: expected object",
            )
        return dict(payload)

    def read_safe_config(self, run_id: str) -> dict[str, Any]:
        rel_dir = self.catalog.get_run_rel_dir(run_id)
        rel_path = (
            f"{rel_dir}/resolved_config.yaml" if rel_dir else "resolved_config.yaml"
        )
        try:
            payload = yaml.safe_load(self.storage.read_text(rel_path)) or {}
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
    del byte_size, modified_ns
    return validate_artifact_record(root, record)


@lru_cache(maxsize=512)
def _validate_artifact_cached_storage(
    root_uri: str,
    rel_dir: str,
    record: ArtifactRecord,
    byte_size: int,
    modified_ns: int,
    storage: ArtifactStorage,
) -> Path:
    del root_uri, byte_size, modified_ns
    return validate_artifact_record(rel_dir, record, storage=storage)


@lru_cache(maxsize=32)
def _read_parquet_cached(
    root_uri: str,
    rel_path: str,
    sha256: str,
    storage: ArtifactStorage,
) -> pd.DataFrame:
    del root_uri, sha256
    return storage.read_parquet(rel_path)


def clear_csv_cache() -> None:
    _read_parquet_cached.cache_clear()
    _validate_artifact_cached.cache_clear()
    _validate_artifact_cached_storage.cache_clear()


def normalize_value(value: Any) -> Any:
    """Convert pandas/numpy/stringified literals into JSON-compatible values."""
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        return [normalize_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): normalize_value(item) for key, item in value.items()}
    import sys

    pd = sys.modules.get("pandas")
    if pd is not None:
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        try:
            missing = pd.isna(value)
        except (TypeError, ValueError):
            missing = False
        if isinstance(missing, bool) and missing:
            return None
    elif isinstance(value, float) and value != value:
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
