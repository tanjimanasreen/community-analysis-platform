import pytest
import os
from pathlib import Path
from unittest.mock import patch
from src.orchestration.models import (
    DatasetIdentity,
    ArtifactReference,
    PipelineRunContext,
    ValidatedRunConfiguration,
)
from src.orchestration.tasks import (
    validate_run_configuration_task,
    resolve_dataset_identity_task,
    run_monthly_network_community_phase_task,
)
from src.orchestration.retry_policy import PipelineError


def test_validate_run_configuration_task():
    config = {
        "output_base_path": "/mock/out",
        "input_path": "/mock/in.csv",
        "data_type": "twitter",
        "content_type": "reply",
        "month": "march",
        "year": "2017",
        "creator_relation": "REPLIED_TO",
        "spreader_relation": "REPLIED_BY",
        "creator_node_column": "target",
        "spreader_node_column": "target",
        "text_node_column": "source",
        "date_column": "created_at",
    }
    val_config = validate_run_configuration_task.fn(config)
    assert val_config.output_root == "/mock/out"
    assert "data_type" in val_config.raw_config
    assert val_config.config_digest is not None


def test_validate_run_configuration_rejects_mismatched_reply_mapping():
    config = {
        "output_base_path": "/mock/out",
        "input_path": "/mock/in.csv",
        "data_type": "twitter",
        "content_type": "reply",
        "month": "march",
        "year": "2017",
        "creator_relation": "TWEETED",
        "spreader_relation": "RETWEETED_BY",
        "creator_node_column": "source",
        "spreader_node_column": "target",
        "text_node_column": "target",
        "date_column": "created_at",
    }

    with pytest.raises(
        PipelineError, match="Invalid analytical mapping for twitter/reply"
    ):
        validate_run_configuration_task.fn(config)


def test_validate_run_configuration_rejects_ldamulticore_auto_alpha():
    config = {
        "output_base_path": "/mock/out",
        "input_path": "/mock/in.csv",
        "data_type": "twitter",
        "content_type": "reply",
        "month": "march",
        "year": "2017",
        "creator_relation": "REPLIED_TO",
        "spreader_relation": "REPLIED_BY",
        "creator_node_column": "target",
        "spreader_node_column": "target",
        "text_node_column": "source",
        "date_column": "created_at",
        "lda": {"implementation": "ldamulticore", "alpha": "auto"},
    }

    with pytest.raises(PipelineError, match="does not support lda.alpha='auto'"):
        validate_run_configuration_task.fn(config)


def test_validate_run_configuration_equivalence():
    from src.config.loader import load_config

    config = {
        "output_base_path": "/mock/out",
        "input_path": "/mock/in.csv",
        "data_type": "twitter",
        "content_type": "reply",
        "month": "march",
        "year": "2017",
        "creator_relation": "REPLIED_TO",
        "spreader_relation": "REPLIED_BY",
        "creator_node_column": "target",
        "spreader_node_column": "target",
        "text_node_column": "source",
        "date_column": "created_at",
    }

    val_config = validate_run_configuration_task.fn(config)

    assert val_config.raw_config["data_type"] == "twitter"
    assert val_config.raw_config["month"] == "march"
    assert val_config.output_root == "/mock/out"


def test_validate_run_configuration_recursively_removes_secrets():
    config = {
        "output_base_path": "/mock/out",
        "input_path": "/mock/in.csv",
        "data_type": "twitter",
        "content_type": "reply",
        "month": "march",
        "year": "2017",
        "creator_relation": "REPLIED_TO",
        "spreader_relation": "REPLIED_BY",
        "creator_node_column": "target",
        "spreader_node_column": "target",
        "text_node_column": "source",
        "date_column": "created_at",
        "OPENAI_API_KEY": "secret-a",
        "provider": {
            "model": "mock-model",
            "max_tokens": 512,
            "credentials": {
                "token": "secret-b",
                "password": "secret-c",
            },
        },
    }

    validated = validate_run_configuration_task.fn(config)

    assert "OPENAI_API_KEY" not in validated.raw_config
    assert validated.raw_config["provider"] == {
        "model": "mock-model",
        "max_tokens": 512,
    }
    serialized = repr(validated.raw_config)
    assert "secret-a" not in serialized
    assert "secret-b" not in serialized
    assert "secret-c" not in serialized


def test_validate_run_configuration_task_missing_output_dir():
    config = {"other": "val"}
    with pytest.raises(PipelineError, match="Missing required config keys"):
        validate_run_configuration_task.fn(config)


def test_resolve_dataset_identity_task_missing_file():
    with pytest.raises(PipelineError, match="not found"):
        resolve_dataset_identity_task.fn(path="/fake/path.csv", dataset_id="test")


def test_known_hash_skips_file_hashing(monkeypatch, tmp_path):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("hash_file must not be called")

    monkeypatch.setattr(
        "src.orchestration.tasks.hash_file",
        fail_if_called,
    )

    dataset_path = tmp_path / "large-placeholder.csv"
    dataset_path.touch()

    identity = resolve_dataset_identity_task.fn(
        path=str(dataset_path),
        dataset_id="retweet-february-2017",
        known_sha256="a" * 64,
        verify_file_hash=False,
    )

    assert identity.sha256 == "a" * 64
    assert identity.identity_source == "supplied"


def test_resolve_dataset_identity_task_known_hash(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("dummy")
    ident = resolve_dataset_identity_task.fn(
        path=str(f), dataset_id="test", known_sha256="a" * 64
    )
    assert ident.sha256 == "a" * 64
    assert ident.identity_source == "supplied"


def test_network_task_delegates_raw_telegram_normalization_to_shared_pipeline(
    tmp_path,
):
    dataset_path = tmp_path / "telegram.csv"
    dataset_path.write_text(
        "source,target,relation\n"
        "creator,message,PRODUCED\n"
        "message,spreader,FORWARDED_BY\n",
        encoding="utf-8",
    )
    identity = DatasetIdentity(
        dataset_id="telegram-test",
        path=str(dataset_path),
        sha256="a" * 64,
        platform="telegram",
        identity_source="computed",
    )
    config = ValidatedRunConfiguration(
        config_digest="123",
        output_root=str(tmp_path),
        raw_config={
            "data_type": "telegram",
            "content_type": "forward",
            "month": "09",
            "year": "2019",
            "creator_relation": "PRODUCED",
            "spreader_relation": "FORWARDED_BY",
            "creator_node_column": "source",
            "spreader_node_column": "target",
            "text_node_column": "target",
            "date_column": "forwarded_date",
        },
    )
    context = PipelineRunContext.create(
        pipeline_run_id="run-telegram",
        git_commit="abc",
        config_digest="123",
        output_root=str(tmp_path),
        datasets=[],
    )

    with patch(
        "src.pipelines.social_network_pipeline.run_network_community_pipeline"
    ) as mock_run:
        with pytest.raises(
            PipelineError, match="expected output artifact not found after execution"
        ):
            run_monthly_network_community_phase_task.fn(
                dataset_identity=identity, config=config, context=context
            )

    delegated = mock_run.call_args.kwargs["df"]
    assert list(delegated.columns) == ["source", "target", "relation"]
    assert "from_id" not in delegated.columns
    assert "forwarder_id" not in delegated.columns


def test_run_monthly_network_community_phase_task_missing_required(tmp_path):
    foo_path = tmp_path / "foo.csv"
    foo_path.write_text("dummy,csv\n1,2\n")
    identity = DatasetIdentity(
        dataset_id="test",
        path=str(foo_path),
        sha256="a" * 64,
        platform="twitter",
        identity_source="computed",
    )
    config = ValidatedRunConfiguration(
        config_digest="123",
        output_root=str(tmp_path),
        raw_config={
            "data_type": "twitter",
            "content_type": "reply",
            "month": "march",
            "year": "2017",
        },
    )
    context = PipelineRunContext.create(
        pipeline_run_id="run-1",
        git_commit="abc",
        config_digest="123",
        output_root=str(tmp_path),
        datasets=[],
    )

    with patch(
        "src.pipelines.social_network_pipeline.run_network_community_pipeline"
    ) as mock_run:
        # Mock doesn't create any files
        with pytest.raises(
            PipelineError, match="expected output artifact not found after execution"
        ):
            run_monthly_network_community_phase_task.fn(
                dataset_identity=identity, config=config, context=context
            )


def _assert_no_large_objects(obj):
    import pandas as pd
    import networkx as nx
    from pydantic import BaseModel

    if isinstance(obj, (pd.DataFrame, nx.Graph, nx.DiGraph)):
        raise AssertionError(f"Found large object: {type(obj)}")
    if isinstance(obj, (str, int, float, bool, type(None))):
        return
    if isinstance(obj, bytes) and len(obj) > 1000:
        raise AssertionError(f"Found large bytes object: {len(obj)}")

    if isinstance(obj, list):
        for item in obj:
            _assert_no_large_objects(item)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_large_objects(k)
            _assert_no_large_objects(v)
    elif isinstance(obj, BaseModel):
        _assert_no_large_objects(obj.model_dump())
    elif hasattr(obj, "__dict__"):
        _assert_no_large_objects(obj.__dict__)


def test_no_large_objects_in_artifact_reference():
    ref = ArtifactReference(
        path="/tmp/test.csv",
        sha256="a" * 64,
        media_type="text/csv",
        byte_size=123,
        asset_key="network_data",
    )
    _assert_no_large_objects(ref)


def test_resolve_dataset_identity_task_computed_hash(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("dummy")
    ident = resolve_dataset_identity_task.fn(path=str(f), dataset_id="test")
    assert ident.sha256 != "a" * 64
    assert len(ident.sha256) == 64
    assert ident.identity_source == "computed"


def test_resolve_dataset_identity_task_malformed_hash(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("dummy")
    with pytest.raises(PipelineError, match="Malformed SHA-256 hash"):
        resolve_dataset_identity_task.fn(
            path=str(f), dataset_id="test", known_sha256="short"
        )


def test_resolve_dataset_identity_task_verify_hash_success(tmp_path):
    from src.orchestration.hashing import hash_file

    f = tmp_path / "data.csv"
    f.write_text("dummy")
    correct_hash = hash_file(str(f))
    ident = resolve_dataset_identity_task.fn(
        path=str(f), dataset_id="test", known_sha256=correct_hash, verify_file_hash=True
    )
    assert ident.sha256 == correct_hash
    assert ident.identity_source == "verified"


def test_resolve_dataset_identity_task_verify_hash_mismatch(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("dummy")
    with pytest.raises(PipelineError, match="Dataset hash mismatch"):
        resolve_dataset_identity_task.fn(
            path=str(f), dataset_id="test", known_sha256="a" * 64, verify_file_hash=True
        )


def test_resolve_dataset_identity_captures_adjacent_dvc_pointer(tmp_path):
    dataset = tmp_path / "dataset.csv"
    dataset.write_text("value\n1\n", encoding="utf-8")
    pointer = Path(f"{dataset}.dvc")
    pointer.write_text(
        "outs:\n- md5: abcdef1234567890\n  size: 8\n  path: dataset.csv\n",
        encoding="utf-8",
    )

    identity = resolve_dataset_identity_task.fn(
        path=str(dataset),
        dataset_id="dataset-1",
        dvc_revision="git-revision-1",
    )

    assert identity.dvc_pointer == str(pointer.resolve())
    assert identity.dvc_content_hash == "abcdef1234567890"
    assert identity.dvc_revision == "git-revision-1"
