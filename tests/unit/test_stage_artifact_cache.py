import json
from pathlib import Path

from src.artifacts.run_manifest import run_root_path
from src.orchestration.hashing import hash_file
from src.orchestration.models import ArtifactReference, PipelineRunContext
from src.orchestration.stage_cache import (
    artifact_reuse_enabled,
    restore_stage_artifacts,
    stage_cache_root,
    store_stage_artifacts,
)


def _context(tmp_path: Path, run_id: str) -> PipelineRunContext:
    return PipelineRunContext.create(
        pipeline_run_id=run_id,
        git_commit="abc123",
        config_digest="digest",
        output_root=str(tmp_path),
        datasets=[],
    )


def _artifact(
    context: PipelineRunContext, relative: str, content: bytes
) -> ArtifactReference:
    path = run_root_path(context.output_root, context.pipeline_run_id) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return ArtifactReference(
        path=str(path),
        sha256=hash_file(str(path)),
        media_type="application/octet-stream",
        asset_key="stage_output",
        byte_size=len(content),
    )


def test_stage_cache_restores_artifact_into_new_run_root(tmp_path):
    key = "a" * 64
    first = _context(tmp_path, "run-a")
    artifact = _artifact(first, "twitter/LDA/scores/reply/01.parquet", b"cached-bytes")

    entry = store_stage_artifacts(
        context=first,
        stage="topic_model",
        cache_key=key,
        artifacts=[artifact],
    )
    assert entry.is_dir()

    # Mutating the original run after the immutable cache snapshot must not alter reuse.
    Path(artifact.path).write_bytes(b"changed-original")

    second = _context(tmp_path, "run-b")
    restored = restore_stage_artifacts(
        context=second,
        stage="topic_model",
        cache_key=key,
    )

    assert restored is not None
    assert len(restored) == 1
    restored_ref = restored[0]
    expected = run_root_path(tmp_path, "run-b") / "twitter/LDA/scores/reply/01.parquet"
    assert Path(restored_ref.path) == expected
    assert expected.read_bytes() == b"cached-bytes"
    assert restored_ref.sha256 == hash_file(str(expected))
    assert restored_ref.asset_key == "stage_output"


def test_stage_cache_tampering_is_a_cache_miss(tmp_path):
    key = "b" * 64
    first = _context(tmp_path, "run-a")
    artifact = _artifact(
        first, "telegram/network_data/forward/012019.parquet", b"valid"
    )
    entry = store_stage_artifacts(
        context=first,
        stage="network_community",
        cache_key=key,
        artifacts=[artifact],
    )

    manifest = json.loads((entry / "manifest.json").read_text(encoding="utf-8"))
    relative = manifest["artifacts"][0]["relative_path"]
    (entry / "files" / relative).write_bytes(b"tampered")

    second = _context(tmp_path, "run-b")
    assert (
        restore_stage_artifacts(
            context=second,
            stage="network_community",
            cache_key=key,
        )
        is None
    )
    assert not (run_root_path(tmp_path, "run-b") / relative).exists()


def test_stage_cache_manifest_contains_only_relative_artifact_paths(tmp_path):
    key = "c" * 64
    context = _context(tmp_path, "run-a")
    artifact = _artifact(context, "provider_run_summary.json", b"{}")
    entry = store_stage_artifacts(
        context=context,
        stage="theme_generation",
        cache_key=key,
        artifacts=[artifact],
    )

    payload = json.loads((entry / "manifest.json").read_text(encoding="utf-8"))
    assert payload["producer_run_id"] == "run-a"
    assert payload["artifacts"][0]["relative_path"] == "provider_run_summary.json"
    assert str(tmp_path) not in json.dumps(payload)
    assert entry.is_relative_to(stage_cache_root(tmp_path))


def test_artifact_reuse_defaults_on_and_can_be_disabled():
    assert artifact_reuse_enabled({}) is True
    assert artifact_reuse_enabled({"orchestration": {}}) is True
    assert artifact_reuse_enabled({"orchestration": {"artifact_reuse": False}}) is False
