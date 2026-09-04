"""Factory for instantiating the configured artifact storage backend."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from src.api.storage.base import ArtifactStorage, FileMetadata
from src.api.storage.local import LocalArtifactStorage


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """Parse an s3:// URI into (bucket, prefix)."""
    parsed = urlparse(uri)
    if parsed.scheme != "s3":
        raise ValueError(f"Invalid S3 URI scheme: {uri}")
    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/")
    return bucket, prefix


def create_artifact_storage(
    *,
    backend_type: str = "local",
    artifact_root: str | Path | None = None,
    s3_bucket: str | None = None,
    s3_prefix: str = "",
    s3_region: str | None = None,
    filesystem: Any = None,
) -> ArtifactStorage:
    """Create the configured artifact storage backend.

    If ``artifact_root`` is an ``s3://`` URI, the S3 backend is selected automatically.
    """
    raw_root = str(artifact_root).strip() if artifact_root is not None else ""

    if raw_root.startswith("s3://"):
        from src.api.storage.s3 import S3ArtifactStorage

        parsed_bucket, parsed_prefix = parse_s3_uri(raw_root)
        resolved_bucket = s3_bucket or parsed_bucket
        resolved_prefix = s3_prefix or parsed_prefix
        return S3ArtifactStorage(
            bucket=resolved_bucket,
            prefix=resolved_prefix,
            region=s3_region,
            filesystem=filesystem,
        )

    normalized_backend = str(backend_type).strip().lower()

    if normalized_backend == "s3":
        if not s3_bucket:
            raise ValueError(
                "S3 storage backend requires 's3_bucket' (or an 's3://' artifact_root URI) to be configured"
            )
        from src.api.storage.s3 import S3ArtifactStorage

        return S3ArtifactStorage(
            bucket=s3_bucket,
            prefix=s3_prefix,
            region=s3_region,
            filesystem=filesystem,
        )

    if normalized_backend == "local":
        local_root = artifact_root or "local_output"
        return LocalArtifactStorage(local_root)

    raise ValueError(
        f"Unsupported storage backend '{backend_type}'. Allowed backends: 'local', 's3'"
    )
