"""
Shared artifact validation helper for orchestration tasks.

Every ArtifactReference that enters a Prefect task must pass these checks
before any domain logic is executed. Failures are terminal (retries=0).
"""

import os
from pathlib import Path
from typing import Sequence

from src.orchestration.models import ArtifactReference
from src.orchestration.hashing import hash_file
from src.orchestration.retry_policy import ErrorCategory, PipelineError

# Extensions that are allowed in analytical artifact references
_ALLOWED_EXTENSIONS = {".csv", ".json", ".html", ".png", ".parquet"}

_ALLOWED_CSV_MEDIA_TYPES = {"text/csv", "text/plain"}
_ALLOWED_JSON_MEDIA_TYPES = {"application/json"}
_ALLOWED_HTML_MEDIA_TYPES = {"text/html"}
_ALLOWED_IMAGE_MEDIA_TYPES = {"image/png", "image/jpeg"}


def validate_artifact(
    ref: ArtifactReference,
    allowed_roots: Sequence[str | Path],
    *,
    required: bool = True,
    expected_media_type: str | None = None,
    required_csv_columns: Sequence[str] | None = None,
    label: str = "artifact",
) -> None:
    """
    Validate an ArtifactReference before reading.

    Checks:
    - Path exists (if required)
    - Path is a regular file (not a directory)
    - Path resolves strictly under one of the allowed_roots (no traversal or symlink escape)
    - File extension is in the allowed set
    - Byte size matches ref.byte_size when provided
    - SHA-256 matches ref.sha256
    - Media type matches expected_media_type when provided
    - CSV schema contains required_csv_columns when provided

    Raises PipelineError with a terminal category on any failure.
    """
    path = ref.path
    if not path:
        raise PipelineError(
            f"{label}: ArtifactReference has empty path",
            ErrorCategory.MISSING_REQUIRED_INPUT,
        )

    # Existence check
    if not os.path.exists(path):
        if not required:
            return
        raise PipelineError(
            f"{label}: required artifact not found: {path}",
            ErrorCategory.MISSING_REQUIRED_INPUT,
        )

    # Regular file check (not directory, not symlink escaping)
    if not os.path.isfile(path):
        raise PipelineError(
            f"{label}: path is not a regular file: {path}",
            ErrorCategory.SCHEMA_VIOLATION,
        )

    # Path containment — resolve strictly to detect traversal and symlink escapes
    resolved_path = None
    try:
        resolved_path = Path(path).resolve(strict=True)
    except (ValueError, OSError) as exc:
        raise PipelineError(
            f"{label}: path could not be resolved: {exc}",
            ErrorCategory.SCHEMA_VIOLATION,
        ) from exc

    is_contained = False
    for root in allowed_roots:
        try:
            resolved_root = Path(root).resolve()
            resolved_path.relative_to(resolved_root)
            is_contained = True
            break
        except (ValueError, OSError):
            continue

    if not is_contained:
        raise PipelineError(
            f"{label}: path {path!r} is outside the allowed roots: {allowed_roots}",
            ErrorCategory.SCHEMA_VIOLATION,
        )

    # Extension check
    ext = resolved_path.suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise PipelineError(
            f"{label}: file extension {ext!r} is not allowed for {path}",
            ErrorCategory.SCHEMA_VIOLATION,
        )

    # Byte size check
    if ref.byte_size is not None:
        actual_size = os.path.getsize(path)
        if actual_size != ref.byte_size:
            raise PipelineError(
                f"{label}: byte size mismatch for {path}. "
                f"Expected {ref.byte_size}, got {actual_size}",
                ErrorCategory.SCHEMA_VIOLATION,
            )

    # SHA-256 check
    if ref.sha256:
        actual_hash = hash_file(path)
        if actual_hash != ref.sha256:
            raise PipelineError(
                f"{label}: SHA-256 mismatch for {path}. "
                f"Expected {ref.sha256}, got {actual_hash}",
                ErrorCategory.SCHEMA_VIOLATION,
            )

    # Media type check
    if expected_media_type and ref.media_type:
        if ref.media_type != expected_media_type:
            raise PipelineError(
                f"{label}: media type mismatch for {path}. "
                f"Expected {expected_media_type!r}, got {ref.media_type!r}",
                ErrorCategory.SCHEMA_VIOLATION,
            )

    # CSV schema check
    if required_csv_columns:
        import pandas as pd

        try:
            if path.endswith(".parquet"):
                # For Parquet, read the schema directly or read 0 rows
                header = pd.read_parquet(path)
            else:
                header = pd.read_csv(path, nrows=0)
            missing = [c for c in required_csv_columns if c not in header.columns]
            if missing:
                raise PipelineError(
                    f"{label}: {path} is missing required columns: {missing}",
                    ErrorCategory.SCHEMA_VIOLATION,
                )
        except PipelineError:
            raise
        except Exception as exc:
            raise PipelineError(
                f"{label}: could not read CSV schema for {path}: {exc}",
                ErrorCategory.SCHEMA_VIOLATION,
            ) from exc


def validate_artifact_output(
    path: str,
    allowed_root: str,
    *,
    label: str = "output artifact",
) -> None:
    """
    Validate a post-execution output artifact path.
    Uses OUTPUT_NOT_FOUND category (not MISSING_REQUIRED_INPUT) for
    missing post-execution outputs to distinguish pre/post execution failures.

    Checks:
    - Path exists
    - Path is a regular file
    - Path resolves under allowed_root
    """
    if not os.path.exists(path):
        raise PipelineError(
            f"{label}: expected output artifact not found after execution: {path}",
            ErrorCategory.OUTPUT_NOT_FOUND,
        )
    if not os.path.isfile(path):
        raise PipelineError(
            f"{label}: output path is not a regular file: {path}",
            ErrorCategory.OUTPUT_NOT_FOUND,
        )
    try:
        resolved_path = Path(path).resolve(strict=True)
        resolved_root = Path(allowed_root).resolve()
        resolved_path.relative_to(resolved_root)
    except (ValueError, OSError) as exc:
        raise PipelineError(
            f"{label}: output path {path!r} is outside the allowed root {allowed_root!r}: {exc}",
            ErrorCategory.SCHEMA_VIOLATION,
        ) from exc
