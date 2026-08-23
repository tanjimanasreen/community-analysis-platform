from __future__ import annotations

import json
import logging
import os
import re
import shutil
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from src.artifacts.run_manifest import run_root_path, utc_now
from src.orchestration.hashing import hash_file
from src.orchestration.models import ArtifactReference, PipelineRunContext

logger = logging.getLogger(__name__)

STAGE_CACHE_SCHEMA_VERSION = "1"
_STAGE_CACHE_DIR = ".stage_cache"
_STAGE_CACHE_LAYOUT_VERSION = "v1"
_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def artifact_reuse_enabled(config: Mapping[str, Any]) -> bool:
    orchestration = config.get("orchestration", {})
    if not isinstance(orchestration, Mapping):
        return True
    enabled = orchestration.get("artifact_reuse", True)
    return enabled if isinstance(enabled, bool) else True


def stage_cache_root(output_root: str | Path) -> Path:
    return (
        Path(output_root).expanduser().resolve()
        / _STAGE_CACHE_DIR
        / _STAGE_CACHE_LAYOUT_VERSION
    )


def _entry_root(output_root: str | Path, stage: str, cache_key: str) -> Path:
    if _SAFE_COMPONENT.fullmatch(stage) is None:
        raise ValueError(f"invalid stage cache stage name: {stage!r}")
    if re.fullmatch(r"[0-9a-f]{64}", cache_key) is None:
        raise ValueError("stage cache key must be a lowercase SHA-256 digest")
    root = stage_cache_root(output_root)
    entry = (root / stage / cache_key).resolve()
    try:
        entry.relative_to(root)
    except ValueError as exc:
        raise ValueError("stage cache entry escapes configured output root") from exc
    return entry


def _relative_run_path(path: str | Path, run_root: Path) -> str:
    resolved = Path(path).resolve(strict=True)
    try:
        relative = resolved.relative_to(run_root.resolve())
    except ValueError as exc:
        raise ValueError(
            f"stage artifact is outside the current run root: {resolved}"
        ) from exc
    if not relative.parts:
        raise ValueError("stage artifact path cannot be the run root")
    return relative.as_posix()


def _safe_relative_path(value: object) -> PurePosixPath:
    text = str(value).replace("\\", "/").strip()
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts:
        raise ValueError(
            "stage cache artifact path must be relative and traversal-safe"
        )
    return path


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    shutil.copy2(source, temp)
    os.replace(temp, target)


def _manifest_payload(
    *,
    stage: str,
    cache_key: str,
    producer_run_id: str,
    artifacts: Sequence[ArtifactReference],
    run_root: Path,
) -> dict[str, Any]:
    records = []
    seen_paths: set[str] = set()
    seen_keys: set[str] = set()
    for artifact in artifacts:
        relative = _relative_run_path(artifact.path, run_root)
        if relative in seen_paths:
            raise ValueError(f"duplicate stage cache artifact path: {relative}")
        seen_paths.add(relative)
        asset_key = artifact.asset_key or Path(relative).stem
        if asset_key in seen_keys:
            raise ValueError(f"duplicate stage cache artifact key: {asset_key}")
        seen_keys.add(asset_key)
        source = Path(artifact.path).resolve(strict=True)
        actual_size = source.stat().st_size
        actual_hash = hash_file(str(source))
        if actual_hash != artifact.sha256:
            raise ValueError(
                f"stage artifact checksum mismatch before caching: {relative}"
            )
        if artifact.byte_size is not None and actual_size != artifact.byte_size:
            raise ValueError(
                f"stage artifact byte size mismatch before caching: {relative}"
            )
        records.append(
            {
                "relative_path": relative,
                "sha256": artifact.sha256,
                "media_type": artifact.media_type,
                "asset_key": asset_key,
                "row_count": artifact.row_count,
                "byte_size": actual_size,
            }
        )

    return {
        "schema_version": STAGE_CACHE_SCHEMA_VERSION,
        "stage": stage,
        "cache_key": cache_key,
        "producer_run_id": producer_run_id,
        "created_at": utc_now(),
        "artifacts": records,
    }


def _read_valid_manifest(
    entry: Path, *, stage: str, cache_key: str
) -> dict[str, Any] | None:
    manifest_path = entry / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != STAGE_CACHE_SCHEMA_VERSION:
        return None
    if payload.get("stage") != stage or payload.get("cache_key") != cache_key:
        return None
    records = payload.get("artifacts")
    if not isinstance(records, list) or not records:
        return None

    seen_paths: set[str] = set()
    seen_keys: set[str] = set()
    try:
        for record in records:
            if not isinstance(record, dict):
                return None
            relative = _safe_relative_path(record.get("relative_path"))
            rel_text = relative.as_posix()
            if rel_text in seen_paths:
                return None
            seen_paths.add(rel_text)
            asset_key = str(record.get("asset_key", "")).strip()
            if not asset_key or asset_key in seen_keys:
                return None
            seen_keys.add(asset_key)
            expected_hash = str(record.get("sha256", ""))
            expected_size = record.get("byte_size")
            if re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None:
                return None
            if not isinstance(expected_size, int) or expected_size < 0:
                return None
            cached_file = (entry / "files" / relative).resolve()
            cached_file.relative_to((entry / "files").resolve())
            if not cached_file.is_file():
                return None
            if cached_file.stat().st_size != expected_size:
                return None
            if hash_file(str(cached_file)) != expected_hash:
                return None
    except (OSError, ValueError, TypeError):
        return None
    return payload


def store_stage_artifacts(
    *,
    context: PipelineRunContext,
    stage: str,
    cache_key: str,
    artifacts: Sequence[ArtifactReference],
) -> Path:
    """Atomically persist immutable copies of one completed stage's outputs."""
    if not artifacts:
        raise ValueError("cannot cache a stage with no artifacts")
    run_root = run_root_path(context.output_root, context.pipeline_run_id)
    entry = _entry_root(context.output_root, stage, cache_key)

    existing = _read_valid_manifest(entry, stage=stage, cache_key=cache_key)
    if existing is not None:
        return entry
    if entry.exists():
        shutil.rmtree(entry, ignore_errors=True)

    entry.parent.mkdir(parents=True, exist_ok=True)
    temp = entry.parent / f".{cache_key}.{uuid.uuid4().hex}.tmp"
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True)

    try:
        payload = _manifest_payload(
            stage=stage,
            cache_key=cache_key,
            producer_run_id=context.pipeline_run_id,
            artifacts=artifacts,
            run_root=run_root,
        )
        for record, artifact in zip(payload["artifacts"], artifacts, strict=True):
            relative = _safe_relative_path(record["relative_path"])
            target = temp / "files" / relative
            _copy_file(Path(artifact.path).resolve(strict=True), target)
            if hash_file(str(target)) != record["sha256"]:
                raise ValueError(
                    f"stage cache copy checksum mismatch: {record['relative_path']}"
                )
        _atomic_write_json(temp / "manifest.json", payload)
        if _read_valid_manifest(temp, stage=stage, cache_key=cache_key) is None:
            raise ValueError("new stage cache entry failed integrity validation")

        # Another process may have completed the same immutable entry first.
        existing = _read_valid_manifest(entry, stage=stage, cache_key=cache_key)
        if existing is not None:
            shutil.rmtree(temp)
            return entry
        try:
            # Rename without replacement: concurrent equivalent writers are
            # first-writer-wins for this immutable computation identity.
            os.rename(temp, entry)
        except OSError:
            # A concurrent equivalent run may have published the immutable entry
            # after our last validation. Reuse it if it is now complete; otherwise
            # preserve the publication error rather than masking a corrupt cache.
            if _read_valid_manifest(entry, stage=stage, cache_key=cache_key) is None:
                raise
            shutil.rmtree(temp, ignore_errors=True)
        logger.info(
            "stage_artifact_cache_store stage=%s cache_key=%s artifact_count=%d",
            stage,
            cache_key[:12],
            len(artifacts),
        )
        return entry
    except Exception:
        if temp.exists():
            shutil.rmtree(temp, ignore_errors=True)
        raise


def restore_stage_artifacts(
    *,
    context: PipelineRunContext,
    stage: str,
    cache_key: str,
) -> tuple[ArtifactReference, ...] | None:
    """Restore a valid cached stage into the current run root, else return a miss."""
    entry = _entry_root(context.output_root, stage, cache_key)
    payload = _read_valid_manifest(entry, stage=stage, cache_key=cache_key)
    if payload is None:
        if entry.exists():
            logger.warning(
                "stage_artifact_cache_invalid stage=%s cache_key=%s",
                stage,
                cache_key[:12],
            )
        return None

    run_root = run_root_path(context.output_root, context.pipeline_run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    restored: list[ArtifactReference] = []
    for record in payload["artifacts"]:
        relative = _safe_relative_path(record["relative_path"])
        source = (entry / "files" / relative).resolve(strict=True)
        target = (run_root / relative).resolve()
        try:
            target.relative_to(run_root.resolve())
        except ValueError as exc:
            raise ValueError(
                "restored stage artifact escapes current run root"
            ) from exc
        _copy_file(source, target)
        if target.stat().st_size != record["byte_size"]:
            raise ValueError(
                f"restored stage artifact byte size mismatch: {relative.as_posix()}"
            )
        if hash_file(str(target)) != record["sha256"]:
            raise ValueError(
                f"restored stage artifact checksum mismatch: {relative.as_posix()}"
            )
        restored.append(
            ArtifactReference(
                path=str(target),
                sha256=record["sha256"],
                media_type=str(record["media_type"]),
                asset_key=str(record["asset_key"]),
                row_count=record.get("row_count"),
                byte_size=int(record["byte_size"]),
            )
        )

    logger.info(
        "stage_artifact_cache_hit stage=%s cache_key=%s "
        "producer_run_id=%s artifact_count=%d",
        stage,
        cache_key[:12],
        str(payload.get("producer_run_id", ""))[:12],
        len(restored),
    )
    return tuple(restored)
