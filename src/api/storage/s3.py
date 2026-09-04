"""Amazon S3 implementation of ArtifactStorage using PyArrow FileSystem."""

from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING, Any, Iterator, Sequence

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.fs as pafs
    import pyarrow.parquet as pq

from src.api.storage.base import ArtifactStorage, FileMetadata


class S3ArtifactStorage(ArtifactStorage):
    """Artifact storage backed by Amazon S3."""

    def __init__(
        self,
        bucket: str,
        *,
        prefix: str = "",
        region: str | None = None,
        filesystem: pafs.FileSystem | None = None,
    ) -> None:
        if not bucket or not str(bucket).strip():
            raise ValueError("S3 bucket name must be explicitly provided")

        self.bucket = str(bucket).strip().strip("/")
        self.prefix = str(prefix).strip().strip("/")
        self.region = region.strip() if region and str(region).strip() else None
        self._fs: pafs.FileSystem | None = filesystem

    @property
    def fs(self) -> pafs.FileSystem:
        """Return the underlying PyArrow filesystem, initializing on demand."""
        if self._fs is None:
            import pyarrow.fs as pafs

            kwargs: dict[str, Any] = {}
            if self.region:
                kwargs["region"] = self.region
            self._fs = pafs.S3FileSystem(**kwargs)
        return self._fs

    @fs.setter
    def fs(self, value: pafs.FileSystem) -> None:
        self._fs = value

    @property
    def backend_type(self) -> str:
        return "s3"

    @property
    def root_uri(self) -> str:
        if self.prefix:
            return f"s3://{self.bucket}/{self.prefix}"
        return f"s3://{self.bucket}"

    @property
    def _is_native_s3(self) -> bool:
        import pyarrow.fs as pafs

        return isinstance(self.fs, pafs.S3FileSystem)

    def _base_dir(self) -> str:
        if self._is_native_s3:
            return f"{self.bucket}/{self.prefix}".strip("/")
        return self.prefix.strip("/")

    def is_ready(self) -> bool:
        import pyarrow.fs as pafs

        try:
            target = self._base_dir()
            info = self.fs.get_file_info(target)
            return info.type in (pafs.FileType.Directory, pafs.FileType.File)
        except Exception:
            return False

    def _full_path(self, relative_path: str) -> str:
        clean = str(relative_path).replace("\\", "/").strip()
        if clean.startswith("/"):
            raise ValueError(f"Path must be relative, not absolute: {relative_path}")
        normalized = posixpath.normpath(clean)
        if normalized == ".." or normalized.startswith("../"):
            raise ValueError(f"Path escapes artifact root: {relative_path}")
        base = self._base_dir()
        if base:
            return f"{base}/{normalized}"
        return normalized

    def _relative_from_full(self, full_path: str) -> str:
        normalized = full_path.replace("\\", "/").strip("/")
        base = self._base_dir()
        if base and (normalized == base or normalized.startswith(base + "/")):
            return normalized[len(base) + 1 :] if len(normalized) > len(base) else ""
        if self.bucket and normalized.startswith(self.bucket + "/"):
            return normalized[len(self.bucket) + 1 :]
        return normalized

    def list_run_manifest_paths(self) -> list[str]:
        import pyarrow.fs as pafs

        target_dir = self._base_dir()
        try:
            selector = pafs.FileSelector(
                target_dir, recursive=True, allow_not_found=True
            )
            infos = self.fs.get_file_info(selector)
        except Exception:
            return []

        manifest_paths: list[str] = []
        is_runs_root = posixpath.basename(target_dir.rstrip("/")) == "runs"
        for info in infos:
            if info.type == pafs.FileType.File and info.path.endswith("/manifest.json"):
                rel = self._relative_from_full(info.path)
                if not rel:
                    continue
                parts = rel.split("/")
                # Bound discovery to exact historical local layouts:
                # 1. runs/<run_id>/manifest.json
                # 2. <platform>/runs/<run_id>/manifest.json
                # 3. <platform>/<content_type>/runs/<run_id>/manifest.json
                # 4. <run_id>/manifest.json (only when root is named "runs")
                if len(parts) == 3 and parts[0] == "runs":
                    manifest_paths.append(rel)
                elif len(parts) == 4 and parts[1] == "runs":
                    manifest_paths.append(rel)
                elif len(parts) == 5 and parts[2] == "runs":
                    manifest_paths.append(rel)
                elif len(parts) == 2 and is_runs_root:
                    manifest_paths.append(rel)

        return sorted(manifest_paths)

    def read_bytes(self, relative_path: str) -> bytes:
        full_key = self._full_path(relative_path)
        with self.fs.open_input_file(full_key) as f:
            return f.read()

    def iter_bytes(
        self, relative_path: str, chunk_size: int = 65536
    ) -> Iterator[bytes]:
        import pyarrow.fs as pafs

        full_key = self._full_path(relative_path)
        info = self.fs.get_file_info(full_key)
        if info.type != pafs.FileType.File:
            raise FileNotFoundError(f"Artifact not found: {relative_path}")
        with self.fs.open_input_stream(full_key) as stream:
            while True:
                chunk = stream.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def read_text(self, relative_path: str, encoding: str = "utf-8") -> str:
        return self.read_bytes(relative_path).decode(encoding)

    def get_metadata(self, relative_path: str) -> FileMetadata:
        import pyarrow.fs as pafs

        full_key = self._full_path(relative_path)
        info = self.fs.get_file_info(full_key)
        if info.type != pafs.FileType.File:
            raise FileNotFoundError(f"Artifact not found: {relative_path}")
        return FileMetadata(
            size=int(info.size),
            mtime_ns=int(info.mtime_ns) if info.mtime_ns is not None else None,
        )

    def exists(self, relative_path: str) -> bool:
        try:
            import pyarrow.fs as pafs

            full_key = self._full_path(relative_path)
            info = self.fs.get_file_info(full_key)
            return info.type == pafs.FileType.File
        except Exception:
            return False

    def open_parquet(self, relative_path: str) -> pq.ParquetFile:
        import pyarrow.parquet as pq

        full_key = self._full_path(relative_path)
        return pq.ParquetFile(full_key, filesystem=self.fs)

    def read_parquet(
        self,
        relative_path: str,
        *,
        columns: Sequence[str] | None = None,
        filters: Sequence[tuple[str, str, Any]] | None = None,
    ) -> pd.DataFrame:
        import pandas as pd

        full_key = self._full_path(relative_path)
        if columns is None and filters is None:
            return pd.read_parquet(full_key, filesystem=self.fs)
        return pd.read_parquet(
            full_key,
            filesystem=self.fs,
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

        full_key = self._full_path(relative_path)
        parquet = pq.ParquetFile(full_key, filesystem=self.fs)
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

    def get_local_path(self, relative_path: str) -> None:
        return None
