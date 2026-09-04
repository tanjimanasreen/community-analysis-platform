"""Base protocol and types for artifact storage backends."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow.parquet as pq


@dataclass(frozen=True)
class FileMetadata:
    """Metadata describing a stored artifact file."""

    size: int
    mtime_ns: int | None = None
    etag: str | None = None


@runtime_checkable
class ArtifactStorage(Protocol):
    """Protocol for reading analytical run artifacts from local disk or S3."""

    @property
    def backend_type(self) -> str:
        """Return the storage backend type ('local' or 's3')."""
        ...

    @property
    def root_uri(self) -> str:
        """Return a human-readable representation of the root location."""
        ...

    def is_ready(self) -> bool:
        """Return True if the underlying storage target is reachable and valid."""
        ...

    def list_run_manifest_paths(self) -> list[str]:
        """Discover relative paths to all manifest.json files (e.g. 'runs/2017-03_twitter_reply/manifest.json')."""
        ...

    def read_bytes(self, relative_path: str) -> bytes:
        """Read raw bytes of an artifact."""
        ...

    def iter_bytes(
        self, relative_path: str, chunk_size: int = 65536
    ) -> Iterator[bytes]:
        """Yield binary chunks for the given artifact for streaming."""
        ...

    def read_text(self, relative_path: str, encoding: str = "utf-8") -> str:
        """Read decoded text content of an artifact."""
        ...

    def get_metadata(self, relative_path: str) -> FileMetadata:
        """Retrieve size and modification metadata for an artifact."""
        ...

    def exists(self, relative_path: str) -> bool:
        """Check whether the artifact exists."""
        ...

    def open_parquet(self, relative_path: str) -> pq.ParquetFile:
        """Open a Parquet file for metadata and row-group inspection."""
        ...

    def read_parquet(
        self,
        relative_path: str,
        *,
        columns: Sequence[str] | None = None,
        filters: Sequence[tuple[str, str, Any]] | None = None,
    ) -> pd.DataFrame:
        """Read a Parquet table with optional column projection and predicate pushdown."""
        ...

    def read_parquet_slice(
        self,
        relative_path: str,
        *,
        offset: int,
        limit: int,
        columns: Sequence[str] | None = None,
    ) -> pd.DataFrame:
        """Read a slice of rows using efficient Parquet row-group reading."""
        ...

    def get_local_path(self, relative_path: str) -> Path | None:
        """Return local Path if on local filesystem, or None if remote."""
        ...
