import json
from pathlib import Path

import pandas as pd
import pytest

from src.artifacts import (
    ArtifactCategory,
    ArtifactRecord,
    RunStatus,
    complete_run_bundle,
    fail_run_bundle,
    initialize_run_bundle,
    load_run_manifest,
    run_root_path,
    validate_run_manifest,
)
from src.orchestration.hashing import hash_file
from src.orchestration.models import (
    ArtifactReference,
    DatasetIdentity,
    PipelineRunContext,
    ValidatedRunConfiguration,
)


def _context(tmp_path: Path) -> PipelineRunContext:
    dataset = tmp_path / "input.csv"
    dataset.write_text("source,target,relation\n", encoding="utf-8")
    identity = DatasetIdentity(
        dataset_id="sample",
        path=str(dataset),
        sha256=hash_file(str(dataset)),
        platform="twitter",
        identity_source="computed",
    )
    return PipelineRunContext.create(
        pipeline_run_id="run-123",
        git_commit="abc123",
        config_digest="digest-1",
        output_root=str(tmp_path / "artifacts"),
        datasets=[identity],
        prefect_flow_run_id="prefect-1",
    )


def _config(tmp_path: Path) -> ValidatedRunConfiguration:
    return ValidatedRunConfiguration(
        config_digest="digest-1",
        output_root=str(tmp_path / "artifacts"),
        raw_config={
            "output_base_path": str(tmp_path / "artifacts"),
            "input_path": str(tmp_path / "input.csv"),
            "data_type": "twitter",
            "content_type": "reply",
            "month": "march",
            "year": "2017",
        },
    )


def _reference(path: Path, key: str, media_type: str = "text/csv") -> ArtifactReference:
    rows = len(pd.read_csv(path)) if path.suffix == ".csv" else None
    return ArtifactReference(
        path=str(path),
        sha256=hash_file(str(path)),
        media_type=media_type,
        asset_key=key,
        row_count=rows,
        byte_size=path.stat().st_size,
    )


def test_artifact_record_rejects_absolute_and_parent_paths():
    kwargs = {
        "key": "network_data",
        "category": ArtifactCategory.DATA,
        "media_type": "text/csv",
        "schema_version": "1",
        "sha256": "a" * 64,
    }
    with pytest.raises(ValueError, match="relative path"):
        ArtifactRecord(path="/tmp/output.csv", **kwargs)
    with pytest.raises(ValueError, match="relative path"):
        ArtifactRecord(path="../output.csv", **kwargs)
    with pytest.raises(ValueError, match="relative path"):
        ArtifactRecord(path=r"C:\temp\output.csv", **kwargs)


def test_complete_run_bundle_publishes_classified_artifacts_and_preserves_legacy(
    tmp_path,
):
    context = _context(tmp_path)
    config = _config(tmp_path)
    manifest_path = initialize_run_bundle(
        context=context,
        config=config,
        started_at="2026-01-01T00:00:00+00:00",
        mlflow_run_id="mlflow-1",
    )
    root = run_root_path(context.output_root, context.pipeline_run_id)
    running = load_run_manifest(root)
    assert running.status is RunStatus.RUNNING
    assert running.pipeline["completed_at"] is None

    network_path = root / "twitter/network_data/reply/march2017.csv"
    network_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "unique_id": ["m1"],
            "from_id": ["u1"],
            "forwarder_id": ["u2"],
            "text": ["hello"],
            "created_at": ["2017-03-01"],
        }
    ).to_csv(network_path, index=False)

    topic_path = (
        root
        / "twitter/_intermediate/topic_inputs/reply/march_2017"
        / "absolute_community_messages.csv"
    )
    topic_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "community_number": [1],
            "messages": [["hello"]],
            "messages_ids": [["m1"]],
            "total_messages": [1],
        }
    ).to_csv(topic_path, index=False)

    original_network = network_path.read_bytes()
    original_topic = topic_path.read_bytes()
    manifest = complete_run_bundle(
        context=context,
        config=config,
        artifacts=[
            _reference(network_path, "network_data"),
            _reference(topic_path, "topic_absolute_messages"),
        ],
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:01:00+00:00",
        mlflow_run_id="mlflow-1",
    )

    assert manifest.status is RunStatus.COMPLETED
    assert manifest_path == root / "manifest.json"
    assert (root / "resolved_config.yaml").is_file()
    assert (root / "inputs/datasets.json").is_file()
    assert network_path.read_bytes() == original_network
    assert topic_path.read_bytes() == original_topic

    records = {record.key: record for record in manifest.artifacts}
    network_record = records["network_data"]
    topic_record = records["topic_absolute_messages"]
    assert network_record.category is ArtifactCategory.DATA
    assert network_record.path == "data/network/march2017.csv"
    assert topic_record.category is ArtifactCategory.INTERMEDIATE
    assert topic_record.path.endswith(
        "intermediate/topic_inputs/reply/march_2017/absolute_community_messages.csv"
    )
    assert (root / network_record.path).read_bytes() == original_network
    assert (root / topic_record.path).read_bytes() == original_topic
    assert validate_run_manifest(root).status is RunStatus.COMPLETED
    assert not list(root.rglob("*.tmp"))

    datasets = json.loads((root / "inputs/datasets.json").read_text(encoding="utf-8"))
    assert datasets["datasets"][0]["source_name"] == "input.csv"
    assert str(tmp_path) not in json.dumps(datasets)


def test_validate_run_manifest_detects_artifact_tampering(tmp_path):
    context = _context(tmp_path)
    config = _config(tmp_path)
    initialize_run_bundle(context=context, config=config, started_at="start")
    root = run_root_path(context.output_root, context.pipeline_run_id)
    network_path = root / "twitter/network_data/reply/march2017.csv"
    network_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "unique_id": ["m1"],
            "from_id": ["u1"],
            "forwarder_id": ["u2"],
            "text": ["hello"],
            "created_at": ["2017-03-01"],
        }
    ).to_csv(network_path, index=False)
    manifest = complete_run_bundle(
        context=context,
        config=config,
        artifacts=[_reference(network_path, "network_data")],
        started_at="start",
        completed_at="end",
    )
    canonical = root / manifest.artifacts[0].path
    canonical.write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="byte size mismatch|checksum mismatch"):
        validate_run_manifest(root)


def test_fail_run_bundle_never_marks_failed_run_completed(tmp_path):
    context = _context(tmp_path)
    config = _config(tmp_path)
    initialize_run_bundle(context=context, config=config, started_at="start")

    manifest = fail_run_bundle(
        context=context,
        config=config,
        started_at="start",
        completed_at="end",
        failure_stage="topic",
        failure_type="ValueError",
        failure_category="SCHEMA_VIOLATION",
    )

    assert manifest.status is RunStatus.FAILED
    assert manifest.failure == {
        "stage": "topic",
        "type": "ValueError",
        "category": "SCHEMA_VIOLATION",
    }
    loaded = load_run_manifest(
        run_root_path(context.output_root, context.pipeline_run_id)
    )
    assert loaded.status is RunStatus.FAILED
    assert loaded.pipeline["completed_at"] == "end"


def test_fail_run_bundle_survives_invalid_partial_artifact(tmp_path):
    context = _context(tmp_path)
    config = _config(tmp_path)
    initialize_run_bundle(context=context, config=config, started_at="start")
    root = run_root_path(context.output_root, context.pipeline_run_id)
    partial = root / "partial.csv"
    partial.write_text("wrong\nvalue\n", encoding="utf-8")
    invalid = ArtifactReference(
        path=str(partial),
        sha256="a" * 64,
        media_type="text/csv",
        asset_key="network_data",
        byte_size=partial.stat().st_size,
        row_count=1,
    )

    manifest = fail_run_bundle(
        context=context,
        config=config,
        started_at="start",
        completed_at="end",
        failure_stage="network_community",
        failure_type="ValueError",
        failure_category="SCHEMA_VIOLATION",
        artifacts=[invalid],
    )

    assert manifest.status is RunStatus.FAILED
    assert manifest.artifacts == ()


def test_run_root_rejects_path_traversal(tmp_path):
    for unsafe in ("../escape", "nested/run", r"nested\\run", ".", "..", ""):
        with pytest.raises(ValueError, match="run_id"):
            run_root_path(tmp_path, unsafe)


def test_terminal_manifest_cannot_be_reinitialized_or_reclassified(tmp_path):
    context = _context(tmp_path)
    config = _config(tmp_path)
    initialize_run_bundle(context=context, config=config, started_at="start")
    fail_run_bundle(
        context=context,
        config=config,
        started_at="start",
        completed_at="end",
        failure_stage="topic",
        failure_type="ValueError",
        failure_category="SCHEMA_VIOLATION",
    )

    with pytest.raises(ValueError, match="already exists"):
        initialize_run_bundle(context=context, config=config, started_at="later")
    with pytest.raises(ValueError, match="terminal"):
        complete_run_bundle(
            context=context,
            config=config,
            artifacts=[],
            started_at="start",
            completed_at="later",
        )


def test_complete_run_bundle_rejects_inconsistent_source_metadata(tmp_path):
    context = _context(tmp_path)
    config = _config(tmp_path)
    initialize_run_bundle(context=context, config=config, started_at="start")
    root = run_root_path(context.output_root, context.pipeline_run_id)
    network_path = root / "twitter/network_data/reply/march2017.csv"
    network_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "unique_id": ["m1"],
            "from_id": ["u1"],
            "forwarder_id": ["u2"],
            "text": ["hello"],
            "created_at": ["2017-03-01"],
        }
    ).to_csv(network_path, index=False)
    inconsistent = ArtifactReference(
        path=str(network_path),
        sha256=hash_file(str(network_path)),
        media_type="text/csv",
        asset_key="network_data",
        byte_size=network_path.stat().st_size,
        row_count=2,
    )

    with pytest.raises(ValueError, match="source artifact row count mismatch"):
        complete_run_bundle(
            context=context,
            config=config,
            artifacts=[inconsistent],
            started_at="start",
            completed_at="end",
        )

    assert load_run_manifest(root).status is RunStatus.RUNNING


def test_complete_run_bundle_rejects_known_csv_schema_violation(tmp_path):
    context = _context(tmp_path)
    config = _config(tmp_path)
    initialize_run_bundle(context=context, config=config, started_at="start")
    root = run_root_path(context.output_root, context.pipeline_run_id)
    invalid = root / "twitter/network_data/reply/march2017.csv"
    invalid.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"unexpected": [1]}).to_csv(invalid, index=False)

    with pytest.raises(ValueError, match="schema mismatch"):
        complete_run_bundle(
            context=context,
            config=config,
            artifacts=[_reference(invalid, "network_data")],
            started_at="start",
            completed_at="end",
        )

    assert load_run_manifest(root).status is RunStatus.RUNNING


def test_complete_run_bundle_classifies_theme_data_and_report_figures(tmp_path):
    from src.reporting.output_contract import get_required_columns_by_artifact

    context = _context(tmp_path)
    config = _config(tmp_path)
    initialize_run_bundle(context=context, config=config, started_at="start")
    root = run_root_path(context.output_root, context.pipeline_run_id)

    schemas = get_required_columns_by_artifact()
    themes = root / "theme-output/march_2017_with_themes.csv"
    transitions = root / "theme-output/community_transition.csv"
    figure = root / "theme-output/sankey/community_transition.html"
    provider_summary = root / "theme-output/provider_run_summary.json"
    themes.parent.mkdir(parents=True, exist_ok=True)
    figure.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=schemas["themed_output"]).to_csv(themes, index=False)
    pd.DataFrame(columns=schemas["community_transition"]).to_csv(
        transitions, index=False
    )
    figure.write_text("<html></html>\n", encoding="utf-8")
    provider_summary.write_text('{"schema_version": "1"}\n', encoding="utf-8")

    manifest = complete_run_bundle(
        context=context,
        config=config,
        artifacts=[
            _reference(themes, "themes_march"),
            _reference(transitions, "community_transitions"),
            _reference(
                figure,
                "visualization_sankey_community_transition.html",
                media_type="text/html",
            ),
            _reference(
                provider_summary,
                "provider_run_summary",
                media_type="application/json",
            ),
        ],
        started_at="start",
        completed_at="end",
    )

    records = {record.key: record for record in manifest.artifacts}
    assert records["themes_march"].category is ArtifactCategory.DATA
    assert records["themes_march"].path.startswith("data/themes/monthly/")
    assert records["community_transitions"].path.startswith("data/themes/")
    visualization = records["visualization_sankey_community_transition.html"]
    assert visualization.category is ArtifactCategory.REPORT
    assert visualization.path == "reports/figures/sankey/community_transition.html"
    assert records["provider_run_summary"].path == (
        "data/themes/provider_run_summary.json"
    )
    assert validate_run_manifest(root) == manifest
