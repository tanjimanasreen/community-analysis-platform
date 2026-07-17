from __future__ import annotations

import ast
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

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

    def __init__(self, catalog: RunCatalog):
        self.catalog = catalog

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
        try:
            return validate_artifact_record(root, record)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message=str(exc),
            ) from exc

    def read_csv(self, run_id: str, artifact_key: str) -> pd.DataFrame:
        record = self.get_record(run_id, artifact_key)
        return self.read_csv_record(run_id, record)

    def read_csv_record(self, run_id: str, record: ArtifactRecord) -> pd.DataFrame:
        path = self.verified_path(run_id, record)
        if path.suffix.lower() != ".csv":
            raise ArtifactValidationError(
                run_id=run_id,
                artifact_key=record.key,
                validation_message="artifact schema mismatch: expected CSV",
            )
        return _read_csv_cached(str(path), record.sha256).copy(deep=False)

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


@lru_cache(maxsize=32)
def _read_csv_cached(path: str, sha256: str) -> pd.DataFrame:
    del sha256  # Included in the cache key so changed artifacts are never reused.
    return pd.read_csv(path, low_memory=False)


def clear_csv_cache() -> None:
    _read_csv_cached.cache_clear()


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
