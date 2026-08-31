"""Unit tests for AWS Batch analytical pipeline runner (batch_runner.py)."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.cloud.batch_runner import (
    BatchRunnerConfig,
    _safe_s3_dest_path,
    download_s3_prefix,
    parse_args,
    publish_completed_run_to_s3,
    run_batch_job,
    upload_local_tree_to_s3,
)


def test_parse_args_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONFIG_PATH", raising=False)
    monkeypatch.delenv("CONFIG", raising=False)
    monkeypatch.delenv("COMMUNITY_ANALYSIS_S3_BUCKET", raising=False)
    monkeypatch.delenv("S3_BUCKET", raising=False)

    config = parse_args(["--config", "tests/configs/test_single_month.yml"])
    assert config.config_path == "tests/configs/test_single_month.yml"
    assert config.command == "run-all"
    assert config.s3_bucket is None
    assert config.skip_s3_download is False
    assert config.skip_s3_upload is False
    assert config.dry_run is False


def test_parse_args_env_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CONFIG_PATH", "configs/telegram/forwarded_message_evolution.yml"
    )
    monkeypatch.setenv("COMMUNITY_ANALYSIS_S3_BUCKET", "test-analytics-bucket")
    monkeypatch.setenv("THEME_PROVIDER", "mock")
    monkeypatch.setenv("SKIP_S3_DOWNLOAD", "true")
    monkeypatch.setenv("WORKSPACE_DIR", "/tmp/custom_workspace")

    config = parse_args([])
    assert config.config_path == "configs/telegram/forwarded_message_evolution.yml"
    assert config.command == "run-evolution-pipeline"
    assert config.s3_bucket == "test-analytics-bucket"
    assert config.theme_provider == "mock"
    assert config.workspace_dir == Path("/tmp/custom_workspace").resolve()
    assert config.skip_s3_download is True


def test_parse_args_missing_config_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONFIG_PATH", raising=False)
    monkeypatch.delenv("CONFIG", raising=False)

    with pytest.raises(SystemExit):
        parse_args([])


def test_download_s3_prefix_accepted_keys(tmp_path: Path) -> None:
    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {
            "Contents": [
                {"Key": "raw/good/file.csv"},
                {"Key": "raw/nested/month/file.csv"},
                {"Key": "raw/"},  # directory marker should be skipped
            ]
        }
    ]
    mock_s3.get_paginator.return_value = mock_paginator

    target_dir = tmp_path / "data" / "raw"
    count = download_s3_prefix(mock_s3, "my-bucket", "raw/", target_dir)

    assert count == 2
    assert mock_s3.download_file.call_count == 2
    download_calls = mock_s3.download_file.call_args_list
    assert download_calls[0][0] == (
        "my-bucket",
        "raw/good/file.csv",
        str((target_dir / "good" / "file.csv").resolve()),
    )
    assert download_calls[1][0] == (
        "my-bucket",
        "raw/nested/month/file.csv",
        str((target_dir / "nested" / "month" / "file.csv").resolve()),
    )


def test_download_s3_prefix_rejects_parent_traversal(tmp_path: Path) -> None:
    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"Contents": [{"Key": "raw/../../escape.py"}]}
    ]
    mock_s3.get_paginator.return_value = mock_paginator

    target_dir = tmp_path / "data" / "raw"
    with pytest.raises(ValueError, match="Path traversal detected in S3 object key"):
        download_s3_prefix(mock_s3, "my-bucket", "raw/", target_dir)

    mock_s3.download_file.assert_not_called()


def test_download_s3_prefix_rejects_deep_parent_traversal(tmp_path: Path) -> None:
    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"Contents": [{"Key": "raw/a/../../../escape.py"}]}
    ]
    mock_s3.get_paginator.return_value = mock_paginator

    target_dir = tmp_path / "data" / "raw"
    with pytest.raises(ValueError, match="Path traversal detected in S3 object key"):
        download_s3_prefix(mock_s3, "my-bucket", "raw/", target_dir)

    mock_s3.download_file.assert_not_called()


def test_download_s3_prefix_rejects_cache_traversal(tmp_path: Path) -> None:
    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"Contents": [{"Key": "cache/../escape.bin"}]}
    ]
    mock_s3.get_paginator.return_value = mock_paginator

    target_dir = tmp_path / "output" / ".stage_cache"
    with pytest.raises(ValueError, match="Path traversal detected in S3 object key"):
        download_s3_prefix(mock_s3, "my-bucket", "cache/", target_dir)

    mock_s3.download_file.assert_not_called()


def test_safe_s3_dest_path_absolute_and_escaping_rejected(tmp_path: Path) -> None:
    target_dir = tmp_path / "data" / "raw"
    with pytest.raises(ValueError, match="Absolute path detected"):
        _safe_s3_dest_path(
            target_dir, "/absolute/path/file.csv", "raw//absolute/path/file.csv"
        )

    with pytest.raises(ValueError, match="Path traversal detected"):
        _safe_s3_dest_path(target_dir, "../escape.csv", "raw/../escape.csv")


def test_upload_local_tree_to_s3(tmp_path: Path) -> None:
    mock_s3 = MagicMock()
    upload_dir = tmp_path / "runs" / "run-123"
    upload_dir.mkdir(parents=True)
    (upload_dir / "manifest.json").write_text('{"status": "completed"}')
    nested = upload_dir / "data"
    nested.mkdir()
    (nested / "table.parquet").write_bytes(b"PAR1")

    count = upload_local_tree_to_s3(mock_s3, upload_dir, "my-bucket", "runs/run-123/")

    assert count == 2
    assert mock_s3.upload_file.call_count == 2


def test_batch_local_output_base_path_override(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    config_file = tmp_path / "test_config.yml"
    original_content = (
        "data_type: telegram\n"
        "content_type: forward\n"
        "year: '2019'\n"
        "output_base_path: /unwritable/system/path\n"
        "creator_relation: PRODUCED\n"
        "spreader_relation: FORWARDED_BY\n"
        "creator_node_column: source\n"
        "spreader_node_column: target\n"
        "text_node_column: target\n"
        "date_column: forwarded_date\n"
        "month: '01'\n"
        "input_path: tests/fixtures/sample.csv\n"
    )
    config_file.write_text(original_content)

    config = BatchRunnerConfig(
        config_path=str(config_file),
        command="run-all",
        s3_bucket=None,
        theme_provider="mock",
        dataset_id=None,
        workspace_dir=workspace_dir,
        skip_s3_download=True,
        skip_s3_upload=True,
        dry_run=True,
    )
    result = run_batch_job(config)
    assert result == 0

    # Verify canonical file on disk was not modified
    assert config_file.read_text() == original_content
    # Verify local output directory was created
    assert (workspace_dir / "output").exists()


def test_stage_cache_directory_consistency(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    expected_cache_dir = workspace_dir / "output" / ".stage_cache"

    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"Contents": [{"Key": "cache/v1/network/hash123/meta.json"}]}
    ]
    mock_s3.get_paginator.return_value = mock_paginator

    config = BatchRunnerConfig(
        config_path="tests/configs/test_single_month.yml",
        command="run-all",
        s3_bucket="my-bucket",
        theme_provider="mock",
        dataset_id=None,
        workspace_dir=workspace_dir,
        skip_s3_download=False,
        skip_s3_upload=True,
        dry_run=True,
    )
    run_batch_job(config, s3_client=mock_s3)

    # Download occurred for both raw and cache
    assert mock_s3.download_file.call_count == 2
    dest_paths = [Path(c[0][2]) for c in mock_s3.download_file.call_args_list]
    # Check that cache download destination was under expected_cache_dir
    assert any(expected_cache_dir in p.parents for p in dest_paths)


def test_publish_completed_run_manifest_last_ordering(tmp_path: Path) -> None:
    mock_s3 = MagicMock()
    output_root = tmp_path / "output"
    run_id = "run-uuid-456"
    run_dir = output_root / "runs" / run_id
    run_dir.mkdir(parents=True)

    # Create run artifacts and manifest
    (run_dir / "data.parquet").write_bytes(b"PAR1")
    (run_dir / "summary.json").write_text("{}")
    (run_dir / "manifest.json").write_text('{"status": "completed"}')

    # Create reports and cache
    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "index.md").write_text("# Report")

    stage_cache_dir = output_root / ".stage_cache"
    stage_cache_dir.mkdir(parents=True)
    (stage_cache_dir / "cache_meta.json").write_text("{}")

    publish_completed_run_to_s3(
        s3_client=mock_s3,
        bucket="my-bucket",
        run_dir=run_dir,
        run_id=run_id,
        output_root=output_root,
    )

    # Verify upload calls
    uploaded_keys = [c[0][2] for c in mock_s3.upload_file.call_args_list]

    # manifest.json must be the LAST upload
    assert uploaded_keys[-1] == f"runs/{run_id}/manifest.json"

    # Other artifacts, reports, and cache must have been uploaded BEFORE manifest.json
    assert f"runs/{run_id}/data.parquet" in uploaded_keys[:-1]
    assert f"runs/{run_id}/summary.json" in uploaded_keys[:-1]
    assert "reports/index.md" in uploaded_keys[:-1]
    assert "cache/cache_meta.json" in uploaded_keys[:-1]


def test_publish_fails_before_manifest_on_artifact_failure(tmp_path: Path) -> None:
    mock_s3 = MagicMock()
    output_root = tmp_path / "output"
    run_id = "run-uuid-789"
    run_dir = output_root / "runs" / run_id
    run_dir.mkdir(parents=True)

    (run_dir / "data.parquet").write_bytes(b"PAR1")
    (run_dir / "manifest.json").write_text('{"status": "completed"}')

    # Simulate network error on first artifact upload
    mock_s3.upload_file.side_effect = IOError("S3 connection reset")

    with pytest.raises(IOError, match="S3 connection reset"):
        publish_completed_run_to_s3(
            s3_client=mock_s3,
            bucket="my-bucket",
            run_dir=run_dir,
            run_id=run_id,
            output_root=output_root,
        )

    # Verify manifest was NEVER uploaded
    uploaded_keys = [c[0][2] for c in mock_s3.upload_file.call_args_list]
    assert f"runs/{run_id}/manifest.json" not in uploaded_keys


def test_run_batch_job_manifest_status_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = BatchRunnerConfig(
        config_path="tests/configs/test_single_month.yml",
        command="run-all",
        s3_bucket="my-bucket",
        theme_provider="mock",
        dataset_id=None,
        workspace_dir=tmp_path,
        skip_s3_download=True,
        skip_s3_upload=True,
        dry_run=False,
    )

    mock_result = MagicMock()
    mock_result.context.pipeline_run_id = "test-run-failed"
    workspace_output_dir = (tmp_path / "output").resolve()
    mock_result.context.output_root = str(workspace_output_dir)

    run_dir = workspace_output_dir / "runs" / "test-run-failed"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"status": "failed", "failure_stage": "topics"})
    )

    from src.orchestration import composition_flow

    monkeypatch.setattr(
        composition_flow, "run_monthly_analysis_flow", lambda **kwargs: mock_result
    )

    with pytest.raises(RuntimeError, match="status is 'failed'"):
        run_batch_job(config)
