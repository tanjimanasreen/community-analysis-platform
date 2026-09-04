"""Local filesystem implementation of ArtifactStorage."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Sequence

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

from src.api.storage.base import ArtifactStorage, FileMetadata


class LocalArtifactStorage(ArtifactStorage):
    """Artifact storage backed by the local filesystem."""

    def __init__(self, artifact_root: str | Path) -> None:
        self.artifact_root = Path(artifact_root).expanduser().resolve()

    @property
    def backend_type(self) -> str:
        return "local"

    @property
    def root_uri(self) -> str:
        return str(self.artifact_root)

    def is_ready(self) -> bool:
        return self.artifact_root.is_dir()

    def _resolve(self, relative_path: str) -> Path:
        clean = relative_path.lstrip("/\\")
        resolved = (self.artifact_root / clean).resolve()
        try:
            resolved.relative_to(self.artifact_root)
        except ValueError as exc:
            raise ValueError(f"Path escapes artifact root: {relative_path}") from exc
        return resolved

    def list_run_manifest_paths(self) -> list[str]:
        if not self.is_ready():
            return []

        run_roots = [self.artifact_root / "runs"]
        if self.artifact_root.name == "runs":
            run_roots.append(self.artifact_root)
        run_roots.extend(self.artifact_root.glob("*/runs"))
        run_roots.extend(self.artifact_root.glob("*/*/runs"))

        seen_roots: set[Path] = set()
        manifest_paths: list[str] = []

        for runs_root in run_roots:
            try:
                resolved_root = runs_root.resolve()
            except OSError:
                continue
            if resolved_root in seen_roots or not resolved_root.is_dir():
                continue
            seen_roots.add(resolved_root)

            for manifest_file in resolved_root.glob("*/manifest.json"):
                if manifest_file.is_file():
                    try:
                        rel = manifest_file.relative_to(self.artifact_root)
                        manifest_paths.append(str(rel).replace(os.sep, "/"))
                    except ValueError:
                        continue

        return sorted(manifest_paths)

    def read_bytes(self, relative_path: str) -> bytes:
        path = self._resolve(relative_path)
        return path.read_bytes()

    def iter_bytes(
        self, relative_path: str, chunk_size: int = 65536
    ) -> Iterator[bytes]:
        path = self._resolve(relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"Artifact not found: {relative_path}")
        with path.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def read_text(self, relative_path: str, encoding: str = "utf-8") -> str:
        path = self._resolve(relative_path)
        return path.read_text(encoding=encoding)

    def get_metadata(self, relative_path: str) -> FileMetadata:
        path = self._resolve(relative_path)
        stat = path.stat()
        return FileMetadata(
            size=int(stat.st_size),
            mtime_ns=int(stat.st_mtime_ns),
        )

    def exists(self, relative_path: str) -> bool:
        try:
            path = self._resolve(relative_path)
            return path.is_file()
        except (ValueError, OSError):
            return False

    def open_parquet(self, relative_path: str) -> pq.ParquetFile:
        import pyarrow.parquet as pq

        path = self._resolve(relative_path)
        return pq.ParquetFile(path)

    def read_parquet(
        self,
        relative_path: str,
        *,
        columns: Sequence[str] | None = None,
        filters: Sequence[tuple[str, str, Any]] | None = None,
    ) -> pd.DataFrame:
        import pandas as pd

        path = self._resolve(relative_path)
        if columns is None and filters is None:
            return pd.read_parquet(path)
        return pd.read_parquet(
            path,
            columns=list(columns) if columns is not None else None,
            filters=filters,
        )

    def read_parquet_slice(
        self,
        relative_path: str,
        *,
        offset: int,
        limit: int,
        columns: Sequence[str] | None = None,
    ) -> pd.DataFrame:
        if offset < 0 or limit < 0:
            raise ValueError("offset and limit must be non-negative")

        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq

        path = self._resolve(relative_path)
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
        return pa.concat_tables(tables, promote_options="default").to_pandas()

    def get_local_path(self, relative_path: str) -> Path | None:
        return self._resolve(relative_path)
