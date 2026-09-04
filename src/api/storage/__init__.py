"""Artifact storage package for local filesystem and cloud object storage."""

from typing import TYPE_CHECKING

from src.api.storage.base import ArtifactStorage, FileMetadata
from src.api.storage.factory import create_artifact_storage, parse_s3_uri
from src.api.storage.local import LocalArtifactStorage

if TYPE_CHECKING:
    from src.api.storage.s3 import S3ArtifactStorage

__all__ = [
    "ArtifactStorage",
    "FileMetadata",
    "LocalArtifactStorage",
    "S3ArtifactStorage",
    "create_artifact_storage",
    "parse_s3_uri",
]


def __getattr__(name: str):
    if name == "S3ArtifactStorage":
        from src.api.storage.s3 import S3ArtifactStorage

        return S3ArtifactStorage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
