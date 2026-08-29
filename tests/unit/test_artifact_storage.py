from __future__ import annotations

import json
import hashlib
from pathlib import Path
import pytest
import pandas as pd
import pyarrow as pa
import pyarrow.fs as pafs
import pyarrow.parquet as pq

import yaml

from src.api.errors import (
    ArtifactNotFoundError,
    ArtifactValidationError,
    InvalidManifestError,
    RunNotFoundError,
)
from src.api.services.artifact_reader import ArtifactReader
from src.api.services.run_catalog import RunCatalog
from src.api.storage.base import ArtifactStorage, FileMetadata
from src.api.storage.factory import create_artifact_storage, parse_s3_uri
from src.api.storage.local import LocalArtifactStorage
from src.api.storage.s3 import S3ArtifactStorage
from src.artifacts.models import (
    ArtifactCategory,
    ArtifactRecord,
    RunManifest,
    RunStatus,
)
from src.artifacts.run_manifest import (
    validate_artifact_record,
    validate_run_manifest,
)


def _create_sample_run(root_dir: Path, run_id: str = "run_sample_01") -> None:
    run_dir = root_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    data_dir = run_dir / "data" / "topics" / "scores"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create a small Parquet file
    df = pd.DataFrame(
        {
            "month": ["2017-03", "2017-03", "2017-03", "2017-03"],
            "unigram_absolute": ["['alpha']", "['beta']", "['gamma']", "['delta']"],
            "unigram_weighted": ["['alpha']", "['beta']", "['gamma']", "['delta']"],
            "bigram_absolute": [
                "['alpha beta']",
                "['beta gamma']",
                "['gamma delta']",
                "['delta alpha']",
            ],
            "bigram_weighted": [
                "['alpha beta']",
                "['beta gamma']",
                "['gamma delta']",
                "['delta alpha']",
            ],
        }
    )
    parquet_path = data_dir / "lda_scores.parquet"
    df.to_parquet(parquet_path, index=False)

    # Compute sha256 and byte_size
    bytes_data = parquet_path.read_bytes()
    sha256 = hashlib.sha256(bytes_data).hexdigest()
    byte_size = len(bytes_data)

    # Create manifest
    manifest_data = {
        "run_id": run_id,
        "schema_version": "1.0",
        "status": "completed",
        "created_at": "2026-08-28T00:00:00Z",
        "dataset": {
            "platform": "twitter",
            "content_type": "reply",
            "date_start": "2017-03-01",
            "date_end": "2017-03-31",
        },
        "pipeline": {
            "started_at": "2026-08-28T00:00:00Z",
            "completed_at": "2026-08-28T00:05:00Z",
        },
        "code": {},
        "artifacts": [
            {
                "key": "lda_scores",
                "path": "data/topics/scores/lda_scores.parquet",
                "category": "data",
                "media_type": "application/vnd.apache.parquet",
                "schema_version": "1.0",
                "sha256": sha256,
                "byte_size": byte_size,
                "rows": 4,
                "stage": "topic_modeling",
            }
        ],
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
    (run_dir / "resolved_config.yaml").write_text(
        "platform: twitter\n", encoding="utf-8"
    )
    inputs_dir = run_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    (inputs_dir / "datasets.json").write_text(
        json.dumps({"datasets": [{"source_name": "input.csv"}]}), encoding="utf-8"
    )


def test_parse_s3_uri() -> None:
    bucket, prefix = parse_s3_uri("s3://my-bucket/runs/2017")
    assert bucket == "my-bucket"
    assert prefix == "runs/2017"

    bucket2, prefix2 = parse_s3_uri("s3://simple-bucket")
    assert bucket2 == "simple-bucket"
    assert prefix2 == ""

    with pytest.raises(ValueError, match="Invalid S3 URI scheme"):
        parse_s3_uri("http://example.com")


def test_create_artifact_storage_factory(tmp_path: Path) -> None:
    local_storage = create_artifact_storage(artifact_root=tmp_path)
    assert isinstance(local_storage, LocalArtifactStorage)
    assert local_storage.backend_type == "local"

    # S3 via s3:// URI
    mock_fs = pafs.LocalFileSystem()
    s3_storage = create_artifact_storage(
        artifact_root="s3://my-bucket/test_prefix", filesystem=mock_fs
    )
    assert isinstance(s3_storage, S3ArtifactStorage)
    assert s3_storage.backend_type == "s3"
    assert s3_storage.bucket == "my-bucket"
    assert s3_storage.prefix == "test_prefix"

    # S3 backend requires bucket if not URI
    with pytest.raises(ValueError, match="S3 storage backend requires 's3_bucket'"):
        create_artifact_storage(backend_type="s3")

    # Invalid backend type
    with pytest.raises(ValueError, match="Unsupported storage backend"):
        create_artifact_storage(backend_type="gcs")


def test_local_and_s3_storage_equivalence(tmp_path: Path) -> None:
    _create_sample_run(tmp_path, "run_01")

    # Setup LocalArtifactStorage
    local_storage = LocalArtifactStorage(tmp_path)
    assert local_storage.is_ready()

    # Setup S3ArtifactStorage using PyArrow SubTreeFileSystem to simulate S3 bucket structure
    fs = pafs.LocalFileSystem()
    sub_fs = pafs.SubTreeFileSystem(str(tmp_path), fs)
    s3_storage = S3ArtifactStorage(
        bucket="test-bucket",
        prefix="",
        filesystem=sub_fs,
    )

    # 1. Verify manifest discovery
    local_manifests = local_storage.list_run_manifest_paths()
    s3_manifests = s3_storage.list_run_manifest_paths()
    assert local_manifests == ["runs/run_01/manifest.json"]
    assert s3_manifests == ["runs/run_01/manifest.json"]

    # 2. Verify bytes & text reading
    assert local_storage.read_text("runs/run_01/manifest.json") == s3_storage.read_text(
        "runs/run_01/manifest.json"
    )
    assert local_storage.read_bytes(
        "runs/run_01/manifest.json"
    ) == s3_storage.read_bytes("runs/run_01/manifest.json")

    # 3. Verify metadata
    local_meta = local_storage.get_metadata(
        "runs/run_01/data/topics/scores/lda_scores.parquet"
    )
    s3_meta = s3_storage.get_metadata(
        "runs/run_01/data/topics/scores/lda_scores.parquet"
    )
    assert local_meta.size == s3_meta.size
    assert local_meta.size > 0

    # 4. Verify Parquet reading
    rel_parquet = "runs/run_01/data/topics/scores/lda_scores.parquet"
    df_local = local_storage.read_parquet(rel_parquet)
    df_s3 = s3_storage.read_parquet(rel_parquet)
    pd.testing.assert_frame_equal(df_local, df_s3)

    # 5. Verify Parquet projection
    df_local_proj = local_storage.read_parquet(
        rel_parquet, columns=["month", "unigram_absolute"]
    )
    df_s3_proj = s3_storage.read_parquet(
        rel_parquet, columns=["month", "unigram_absolute"]
    )
    pd.testing.assert_frame_equal(df_local_proj, df_s3_proj)
    assert list(df_s3_proj.columns) == ["month", "unigram_absolute"]

    # 6. Verify Parquet slicing
    slice_local = local_storage.read_parquet_slice(rel_parquet, offset=1, limit=2)
    slice_s3 = s3_storage.read_parquet_slice(rel_parquet, offset=1, limit=2)
    pd.testing.assert_frame_equal(slice_local, slice_s3)
    assert len(slice_s3) == 2
    assert slice_s3["month"].tolist() == ["2017-03", "2017-03"]


def test_run_catalog_and_artifact_reader_with_s3(tmp_path: Path) -> None:
    root_with_prefix = tmp_path / "analytical_root"
    _create_sample_run(root_with_prefix, "run_s3_01")

    fs = pafs.LocalFileSystem()
    sub_fs = pafs.SubTreeFileSystem(str(tmp_path), fs)
    s3_storage = S3ArtifactStorage(
        bucket="my-data-bucket",
        prefix="analytical_root",
        filesystem=sub_fs,
    )

    catalog = RunCatalog(storage=s3_storage)
    manifests = catalog.list_manifests()
    assert len(manifests) == 1
    assert manifests[0].run_id == "run_s3_01"

    manifest = catalog.get_manifest("run_s3_01")
    assert manifest.status == RunStatus.COMPLETED

    # Quick and deep verification
    assert catalog.verify("run_s3_01", deep=False).run_id == "run_s3_01"
    assert catalog.verify("run_s3_01", deep=True).run_id == "run_s3_01"

    reader = ArtifactReader(catalog, storage=s3_storage)
    records = reader.records("run_s3_01")
    assert len(records) == 1
    assert records[0].key == "lda_scores"

    # Read Parquet
    df = reader.read_parquet("run_s3_01", "lda_scores")
    assert len(df) == 4
    assert "month" in df.columns

    # Read slice
    slice_df = reader.read_parquet_record_slice(
        "run_s3_01", records[0], offset=0, limit=2, columns=["month"]
    )
    assert len(slice_df) == 2
    assert list(slice_df.columns) == ["month"]

    # Read safe config
    cfg = reader.read_safe_config("run_s3_01")
    assert cfg.get("platform") == "twitter"

    # Error handling
    with pytest.raises(RunNotFoundError):
        catalog.get_manifest("non_existent_run")

    with pytest.raises(ArtifactNotFoundError):
        reader.get_record("run_s3_01", "non_existent_artifact")


def test_s3_storage_native_s3_path_formatting(monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Bucket only without prefix
    storage_root = S3ArtifactStorage(
        bucket="my-data-bucket", prefix="", filesystem=pafs.LocalFileSystem()
    )
    # Mock _is_native_s3 to True to test S3FileSystem path convention
    monkeypatch.setattr(S3ArtifactStorage, "_is_native_s3", True)

    assert storage_root._base_dir() == "my-data-bucket"
    assert (
        storage_root._full_path("runs/run-01/manifest.json")
        == "my-data-bucket/runs/run-01/manifest.json"
    )
    assert (
        storage_root._relative_from_full("my-data-bucket/runs/run-01/manifest.json")
        == "runs/run-01/manifest.json"
    )
    assert storage_root.root_uri == "s3://my-data-bucket"

    # 2. Bucket with nested prefix and leading/trailing slashes
    storage_nested = S3ArtifactStorage(
        bucket="my-data-bucket",
        prefix="///stage/artifacts///",
        filesystem=pafs.LocalFileSystem(),
    )
    assert storage_nested.prefix == "stage/artifacts"
    assert storage_nested._base_dir() == "my-data-bucket/stage/artifacts"
    assert (
        storage_nested._full_path("runs/run-01/data/network/network.parquet")
        == "my-data-bucket/stage/artifacts/runs/run-01/data/network/network.parquet"
    )
    assert (
        storage_nested._relative_from_full(
            "my-data-bucket/stage/artifacts/runs/run-01/data/network/network.parquet"
        )
        == "runs/run-01/data/network/network.parquet"
    )
    assert storage_nested.root_uri == "s3://my-data-bucket/stage/artifacts"

    # 3. Path traversal security checks
    with pytest.raises(ValueError, match="Path escapes artifact root"):
        storage_nested._full_path("../secret.txt")

    with pytest.raises(ValueError, match="Path escapes artifact root"):
        storage_nested._full_path("runs/../../outside.txt")

    with pytest.raises(ValueError, match="Path must be relative"):
        storage_nested._full_path("/runs/absolute.txt")


def test_storage_iter_bytes_streaming(tmp_path: Path) -> None:
    _create_sample_run(tmp_path, "stream_run")

    local_storage = LocalArtifactStorage(tmp_path)
    fs = pafs.LocalFileSystem()
    sub_fs = pafs.SubTreeFileSystem(str(tmp_path), fs)
    s3_storage = S3ArtifactStorage(bucket="bucket", filesystem=sub_fs)

    rel_path = "runs/stream_run/data/topics/scores/lda_scores.parquet"
    original_bytes = local_storage.read_bytes(rel_path)

    # Stream in 16-byte chunks
    local_chunks = list(local_storage.iter_bytes(rel_path, chunk_size=16))
    assert b"".join(local_chunks) == original_bytes
    assert len(local_chunks) > 1

    s3_chunks = list(s3_storage.iter_bytes(rel_path, chunk_size=16))
    assert b"".join(s3_chunks) == original_bytes
    assert len(s3_chunks) > 1


@pytest.fixture(params=["local", "s3"])
def storage_pair(request: pytest.FixtureRequest, tmp_path: Path) -> tuple[ArtifactStorage, Path]:
    backend = request.param
    base_dir = tmp_path / f"test_{backend}"
    base_dir.mkdir(parents=True, exist_ok=True)
    if backend == "local":
        return LocalArtifactStorage(base_dir), base_dir
    fs = pafs.LocalFileSystem()
    sub_fs = pafs.SubTreeFileSystem(str(base_dir), fs)
    return S3ArtifactStorage(bucket="test-bucket", filesystem=sub_fs), base_dir


def test_storage_validation_parity_valid_run(storage_pair: tuple[ArtifactStorage, Path]) -> None:
    storage, base_dir = storage_pair
    run_id = "parity_valid"
    _create_sample_run(base_dir, run_id)

    catalog = RunCatalog(storage=storage, refresh_seconds=0)
    reader = ArtifactReader(catalog, storage=storage)
    manifest = catalog.get_manifest(run_id)
    record = manifest.artifacts[0]

    # Quick verify, deep verify, and per-artifact verification all succeed on both backends
    assert catalog.verify(run_id, deep=False).run_id == run_id
    assert catalog.verify(run_id, deep=True).run_id == run_id
    assert reader.verified_path(run_id, record) is not None


def test_storage_validation_parity_missing_artifact(storage_pair: tuple[ArtifactStorage, Path]) -> None:
    storage, base_dir = storage_pair
    run_id = "parity_missing_art"
    _create_sample_run(base_dir, run_id)

    catalog = RunCatalog(storage=storage, refresh_seconds=0)
    reader = ArtifactReader(catalog, storage=storage)
    manifest = catalog.get_manifest(run_id)
    record = manifest.artifacts[0]

    # Delete the artifact file
    art_file = base_dir / "runs" / run_id / "data" / "topics" / "scores" / "lda_scores.parquet"
    art_file.unlink()

    with pytest.raises(InvalidManifestError, match="is not a regular file"):
        catalog.verify(run_id, deep=False)
    with pytest.raises(InvalidManifestError, match="is not a regular file"):
        catalog.verify(run_id, deep=True)
    with pytest.raises(ArtifactValidationError) as exc_info:
        reader.verified_path(run_id, record)
    assert exc_info.value.code == "ARTIFACT_VALIDATION_FAILED"


def test_storage_validation_parity_byte_size_mismatch(storage_pair: tuple[ArtifactStorage, Path]) -> None:
    storage, base_dir = storage_pair
    run_id = "parity_byte_size"
    _create_sample_run(base_dir, run_id)

    catalog = RunCatalog(storage=storage, refresh_seconds=0)
    reader = ArtifactReader(catalog, storage=storage)
    manifest = catalog.get_manifest(run_id)
    record = manifest.artifacts[0]

    # Mutate byte_size in manifest
    manifest_path = base_dir / "runs" / run_id / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["byte_size"] = 999999
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    catalog_mutated = RunCatalog(storage=storage, refresh_seconds=0)
    with pytest.raises(InvalidManifestError, match="byte size mismatch"):
        catalog_mutated.verify(run_id, deep=False)
    with pytest.raises(InvalidManifestError, match="byte size mismatch"):
        catalog_mutated.verify(run_id, deep=True)
    with pytest.raises(ArtifactValidationError) as exc_info:
        # Create a mutated record object to test reader directly
        mutated_rec = ArtifactRecord(
            key=record.key,
            path=record.path,
            category=record.category,
            media_type=record.media_type,
            schema_version=record.schema_version,
            sha256=record.sha256,
            byte_size=999999,
            rows=record.rows,
        )
        reader.verified_path(run_id, mutated_rec)
    assert exc_info.value.code == "ARTIFACT_CHECKSUM_MISMATCH"


def test_storage_validation_parity_missing_metadata(storage_pair: tuple[ArtifactStorage, Path]) -> None:
    storage, base_dir = storage_pair
    run_id = "parity_missing_meta"
    _create_sample_run(base_dir, run_id)

    # Delete inputs/datasets.json
    (base_dir / "runs" / run_id / "inputs" / "datasets.json").unlink()

    catalog = RunCatalog(storage=storage, refresh_seconds=0)
    # Quick mode passes (historical behavior)
    assert catalog.verify(run_id, deep=False).run_id == run_id
    # Deep mode fails on missing metadata file
    with pytest.raises(InvalidManifestError, match="run metadata file is missing"):
        catalog.verify(run_id, deep=True)


def test_storage_validation_parity_checksum_mismatch(storage_pair: tuple[ArtifactStorage, Path]) -> None:
    storage, base_dir = storage_pair
    run_id = "parity_checksum"
    _create_sample_run(base_dir, run_id)

    catalog = RunCatalog(storage=storage, refresh_seconds=0)
    reader = ArtifactReader(catalog, storage=storage)
    manifest = catalog.get_manifest(run_id)
    record = manifest.artifacts[0]

    # Tamper checksum
    manifest_path = base_dir / "runs" / run_id / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    catalog_mutated = RunCatalog(storage=storage, refresh_seconds=0)
    # Quick verify passes (does not re-hash)
    assert catalog_mutated.verify(run_id, deep=False).run_id == run_id
    # Deep verify and per-artifact verification fail on checksum mismatch
    with pytest.raises(InvalidManifestError, match="checksum mismatch"):
        catalog_mutated.verify(run_id, deep=True)
    with pytest.raises(ArtifactValidationError) as exc_info:
        mutated_rec = ArtifactRecord(
            key=record.key,
            path=record.path,
            category=record.category,
            media_type=record.media_type,
            schema_version=record.schema_version,
            sha256="0" * 64,
            byte_size=record.byte_size,
            rows=record.rows,
        )
        reader.verified_path(run_id, mutated_rec)
    assert exc_info.value.code == "ARTIFACT_CHECKSUM_MISMATCH"


def _add_network_data_artifact(base_dir: Path, run_id: str) -> ArtifactRecord:
    net_dir = base_dir / "runs" / run_id / "data" / "network"
    net_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {
            "unique_id": ["1", "2"],
            "from_id": ["u1", "u2"],
            "forwarder_id": ["u2", "u3"],
            "text": ["hello", "world"],
            "created_at": ["2017-03-01", "2017-03-02"],
        }
    )
    net_path = net_dir / "network.parquet"
    df.to_parquet(net_path, index=False)
    bytes_data = net_path.read_bytes()
    rec = ArtifactRecord(
        key="network_data",
        path="data/network/network.parquet",
        category=ArtifactCategory.DATA,
        media_type="application/vnd.apache.parquet",
        schema_version="1.0",
        sha256=hashlib.sha256(bytes_data).hexdigest(),
        byte_size=len(bytes_data),
        rows=2,
        stage="network_community",
    )
    manifest_path = base_dir / "runs" / run_id / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"].append(rec.to_dict())
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return rec


def test_storage_validation_parity_malformed_config_no_config_dependent_artifacts(
    storage_pair: tuple[ArtifactStorage, Path]
) -> None:
    # CASE 1: Run without config-dependent artifacts + malformed resolved_config.yaml
    storage, base_dir = storage_pair
    run_id = "parity_bad_config_no_dep"
    _create_sample_run(base_dir, run_id)

    config_path = base_dir / "runs" / run_id / "resolved_config.yaml"
    # 1. Invalid YAML syntax
    config_path.write_text(": invalid [yaml syntax", encoding="utf-8")

    catalog = RunCatalog(storage=storage, refresh_seconds=0)
    # Quick mode passes
    assert catalog.verify(run_id, deep=False).run_id == run_id
    # Deep mode PASSES because resolved_config is not parsed for lda_scores
    assert catalog.verify(run_id, deep=True).run_id == run_id

    # 2. Non-mapping YAML payload (e.g. list)
    config_path.write_text("- item1\n- item2\n", encoding="utf-8")
    catalog_non_map = RunCatalog(storage=storage, refresh_seconds=0)
    assert catalog_non_map.verify(run_id, deep=False).run_id == run_id
    assert catalog_non_map.verify(run_id, deep=True).run_id == run_id


def test_storage_validation_parity_missing_config_for_network_data(
    storage_pair: tuple[ArtifactStorage, Path]
) -> None:
    # CASE 2: network_data + missing resolved_config.yaml
    storage, base_dir = storage_pair
    run_id = "parity_missing_config_net"
    _create_sample_run(base_dir, run_id)
    net_rec = _add_network_data_artifact(base_dir, run_id)

    # Delete resolved_config.yaml
    (base_dir / "runs" / run_id / "resolved_config.yaml").unlink()

    catalog = RunCatalog(storage=storage, refresh_seconds=0)
    reader = ArtifactReader(catalog, storage=storage)

    # Quick verify passes (does not require config)
    assert catalog.verify(run_id, deep=False).run_id == run_id

    # Deep verify fails on missing metadata file
    with pytest.raises(InvalidManifestError, match="run metadata file is missing"):
        catalog.verify(run_id, deep=True)

    # Per-artifact validation fails with FileNotFoundError when config is missing
    with pytest.raises(FileNotFoundError):
        validate_artifact_record(
            catalog.get_run_rel_dir(run_id), net_rec, storage=storage
        )
    with pytest.raises(ArtifactValidationError):
        reader.verified_path(run_id, net_rec)


def test_storage_validation_parity_malformed_config_for_network_data(
    storage_pair: tuple[ArtifactStorage, Path]
) -> None:
    # CASE 3: network_data + malformed resolved_config.yaml
    storage, base_dir = storage_pair
    run_id = "parity_bad_config_net"
    _create_sample_run(base_dir, run_id)
    net_rec = _add_network_data_artifact(base_dir, run_id)

    config_path = base_dir / "runs" / run_id / "resolved_config.yaml"

    # 1. Invalid YAML syntax
    config_path.write_text(": invalid [yaml syntax", encoding="utf-8")
    catalog = RunCatalog(storage=storage, refresh_seconds=0)
    reader = ArtifactReader(catalog, storage=storage)
    with pytest.raises(yaml.YAMLError):
        validate_artifact_record(
            catalog.get_run_rel_dir(run_id), net_rec, storage=storage
        )
    with pytest.raises(yaml.YAMLError):
        catalog.verify(run_id, deep=True)

    # 2. Non-mapping YAML payload (e.g. list)
    config_path.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain an object"):
        validate_artifact_record(
            catalog.get_run_rel_dir(run_id), net_rec, storage=storage
        )
    with pytest.raises(InvalidManifestError, match="must contain an object"):
        catalog.verify(run_id, deep=True)


def test_storage_validation_parity_csv_utf8_bom(
    storage_pair: tuple[ArtifactStorage, Path]
) -> None:
    # CASE 4: CSV artifact with UTF-8 BOM
    storage, base_dir = storage_pair
    run_id = "parity_csv_bom"
    _create_sample_run(base_dir, run_id)

    csv_dir = base_dir / "runs" / run_id / "data" / "topics" / "scores"
    csv_path = csv_dir / "sample_scores.csv"
    # Write CSV with UTF-8 BOM
    csv_content = "\ufeffmonth,unigram_absolute,unigram_weighted,bigram_absolute,bigram_weighted\n2017-03,['a'],['a'],['a b'],['a b']\n"
    csv_path.write_bytes(csv_content.encode("utf-8"))

    bytes_data = csv_path.read_bytes()
    sha256 = hashlib.sha256(bytes_data).hexdigest()
    csv_rec = ArtifactRecord(
        key="lda_scores",
        path="data/topics/scores/sample_scores.csv",
        category=ArtifactCategory.DATA,
        media_type="text/csv",
        schema_version="1.0",
        sha256=sha256,
        byte_size=len(bytes_data),
        rows=1,
        stage="topic_modeling",
    )

    manifest_path = base_dir / "runs" / run_id / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"] = [csv_rec.to_dict()]
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    catalog = RunCatalog(storage=storage, refresh_seconds=0)
    reader = ArtifactReader(catalog, storage=storage)

    # Validates cleanly across Local and S3 without column corruption
    assert catalog.verify(run_id, deep=False).run_id == run_id
    assert catalog.verify(run_id, deep=True).run_id == run_id
    assert reader.verified_path(run_id, csv_rec) is not None


def test_storage_discovery_parity_layouts(tmp_path: Path) -> None:
    # CASE 5 & CASE 6: Valid and unsupported run-discovery layouts
    local_root = tmp_path / "discovery_local"
    s3_root = tmp_path / "discovery_s3"

    for root in (local_root, s3_root):
        # Valid layouts:
        _create_sample_run(root, "run_valid_1")  # runs/run_valid_1/manifest.json
        (root / "twitter" / "runs" / "run_valid_2").mkdir(parents=True, exist_ok=True)
        _create_sample_run(root / "twitter", "run_valid_2")  # twitter/runs/run_valid_2/manifest.json
        (root / "twitter" / "reply" / "runs" / "run_valid_3").mkdir(parents=True, exist_ok=True)
        _create_sample_run(root / "twitter" / "reply", "run_valid_3")  # twitter/reply/runs/run_valid_3/manifest.json

        # Unsupported / too-deep layouts (must be ignored):
        deep_dir = root / "a" / "b" / "c" / "runs" / "run_too_deep"
        deep_dir.mkdir(parents=True, exist_ok=True)
        _create_sample_run(root / "a" / "b" / "c", "run_too_deep")

        unrelated_dir = root / "unrelated" / "run_no_runs"
        unrelated_dir.mkdir(parents=True, exist_ok=True)
        (unrelated_dir / "manifest.json").write_text(json.dumps({"run_id": "run_no_runs"}), encoding="utf-8")

    local_storage = LocalArtifactStorage(local_root)
    s3_fs = pafs.SubTreeFileSystem(str(s3_root), pafs.LocalFileSystem())
    s3_storage = S3ArtifactStorage(bucket="test-bucket", filesystem=s3_fs)

    local_manifest_paths = set(local_storage.list_run_manifest_paths())
    s3_manifest_paths = set(s3_storage.list_run_manifest_paths())

    assert local_manifest_paths == {
        "runs/run_valid_1/manifest.json",
        "twitter/runs/run_valid_2/manifest.json",
        "twitter/reply/runs/run_valid_3/manifest.json",
    }
    assert s3_manifest_paths == local_manifest_paths

    local_catalog = RunCatalog(storage=local_storage, refresh_seconds=0)
    s3_catalog = RunCatalog(storage=s3_storage, refresh_seconds=0)

    local_run_ids = {r.run_id for r in local_catalog.list_manifests()}
    s3_run_ids = {r.run_id for r in s3_catalog.list_manifests()}

    # Both discover only the 3 valid layouts:
    assert local_run_ids == {"run_valid_1", "run_valid_2", "run_valid_3"}
    assert s3_run_ids == {"run_valid_1", "run_valid_2", "run_valid_3"}
    assert local_run_ids == s3_run_ids

    # Both ignore too-deep and unrelated layouts:
    assert "run_too_deep" not in local_run_ids
    assert "run_too_deep" not in s3_run_ids
    assert "run_no_runs" not in local_run_ids
    assert "run_no_runs" not in s3_run_ids


def test_storage_validation_parity_schema_mismatch(storage_pair: tuple[ArtifactStorage, Path]) -> None:
    storage, base_dir = storage_pair
    run_id = "parity_schema_mismatch"
    _create_sample_run(base_dir, run_id)

    # Write a parquet file missing required columns (e.g. only col_a)
    art_path = base_dir / "runs" / run_id / "data" / "topics" / "scores" / "lda_scores.parquet"
    bad_df = pd.DataFrame({"col_a": [1, 2]})
    bad_df.to_parquet(art_path, index=False)

    # Update byte_size and sha256 in manifest so size/checksum match the new file
    hasher = hashlib.sha256()
    hasher.update(art_path.read_bytes())
    new_hash = hasher.hexdigest()
    new_size = art_path.stat().st_size

    manifest_path = base_dir / "runs" / run_id / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["sha256"] = new_hash
    payload["artifacts"][0]["byte_size"] = new_size
    payload["artifacts"][0]["rows"] = len(bad_df)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    catalog = RunCatalog(storage=storage, refresh_seconds=0)
    reader = ArtifactReader(catalog, storage=storage)
    manifest = catalog.get_manifest(run_id)
    record = manifest.artifacts[0]

    # Quick verify passes (doesn't inspect columns)
    assert catalog.verify(run_id, deep=False).run_id == run_id
    # Deep verify and per-artifact verification fail with missing columns
    with pytest.raises(InvalidManifestError, match="missing columns"):
        catalog.verify(run_id, deep=True)
    with pytest.raises(ArtifactValidationError) as exc_info:
        reader.verified_path(run_id, record)
    assert exc_info.value.code == "ARTIFACT_SCHEMA_MISMATCH"


def test_storage_validation_parity_path_containment(storage_pair: tuple[ArtifactStorage, Path]) -> None:
    storage, base_dir = storage_pair
    run_id = "parity_path_contain"
    _create_sample_run(base_dir, run_id)

    manifest_path = base_dir / "runs" / run_id / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["path"] = "../escaped.parquet"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    catalog = RunCatalog(storage=storage, refresh_seconds=0)
    # Loading corrupted manifest with escaping path fails
    with pytest.raises(InvalidManifestError):
        catalog.get_manifest(run_id)
    with pytest.raises(InvalidManifestError):
        catalog.verify(run_id, deep=False)
    with pytest.raises(InvalidManifestError):
        catalog.verify(run_id, deep=True)


def test_storage_manifest_mutation_freshness_with_nonzero_ttl(
    storage_pair: tuple[ArtifactStorage, Path]
) -> None:
    storage, base_dir = storage_pair
    run_id = "parity_mutation_freshness"
    _create_sample_run(base_dir, run_id)

    # Instantiate catalog with 60s TTL
    catalog = RunCatalog(storage=storage, refresh_seconds=60.0)

    # 1. Initial get_manifest reads original manifest
    m1 = catalog.get_manifest(run_id)
    assert m1.run_id == run_id
    assert m1.code.get("git_commit") is None

    # 2. Modify manifest.json on underlying storage directly
    manifest_path = base_dir / "runs" / run_id / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["code"] = {"git_commit": "mutated_sha_12345"}
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    # 3. Cache deadline is still active in the future
    assert catalog._cache_deadline > 0

    # 4. Immediately read manifest without invalidating or expiring cache
    m2 = catalog.get_manifest(run_id)
    assert m2.run_id == run_id
    assert m2.code.get("git_commit") == "mutated_sha_12345"


def test_storage_manifest_deletion_freshness_with_nonzero_ttl(
    storage_pair: tuple[ArtifactStorage, Path]
) -> None:
    storage, base_dir = storage_pair
    run_id = "parity_deletion_freshness"
    _create_sample_run(base_dir, run_id)

    # Instantiate catalog with 60s TTL
    catalog = RunCatalog(storage=storage, refresh_seconds=60.0)

    # 1. Initial get_manifest succeeds
    m1 = catalog.get_manifest(run_id)
    assert m1.run_id == run_id

    # 2. Delete manifest.json on underlying storage directly
    manifest_path = base_dir / "runs" / run_id / "manifest.json"
    manifest_path.unlink()

    # 3. Cache deadline is still active in the future
    assert catalog._cache_deadline > 0

    # 4. Immediately read manifest: must raise RunNotFoundError (not return cached manifest)
    with pytest.raises(RunNotFoundError):
        catalog.get_manifest(run_id)
