from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.api.errors import InvalidManifestError, RunNotFoundError
from src.api.storage.base import ArtifactStorage
from src.api.storage.factory import create_artifact_storage
from src.artifacts.models import RunManifest, RunStatus
from src.artifacts.run_manifest import validate_run_manifest

_SAFE_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


@dataclass(frozen=True)
class RunFilter:
    platform: str | None = None
    content_type: str | None = None
    year: int | None = None
    month: int | None = None
    status: RunStatus | None = None


class RunCatalog:
    """Discovers run manifests without eagerly reading analytical artifacts."""

    def __init__(
        self,
        artifact_root: str | Path | ArtifactStorage | None = None,
        *,
        refresh_seconds: float = 1.0,
        storage: ArtifactStorage | None = None,
    ):
        if storage is not None:
            self.storage: ArtifactStorage = storage
        elif isinstance(artifact_root, ArtifactStorage):
            self.storage = artifact_root
        else:
            self.storage = create_artifact_storage(
                artifact_root=artifact_root or "local_output"
            )

        if self.storage.backend_type == "local":
            self.artifact_root = Path(self.storage.root_uri)
        else:
            self.artifact_root = Path(str(artifact_root or "."))

        self.refresh_seconds = max(0.0, float(refresh_seconds))
        self._cache_deadline = 0.0
        self._cache: tuple[RunManifest, ...] = ()
        self._path_cache: dict[str, str] = {}  # run_id -> relative manifest path
        self._duplicate_run_ids: set[str] = set()

    def invalidate(self) -> None:
        self._cache_deadline = 0.0
        self._cache = ()
        self._path_cache = {}
        self._duplicate_run_ids = set()

    def list_manifests(self, filters: RunFilter | None = None) -> list[RunManifest]:
        manifests = list(self._discover())
        if filters is not None:
            manifests = [item for item in manifests if _matches(item, filters)]
        return manifests

    def get_run_rel_dir(self, run_id: str) -> str:
        normalized = str(run_id).strip()
        if _SAFE_RUN_ID.fullmatch(normalized) is None:
            raise RunNotFoundError(normalized or run_id)

        self._discover()
        if normalized in self._duplicate_run_ids:
            raise InvalidManifestError(
                normalized,
                "Duplicate run IDs were discovered under the configured artifact root.",
            )
        if normalized not in self._path_cache:
            raise RunNotFoundError(normalized)

        rel_path = self._path_cache[normalized]
        parts = rel_path.replace("\\", "/").split("/")
        return "/".join(parts[:-1])

    def get_run_root(self, run_id: str) -> Path:
        rel_dir = self.get_run_rel_dir(run_id)
        local_path = self.storage.get_local_path(rel_dir)
        if local_path is None or not local_path.is_dir():
            if self.storage.backend_type == "local":
                raise RunNotFoundError(run_id)
            return Path(rel_dir)
        return local_path

    def get_manifest(self, run_id: str) -> RunManifest:
        normalized = str(run_id).strip()
        if _SAFE_RUN_ID.fullmatch(normalized) is None:
            raise RunNotFoundError(normalized or run_id)

        self._discover()
        if normalized in self._duplicate_run_ids:
            raise InvalidManifestError(
                normalized,
                "Duplicate run IDs were discovered under the configured artifact root.",
            )
        if normalized not in self._path_cache:
            raise RunNotFoundError(normalized)

        rel_path = self._path_cache[normalized]
        if not self.storage.exists(rel_path):
            raise RunNotFoundError(normalized)
        try:
            payload = json.loads(self.storage.read_text(rel_path))
            manifest = RunManifest.from_dict(payload)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise InvalidManifestError(run_id) from exc
        if manifest.run_id != run_id:
            raise InvalidManifestError(
                run_id, "The run manifest identifier does not match its directory."
            )
        return manifest

    def verify(self, run_id: str, *, deep: bool = False) -> RunManifest:
        """Verify a run quickly for dashboard use or deeply for operations.

        Completed runs are checksum-verified before publication.  The default
        dashboard check therefore validates manifest structure, containment,
        file presence, and byte sizes without re-hashing every large artifact.
        Set ``deep=True`` for a full checksum and schema audit.
        """
        rel_dir = self.get_run_rel_dir(run_id)
        manifest = self.get_manifest(run_id)
        try:
            if deep:
                return validate_run_manifest(
                    manifest, run_root=rel_dir, storage=self.storage
                )
            _validate_manifest_files_quick(self.storage, rel_dir, manifest)
            return manifest
        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise InvalidManifestError(run_id, str(exc)) from exc

    def _discover(self) -> tuple[RunManifest, ...]:
        now = time.monotonic()
        if now < self._cache_deadline:
            return self._cache

        manifest_by_id: dict[str, RunManifest] = {}
        path_cache: dict[str, str] = {}
        duplicate_run_ids: set[str] = set()

        if self.storage.is_ready():
            manifest_paths = self.storage.list_run_manifest_paths()
            for rel_path in manifest_paths:
                parts = rel_path.replace("\\", "/").split("/")
                if len(parts) < 2 or parts[-1] != "manifest.json":
                    continue
                run_id = parts[-2]
                if _SAFE_RUN_ID.fullmatch(run_id) is None:
                    continue
                if run_id in duplicate_run_ids:
                    continue
                if run_id in path_cache:
                    duplicate_run_ids.add(run_id)
                    path_cache.pop(run_id, None)
                    manifest_by_id.pop(run_id, None)
                    continue
                path_cache[run_id] = rel_path
                try:
                    text = self.storage.read_text(rel_path)
                    payload = json.loads(text)
                    manifest = RunManifest.from_dict(payload)
                except (
                    OSError,
                    json.JSONDecodeError,
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    continue
                if manifest.run_id == run_id:
                    manifest_by_id[run_id] = manifest

        manifests = list(manifest_by_id.values())
        manifests.sort(
            key=lambda item: str(item.pipeline.get("started_at") or ""), reverse=True
        )
        self._cache = tuple(manifests)
        self._path_cache = path_cache
        self._duplicate_run_ids = duplicate_run_ids
        self._cache_deadline = now + self.refresh_seconds
        return self._cache


def _validate_manifest_files_quick(
    storage: ArtifactStorage, run_rel_dir: str, manifest: RunManifest
) -> None:
    for record in manifest.artifacts:
        clean = str(record.path).replace("\\", "/").strip()
        if clean.startswith("/") or ".." in clean.split("/"):
            raise ValueError(f"artifact path escapes the run root: {record.path}")
        full_rel = f"{run_rel_dir}/{clean}" if run_rel_dir else clean
        if not storage.exists(full_rel):
            raise ValueError(f"artifact is not a regular file: {record.path}")
        if record.byte_size is not None:
            meta = storage.get_metadata(full_rel)
            if meta.size != record.byte_size:
                raise ValueError(f"artifact byte size mismatch: {record.key}")


def _matches(manifest: RunManifest, filters: RunFilter) -> bool:
    dataset = manifest.dataset
    if filters.platform and str(dataset.get("platform", "")) != filters.platform:
        return False
    if (
        filters.content_type
        and str(dataset.get("content_type", "")) != filters.content_type
    ):
        return False
    if filters.status and manifest.status is not filters.status:
        return False

    date_start = str(dataset.get("date_start") or "")
    year, month = _year_month(date_start)
    if filters.year is not None and year != filters.year:
        return False
    if filters.month is not None and month != filters.month:
        return False
    return True


def _year_month(value: str) -> tuple[int | None, int | None]:
    try:
        parts = value.split("-")
        return int(parts[0]), int(parts[1])
    except (IndexError, TypeError, ValueError):
        return None, None


def manifest_year_month(manifest: RunManifest) -> tuple[int | None, int | None]:
    return _year_month(str(manifest.dataset.get("date_start") or ""))


def unique_values(manifests: Iterable[RunManifest], key: str) -> list[str]:
    return sorted(
        {
            str(item.dataset.get(key))
            for item in manifests
            if item.dataset.get(key) not in {None, ""}
        }
    )
