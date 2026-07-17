import hashlib
from pathlib import Path

from src.orchestration.models import (
    ArtifactReference,
    DatasetIdentity,
    PipelineRunContext,
    ThemeInputBundle,
    ThemeOutputBundle,
    TopicOutputBundle,
)
from src.tracking.summaries import (
    build_artifact_manifest,
    build_lineage_summary,
    theme_metrics,
    topic_metrics,
)


def _ref(path: Path, asset_key: str) -> ArtifactReference:
    return ArtifactReference(
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        media_type="text/csv",
        asset_key=asset_key,
        byte_size=path.stat().st_size,
        row_count=1,
    )


def test_summaries_use_artifact_references_not_file_contents(tmp_path):
    output_root = tmp_path / "output"
    run_root = output_root / "runs" / "run-1"
    run_root.mkdir(parents=True)
    lda = run_root / "lda.csv"
    matched = run_root / "matched.csv"
    theme = run_root / "theme.csv"
    for path in (lda, matched, theme):
        path.write_text("x\n1\n", encoding="utf-8")
    topic = TopicOutputBundle(
        lda_scores=_ref(lda, "lda_scores"),
        matched_communities_topics=_ref(matched, "matched_communities_topics"),
        partial_matched_communities_topics=None,
        theme_inputs=(),
    )
    theme_input = ThemeInputBundle(
        monthly_topic_outputs={"march": topic.matched_communities_topics}
    )
    theme_output = ThemeOutputBundle(
        themes=(_ref(theme, "themes_march"),),
        community_transitions=None,
        visualizations=(),
        provider_run_summary=None,
    )
    topic_summary = topic_metrics(topic, 1.25)
    assert topic_summary["artifact_count"] == 2
    assert topic_summary["matched_community_count"] == 1
    theme_summary = theme_metrics(theme_input, theme_output, 2.5)
    assert theme_summary["theme_input_count"] == 1
    assert theme_summary["theme_output_count"] == 1
    assert theme_summary["theme_generation_success_count"] == 1

    context = PipelineRunContext.create(
        pipeline_run_id="run-1",
        git_commit="abc",
        config_digest="digest",
        output_root=str(output_root),
        datasets=[],
    )
    manifest = build_artifact_manifest(
        context,
        [
            topic.lda_scores,
            topic.matched_communities_topics,
            theme_output.themes[0],
        ],
    )
    assert {item["stage"] for item in manifest["artifacts"]} == {
        "topic",
        "theme",
    }
    assert all(
        not item["relative_path"].startswith("/") for item in manifest["artifacts"]
    )


def test_lineage_summary_is_relative_and_includes_dvc_metadata(tmp_path):
    dataset = tmp_path / "private" / "dataset.csv"
    dataset.parent.mkdir()
    dataset.write_text("x\n1\n", encoding="utf-8")
    pointer = Path(f"{dataset}.dvc")
    pointer.write_text("outs:\n- md5: abc123\n", encoding="utf-8")
    identity = DatasetIdentity(
        dataset_id="dataset-1",
        path=str(dataset),
        sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),
        dvc_pointer=str(pointer),
        dvc_content_hash="abc123",
        dvc_revision="revision-1",
    )
    context = PipelineRunContext.create(
        pipeline_run_id="run-1",
        git_commit="abc",
        config_digest="digest",
        output_root=str(tmp_path / "output"),
        datasets=[identity],
        dvc_revision="revision-1",
    )
    summary = build_lineage_summary(
        context,
        project_root=tmp_path,
        git_branch="test",
    )
    entry = summary["datasets"][0]
    assert entry == {
        "dataset_id": "dataset-1",
        "dataset_relative_path": "private/dataset.csv",
        "dataset_sha256": identity.sha256,
        "dataset_byte_size": dataset.stat().st_size,
        "dvc_file_relative_path": "private/dataset.csv.dvc",
        "dvc_content_hash": "abc123",
        "dvc_revision": "revision-1",
    }
    assert str(tmp_path) not in repr(summary)
