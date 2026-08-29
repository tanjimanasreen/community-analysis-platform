# Execution Plan 090: Cloud Artifact Storage Abstraction and S3 Read Foundation

**Status**: complete
**Milestones**:
- [x] Pre-change verification (Git branch `dev`, clean tree, HEAD at `9d04d3bc`)
- [x] Design and implement `ArtifactStorage` abstraction (`LocalArtifactStorage`, `S3ArtifactStorage`) in `src/api/storage/`
- [x] Update `src/config/settings.py` and `src/api/dependencies.py` to support `storage_backend` ("local" / "s3"), S3 bucket, prefix, and region with backward-compatible defaults
- [x] Refactor `src/api/services/run_catalog.py` and `src/api/services/artifact_reader.py` to use `ArtifactStorage`
- [x] Update `src/api/routers/reports.py` to handle both local file responses and true remote streaming responses seamlessly
- [x] Add comprehensive tests for `LocalArtifactStorage`, `S3ArtifactStorage`, configuration, and S3-to-local contract equivalence
- [x] Verify non-regression across all existing API unit tests (`tests/unit/test_backend_api.py`, etc.)
- [x] Update documentation and `.env.example`
- [x] Surgical Remediation: Unified canonical run and artifact validation across Local and S3 backends (`validate_run_manifest`, `validate_artifact_record`)
- [x] Surgical Remediation: Added chunked streaming primitive (`iter_bytes`) to `ArtifactStorage` and updated remote download/report endpoints to return Starlette `StreamingResponse`
- [x] Surgical Remediation: Added offline tests for native S3 path formatting, traversal escaping, and prefix normalization
- [x] Surgical Remediation: Added comprehensive corruption & parity test coverage (tampered checksum, byte size, missing metadata, schema mismatch)
- [x] Surgical Remediation: Restored clean `Makefile` without stray whitespace changes
- [x] Ultra-Surgical Fix: Restored `RunCatalog.get_manifest()` freshness behavior with active discovery caching
- [x] Final Human Review and Approval

## Context & Objectives
Enable the read-only FastAPI serving layer (`src/api/`) to read analytical artifacts from either local disk or Amazon S3 (`s3://<bucket>/<prefix>`) via a clean, minimal storage abstraction. Local filesystem remains the default backend without requiring AWS credentials or network access.

## Architecture & Storage Abstraction Design
1. **Minimal Interface (`ArtifactStorage`)**:
   - `backend_type: str` ("local" | "s3")
   - `root_uri: str`
   - `is_ready() -> bool`
   - `list_run_manifest_paths() -> list[str]` (discovers `runs/<run_id>/manifest.json` keys)
   - `read_bytes(relative_path: str) -> bytes`
   - `iter_bytes(relative_path: str, chunk_size: int = 65536) -> Iterator[bytes]`
   - `read_text(relative_path: str, encoding: str = "utf-8") -> str`
   - `get_metadata(relative_path: str) -> FileMetadata` (size, mtime_ns, etag)
   - `exists(relative_path: str) -> bool`
   - `open_parquet(relative_path: str) -> pyarrow.parquet.ParquetFile`
   - `read_parquet(relative_path: str, columns=..., filters=...) -> pd.DataFrame`
   - `read_parquet_slice(relative_path: str, offset=..., limit=..., columns=...) -> pd.DataFrame`
   - `get_local_path(relative_path: str) -> Path | None` (returns local Path if local, None if remote)

2. **Storage Implementations**:
   - `LocalArtifactStorage`: Direct filesystem access wrapping `pathlib.Path` and PyArrow.
   - `S3ArtifactStorage`: Object storage access wrapping `pyarrow.fs.S3FileSystem` (and mockable with PyArrow filesystems in unit tests).

3. **Canonical Validation Parity**:
   - Storage-neutral validation engine (`_validate_run_manifest_storage`, `_validate_artifact_record_storage`) in `src/artifacts/run_manifest.py` enforcing identical lifecycle, metadata presence (`resolved_config.yaml`, `inputs/datasets.json`), path containment, category prefixes, media types, streaming SHA-256 checksums, Parquet/CSV shapes and column schemas, and JSON schema versions across all storage backends.

4. **No New Dependencies**:
   - `pyarrow` is already a core runtime dependency (`pyarrow>=12.0.0`) and includes `pyarrow._s3fs.S3FileSystem`.

5. **Preservation Guarantees**:
   - 100% backward compatibility for local filesystem runs.
   - No changes to manifest format, Parquet table schemas, checksum hashes, or API contracts.
   - Offline unit tests without live AWS credentials or network calls.

## Progress Log
- 2026-08-28: Completed pre-change discovery and verified clean Git working tree on branch `dev`.
- 2026-08-28: Implemented `src/api/storage/` module with `base.py`, `local.py`, `s3.py`, `factory.py`, and `__init__.py`.
- 2026-08-28: Updated `APISettings` in `src/config/settings.py` and `ApiSettings` in `src/api/dependencies.py` to support `COMMUNITY_ANALYSIS_STORAGE_BACKEND`, `COMMUNITY_ANALYSIS_S3_BUCKET`, `COMMUNITY_ANALYSIS_S3_PREFIX`, and `COMMUNITY_ANALYSIS_S3_REGION`.
- 2026-08-28: Refactored `RunCatalog` and `ArtifactReader` to operate over `ArtifactStorage`.
- 2026-08-28: Updated `reports.py` router to stream remote S3 artifacts or serve local files via `FileResponse`.
- 2026-08-28: Added unit test suite in `tests/unit/test_artifact_storage.py` and integration suite in `tests/unit/test_api_storage_integration.py`.
- 2026-08-28: Validated all API unit tests, storage unit tests, CDK infra tests, `make format`, `make lint`, and `make api-smoke-test`.
- 2026-08-29: Executed Plan 090 Ultra-Surgical Fix (Manifest Freshness):
  1. Identified historical `RunCatalog.get_manifest()` freshness behavior where discovery/location caching was retained while manifest content re-reading was executed fresh per invocation.
  2. Bypassed cached `RunManifest` return in `get_manifest()` while maintaining active discovery TTL (`_cache_deadline` and `_path_cache`) to avoid redundant S3 listings.
  3. Added parameterized nonzero-TTL (60s) mutation and deletion regression tests across `LocalArtifactStorage` and `S3ArtifactStorage`.
  4. Validated 77 unit tests, `make api-smoke-test`, `make infra-test`, and `make lint`.
- 2026-08-29: Final human review:
  - APPROVED.
  - Storage abstraction architecture approved.
  - Local/S3 behavioral parity verified.
  - Manifest freshness parity verified.
  - Quick/deep validation parity verified.
  - ArtifactReader parity verified.
  - Native S3 path and bounded discovery behavior verified.
  - Remote streaming verified.
  - No analytical contracts changed.
  - No AWS resources changed during implementation/testing.

