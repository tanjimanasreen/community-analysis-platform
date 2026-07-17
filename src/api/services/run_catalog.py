from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.api.errors import InvalidManifestError, RunNotFoundError
from src.artifacts.models import RunManifest, RunStatus
from src.artifacts.run_manifest import load_run_manifest, validate_run_manifest

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

    def __init__(self, artifact_root: str | Path, *, refresh_seconds: float = 1.0):
        self.artifact_root = Path(artifact_root).expanduser().resolve()
        self.runs_root = self.artifact_root / "runs"
        self.refresh_seconds = max(0.0, float(refresh_seconds))
        self._cache_deadline = 0.0
        self._cache: tuple[RunManifest, ...] = ()

    def invalidate(self) -> None:
        self._cache_deadline = 0.0
        self._cache = ()

    def list_manifests(self, filters: RunFilter | None = None) -> list[RunManifest]:
        manifests = list(self._discover())
        if filters is not None:
            manifests = [item for item in manifests if _matches(item, filters)]
        return manifests

    def get_run_root(self, run_id: str) -> Path:
        normalized = str(run_id).strip()
        if _SAFE_RUN_ID.fullmatch(normalized) is None:
            raise RunNotFoundError(normalized or run_id)
        root = (self.runs_root / normalized).resolve()
        try:
            root.relative_to(self.runs_root.resolve())
        except ValueError as exc:
            raise RunNotFoundError(normalized) from exc
        if not root.is_dir():
            raise RunNotFoundError(normalized)
        return root

    def get_manifest(self, run_id: str) -> RunManifest:
        root = self.get_run_root(run_id)
        path = root / "manifest.json"
        if not path.is_file():
            raise RunNotFoundError(run_id)
        try:
            manifest = load_run_manifest(path)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise InvalidManifestError(run_id) from exc
        if manifest.run_id != run_id:
            raise InvalidManifestError(
                run_id, "The run manifest identifier does not match its directory."
            )
        return manifest

    def verify(self, run_id: str) -> RunManifest:
        root = self.get_run_root(run_id)
        try:
            return validate_run_manifest(root)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise InvalidManifestError(run_id, str(exc)) from exc

    def _discover(self) -> tuple[RunManifest, ...]:
        now = time.monotonic()
        if now < self._cache_deadline:
            return self._cache

        manifests: list[RunManifest] = []
        if self.runs_root.is_dir():
            for run_dir in self.runs_root.iterdir():
                if not run_dir.is_dir() or _SAFE_RUN_ID.fullmatch(run_dir.name) is None:
                    continue
                path = run_dir / "manifest.json"
                if not path.is_file():
                    continue
                try:
                    manifest = load_run_manifest(path)
                except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
                if manifest.run_id == run_dir.name:
                    manifests.append(manifest)

        manifests.sort(
            key=lambda item: str(item.pipeline.get("started_at") or ""), reverse=True
        )
        self._cache = tuple(manifests)
        self._cache_deadline = now + self.refresh_seconds
        return self._cache


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
