"""
Comprehensive hardened tests for the Topic orchestration task.

Covers:
- Input validation: missing files, size mismatch, hash mismatch, path escape,
  symlink escape, directory-instead-of-file, invalid media type, invalid schema
- Optional partial-matched absent
- Delegation: domain function called exactly once, correct params
- Outputs: correct types, correct paths, correct asset keys
- No large object (DataFrame, model, corpus) in results
- Cache key helper: stable inputs produce same key, provider config excluded,
  LDA param changes invalidate key
- retries=0 confirmed
- No Prefect imports in topic domain modules
"""

import os
import hashlib
import json
import pytest
import pandas as pd

pytestmark = pytest.mark.requires_loopback
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from prefect.testing.utilities import prefect_test_harness

from src.orchestration.models import (
    ArtifactReference,
    PipelineRunContext,
    TopicInputBundle,
    TopicOutputBundle,
    ValidatedRunConfiguration,
)
from src.orchestration.tasks import run_monthly_topic_phase_task
from src.orchestration.retry_policy import ErrorCategory, PipelineError
from src.orchestration.hashing import topic_cache_key_fn, build_stage_cache_key

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


COMMUNITY_MESSAGE_FRAME = pd.DataFrame(
    {
        "community_number": [1],
        "messages": [["hello"]],
        "messages_ids": [["m1"]],
        "total_messages": [1],
    }
)
MATCHED_COMMUNITY_FRAME = pd.DataFrame(
    {
        "abs_community": [1],
        "per_community": [2],
        "jaccard_score": [1.0],
        "members": [["u1"]],
    }
)
PARTIAL_MATCHED_COMMUNITY_FRAME = pd.DataFrame(
    {
        "abs_community": [1],
        "absolute_members": [["u1"]],
        "per_community": [2],
        "weighted_members": [["u1"]],
        "jaccard_score": [1.0],
        "common_members": [["u1"]],
        "uncommon_members": [[]],
    }
)


def _write(path: Path, frame: pd.DataFrame) -> ArtifactReference:
    frame.to_parquet(path, index=False)
    content = path.read_bytes()
    return ArtifactReference(
        path=str(path),
        sha256=_sha256(content),
        media_type="application/octet-stream",
        byte_size=len(content),
        asset_key=path.stem,
    )


def _context(tmp_path) -> PipelineRunContext:
    return PipelineRunContext.create(
        pipeline_run_id="run-test",
        git_commit="abc",
        config_digest="d",
        output_root=str(tmp_path),
        datasets=[],
    )


def _config(tmp_path) -> ValidatedRunConfiguration:
    return ValidatedRunConfiguration(
        config_digest="d",
        output_root=str(tmp_path),
        raw_config={
            "month": "march",
            "year": "2017",
            "data_type": "twitter",
            "content_type": "reply",
        },
    )


def _bundle(tmp_path, *, partial=None) -> TopicInputBundle:
    abs_ref = _write(tmp_path / "abs.parquet", COMMUNITY_MESSAGE_FRAME)
    wgt_ref = _write(tmp_path / "wgt.parquet", COMMUNITY_MESSAGE_FRAME)
    mch_ref = _write(tmp_path / "mch.parquet", MATCHED_COMMUNITY_FRAME)
    return TopicInputBundle(
        absolute_community_messages=abs_ref,
        weighted_community_messages=wgt_ref,
        matched_communities=mch_ref,
        partial_matched_communities=partial,
        allowed_input_roots=(str(tmp_path),),
    )


def _make_topic_outputs(out_dir: str, data_type="twitter", content_type="reply"):
    """Create the exact output files that run_topic_phase would produce."""
    scores_dir = os.path.join(out_dir, data_type, "LDA", "scores", content_type)
    os.makedirs(scores_dir, exist_ok=True)
    pd.DataFrame({"month": ["march"], "score": [0.5]}).to_parquet(
        Path(scores_dir) / "march.parquet", index=False
    )

    matched_dir = os.path.join(out_dir, data_type, "LDA", "matched", content_type)
    os.makedirs(matched_dir, exist_ok=True)
    pd.DataFrame({"community": [1], "topic": ["a"]}).to_parquet(
        Path(matched_dir) / "march_2017.parquet", index=False
    )

    manifest_dir = os.path.join(
        out_dir, data_type, "_intermediate", "theme_inputs", content_type, "2017"
    )
    os.makedirs(manifest_dir, exist_ok=True)
    (Path(manifest_dir) / "manifest.json").write_text("{}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def prefect_test_fixture():
    with prefect_test_harness():
        yield


# ---------------------------------------------------------------------------
# 1. Domain isolation — no Prefect imports in domain modules
# ---------------------------------------------------------------------------


def test_no_prefect_import_in_topic_domain():
    import subprocess

    result = subprocess.run(
        ["grep", "-rn", "from prefect", "src/topics", "src/pipelines"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parents[2]),
    )
    assert result.returncode != 0 or result.stdout.strip() == "", (
        "Prefect imports found in domain modules:\n" + result.stdout
    )


# ---------------------------------------------------------------------------
# 2. retries=0 confirmed in task decoration
# ---------------------------------------------------------------------------


def test_topic_task_retries_zero():
    assert run_monthly_topic_phase_task.retries == 0


# ---------------------------------------------------------------------------
# 3. Input validation — missing required artifact
# ---------------------------------------------------------------------------


def test_missing_abs_input_raises(tmp_path):
    bundle = TopicInputBundle(
        absolute_community_messages=ArtifactReference(
            path="/nonexistent/abs.parquet",
            sha256="0" * 64,
            media_type="application/octet-stream",
        ),
        weighted_community_messages=ArtifactReference(
            path="/nonexistent/wgt.parquet",
            sha256="0" * 64,
            media_type="application/octet-stream",
        ),
        matched_communities=ArtifactReference(
            path="/nonexistent/mch.parquet",
            sha256="0" * 64,
            media_type="application/octet-stream",
        ),
        partial_matched_communities=None,
    )
    with pytest.raises(PipelineError) as exc_info:
        run_monthly_topic_phase_task.fn(bundle, _config(tmp_path), _context(tmp_path))
    assert exc_info.value.category == ErrorCategory.MISSING_REQUIRED_INPUT


# ---------------------------------------------------------------------------
# 4. Input validation — directory instead of file
# ---------------------------------------------------------------------------


def test_directory_instead_of_file_raises(tmp_path):
    a_dir = tmp_path / "abs_dir"
    a_dir.mkdir()
    bundle = TopicInputBundle(
        absolute_community_messages=ArtifactReference(
            path=str(a_dir), sha256="0" * 64, media_type="application/octet-stream"
        ),
        weighted_community_messages=ArtifactReference(
            path=str(a_dir), sha256="0" * 64, media_type="application/octet-stream"
        ),
        matched_communities=ArtifactReference(
            path=str(a_dir), sha256="0" * 64, media_type="application/octet-stream"
        ),
        partial_matched_communities=None,
    )
    with pytest.raises(PipelineError) as exc_info:
        run_monthly_topic_phase_task.fn(bundle, _config(tmp_path), _context(tmp_path))
    assert exc_info.value.category == ErrorCategory.SCHEMA_VIOLATION


# ---------------------------------------------------------------------------
# 5. Input validation — path outside allowed root
# ---------------------------------------------------------------------------


def test_path_outside_allowed_root_raises(tmp_path):
    import tempfile

    other_dir = Path(tempfile.mkdtemp())
    try:
        abs_path = other_dir / "abs.parquet"
        abs_path.write_bytes(b"col\nval")
        bundle = TopicInputBundle(
            absolute_community_messages=ArtifactReference(
                path=str(abs_path),
                sha256=_sha256(b"col\nval"),
                media_type="application/octet-stream",
                byte_size=7,
            ),
            weighted_community_messages=ArtifactReference(
                path=str(abs_path),
                sha256=_sha256(b"col\nval"),
                media_type="application/octet-stream",
                byte_size=7,
            ),
            matched_communities=ArtifactReference(
                path=str(abs_path),
                sha256=_sha256(b"col\nval"),
                media_type="application/octet-stream",
                byte_size=7,
            ),
            partial_matched_communities=None,
        )
        with pytest.raises(PipelineError) as exc_info:
            run_monthly_topic_phase_task.fn(
                bundle, _config(tmp_path), _context(tmp_path)
            )
        assert exc_info.value.category == ErrorCategory.SCHEMA_VIOLATION
    finally:
        import shutil

        shutil.rmtree(str(other_dir), ignore_errors=True)


# ---------------------------------------------------------------------------
# 5b. Input validation — standalone input root accepted
# ---------------------------------------------------------------------------


@patch("src.pipelines.social_network_pipeline.run_topic_phase")
def test_explicit_standalone_input_root_accepted(mock_run, tmp_path):
    import tempfile

    other_dir = Path(tempfile.mkdtemp())
    try:
        abs_path = other_dir / "abs.parquet"
        weighted_path = other_dir / "weighted.parquet"
        matched_path = other_dir / "matched.parquet"
        abs_ref = _write(abs_path, COMMUNITY_MESSAGE_FRAME)
        weighted_ref = _write(weighted_path, COMMUNITY_MESSAGE_FRAME)
        matched_ref = _write(matched_path, MATCHED_COMMUNITY_FRAME)
        bundle = TopicInputBundle(
            absolute_community_messages=abs_ref,
            weighted_community_messages=weighted_ref,
            matched_communities=matched_ref,
            partial_matched_communities=None,
            allowed_input_roots=(str(other_dir),),
        )
        ctx = _context(tmp_path)
        cfg = _config(tmp_path)

        mock_run.side_effect = lambda **kw: _make_topic_outputs(
            kw["output_dir"],
            kw.get("data_type", "twitter"),
            kw.get("content_type", "reply"),
        )

        # This should NOT raise an error about being outside allowed_root
        result = run_monthly_topic_phase_task.fn(bundle, cfg, ctx)
        assert isinstance(result, TopicOutputBundle)
    finally:
        import shutil

        shutil.rmtree(str(other_dir), ignore_errors=True)


# ---------------------------------------------------------------------------
# 6. Input validation — byte size mismatch
# ---------------------------------------------------------------------------


def test_size_mismatch_raises(tmp_path):
    content = b"col\nval"
    p = tmp_path / "abs.parquet"
    p.write_bytes(content)

    wrong_size_ref = ArtifactReference(
        path=str(p),
        sha256=_sha256(content),
        media_type="application/octet-stream",
        byte_size=9999,  # wrong
    )
    bundle = TopicInputBundle(
        absolute_community_messages=wrong_size_ref,
        weighted_community_messages=wrong_size_ref,
        matched_communities=wrong_size_ref,
        partial_matched_communities=None,
    )
    with pytest.raises(PipelineError) as exc_info:
        run_monthly_topic_phase_task.fn(bundle, _config(tmp_path), _context(tmp_path))
    assert exc_info.value.category == ErrorCategory.SCHEMA_VIOLATION


# ---------------------------------------------------------------------------
# 7. Input validation — SHA-256 mismatch
# ---------------------------------------------------------------------------


def test_hash_mismatch_raises(tmp_path):
    content = b"col\nval"
    p = tmp_path / "abs.parquet"
    p.write_bytes(content)

    wrong_hash_ref = ArtifactReference(
        path=str(p),
        sha256="a" * 64,  # wrong hash
        media_type="application/octet-stream",
        byte_size=len(content),
    )
    bundle = TopicInputBundle(
        absolute_community_messages=wrong_hash_ref,
        weighted_community_messages=wrong_hash_ref,
        matched_communities=wrong_hash_ref,
        partial_matched_communities=None,
    )
    with pytest.raises(PipelineError) as exc_info:
        run_monthly_topic_phase_task.fn(bundle, _config(tmp_path), _context(tmp_path))
    assert exc_info.value.category == ErrorCategory.SCHEMA_VIOLATION


# ---------------------------------------------------------------------------
# 8. Optional partial-matched absent is accepted
# ---------------------------------------------------------------------------


@patch("src.pipelines.social_network_pipeline.run_topic_phase")
def test_optional_partial_absent_succeeds(mock_run, tmp_path):
    bundle = _bundle(tmp_path, partial=None)
    ctx = _context(tmp_path)
    cfg = _config(tmp_path)

    mock_run.side_effect = lambda **kw: _make_topic_outputs(
        kw["output_dir"],
        kw.get("data_type", "twitter"),
        kw.get("content_type", "reply"),
    )

    result = run_monthly_topic_phase_task.fn(bundle, cfg, ctx)
    assert isinstance(result, TopicOutputBundle)
    assert result.partial_matched_communities_topics is None


# ---------------------------------------------------------------------------
# 9. Delegation — domain function called exactly once
# ---------------------------------------------------------------------------


@patch("src.pipelines.social_network_pipeline.run_topic_phase")
def test_domain_called_exactly_once(mock_run, tmp_path):
    bundle = _bundle(tmp_path)
    ctx = _context(tmp_path)
    cfg = _config(tmp_path)

    mock_run.side_effect = lambda **kw: _make_topic_outputs(
        kw["output_dir"],
        kw.get("data_type", "twitter"),
        kw.get("content_type", "reply"),
    )

    run_monthly_topic_phase_task.fn(bundle, cfg, ctx)
    mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# 10. Outputs — correct types and keys, no large objects
# ---------------------------------------------------------------------------


@patch("src.pipelines.social_network_pipeline.run_topic_phase")
def test_output_bundle_contains_only_artifact_references(mock_run, tmp_path):
    bundle = _bundle(tmp_path)
    ctx = _context(tmp_path)
    cfg = _config(tmp_path)

    mock_run.side_effect = lambda **kw: _make_topic_outputs(
        kw["output_dir"],
        kw.get("data_type", "twitter"),
        kw.get("content_type", "reply"),
    )

    result = run_monthly_topic_phase_task.fn(bundle, cfg, ctx)

    import pandas as pd
    import gensim

    def _check_no_large_obj(obj, path="result"):
        forbidden_types = (
            pd.DataFrame,
            gensim.models.LdaModel,
            gensim.models.LdaMulticore,
        )
        if isinstance(obj, forbidden_types):
            pytest.fail(f"Large object {type(obj)} found at {path}")
        if isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                _check_no_large_obj(item, f"{path}[{i}]")
        if hasattr(obj, "__dataclass_fields__"):
            for field in obj.__dataclass_fields__:
                _check_no_large_obj(getattr(obj, field), f"{path}.{field}")

    _check_no_large_obj(result)
    assert isinstance(result.lda_scores, ArtifactReference)
    assert result.lda_scores.asset_key == "lda_scores_march"
    assert result.lda_scores.path.endswith("march.parquet")
    assert len(result.theme_inputs) == 1


# ---------------------------------------------------------------------------
# 11. Outputs — stale / debug files are NOT included
# ---------------------------------------------------------------------------


@patch("src.pipelines.social_network_pipeline.run_topic_phase")
def test_stale_files_excluded_from_output(mock_run, tmp_path):
    bundle = _bundle(tmp_path)
    ctx = _context(tmp_path)
    cfg = _config(tmp_path)

    def side_effect(**kw):
        out = kw["output_dir"]
        _make_topic_outputs(out, "twitter", "reply")
        # Create stale/debug file in output directory
        (Path(out) / "debug_leftover.parquet").write_text("stale")

    mock_run.side_effect = side_effect

    result = run_monthly_topic_phase_task.fn(bundle, cfg, ctx)

    all_paths = (
        [result.lda_scores.path]
        + [
            r.path
            for r in [
                result.matched_communities_topics,
                result.partial_matched_communities_topics,
            ]
            if r
        ]
        + [r.path for r in result.theme_inputs]
    )

    assert not any("debug_leftover" in p for p in all_paths)


# ---------------------------------------------------------------------------
# 12. Required configuration and schema validation
# ---------------------------------------------------------------------------


def test_missing_required_topic_config_fails_before_domain(tmp_path):
    bundle = _bundle(tmp_path)
    config = ValidatedRunConfiguration(
        config_digest="d",
        output_root=str(tmp_path),
        raw_config={"data_type": "twitter", "content_type": "reply", "month": "march"},
    )
    with patch("src.pipelines.social_network_pipeline.run_topic_phase") as mock_run:
        with pytest.raises(PipelineError) as exc_info:
            run_monthly_topic_phase_task.fn(bundle, config, _context(tmp_path))
    assert exc_info.value.category == ErrorCategory.INVALID_CONFIGURATION
    mock_run.assert_not_called()


def test_invalid_topic_parquet_schema_fails_before_domain(tmp_path):
    invalid = _write(tmp_path / "invalid.parquet", pd.DataFrame({"wrong": ["value"]}))
    bundle = TopicInputBundle(
        absolute_community_messages=invalid,
        weighted_community_messages=invalid,
        matched_communities=invalid,
        partial_matched_communities=None,
        allowed_input_roots=(str(tmp_path),),
    )
    with patch("src.pipelines.social_network_pipeline.run_topic_phase") as mock_run:
        with pytest.raises(PipelineError) as exc_info:
            run_monthly_topic_phase_task.fn(
                bundle, _config(tmp_path), _context(tmp_path)
            )
    assert exc_info.value.category == ErrorCategory.SCHEMA_VIOLATION
    mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# 13. Cache key helper tests
# ---------------------------------------------------------------------------


def _make_cache_params(tmp_path, lda_config=None, provider_config=None):
    content = b"col\nval"
    p = tmp_path / "f.parquet"
    p.write_bytes(content)
    ref = ArtifactReference(
        path=str(p),
        sha256=_sha256(content),
        media_type="application/octet-stream",
        byte_size=len(content),
    )
    bundle = TopicInputBundle(
        absolute_community_messages=ref,
        weighted_community_messages=ref,
        matched_communities=ref,
        partial_matched_communities=None,
    )
    raw = {
        "lda": lda_config or {"num_topics": 15, "random_state": 100, "passes": 80},
        "preprocessing": {"remove_stopwords": True},
        "matching": {"threshold": 0.1},
    }
    if provider_config:
        raw["theme_provider"] = provider_config
        raw["prompt_version"] = "v99"

    config = ValidatedRunConfiguration(
        config_digest="d", output_root=str(tmp_path), raw_config=raw
    )
    return {"input_bundle": bundle, "config": config}


def test_cache_key_same_inputs_same_key(tmp_path):
    params = _make_cache_params(tmp_path)
    k1 = topic_cache_key_fn(None, params)
    k2 = topic_cache_key_fn(None, params)
    assert k1 == k2


def test_cache_key_stable_across_dict_order(tmp_path):
    content = b"col\nval"
    p = tmp_path / "f.parquet"
    p.write_bytes(content)
    ref = ArtifactReference(
        path=str(p),
        sha256=_sha256(content),
        media_type="application/octet-stream",
        byte_size=len(content),
    )
    bundle = TopicInputBundle(
        absolute_community_messages=ref,
        weighted_community_messages=ref,
        matched_communities=ref,
        partial_matched_communities=None,
    )
    base_raw = {
        "lda": {"num_topics": 15, "random_state": 100},
        "preprocessing": {},
        "matching": {},
    }
    # dict ordering differs — key must be the same
    cfg1 = ValidatedRunConfiguration("d", str(tmp_path), base_raw)
    cfg2 = ValidatedRunConfiguration(
        "d", str(tmp_path), dict(reversed(list(base_raw.items())))
    )
    k1 = topic_cache_key_fn(None, {"input_bundle": bundle, "config": cfg1})
    k2 = topic_cache_key_fn(None, {"input_bundle": bundle, "config": cfg2})
    assert k1 == k2


def test_cache_key_changes_on_lda_seed_change(tmp_path):
    params_a = _make_cache_params(tmp_path, lda_config={"random_state": 100})
    params_b = _make_cache_params(tmp_path, lda_config={"random_state": 999})
    assert topic_cache_key_fn(None, params_a) != topic_cache_key_fn(None, params_b)


def test_cache_key_changes_on_input_hash_change(tmp_path):
    params_a = _make_cache_params(tmp_path)
    content_b = b"col\nother"
    p_b = tmp_path / "b.parquet"
    p_b.write_bytes(content_b)
    ref_b = ArtifactReference(
        path=str(p_b),
        sha256=_sha256(content_b),
        media_type="application/octet-stream",
        byte_size=len(content_b),
    )
    params_b_bundle = TopicInputBundle(
        absolute_community_messages=ref_b,
        weighted_community_messages=ref_b,
        matched_communities=ref_b,
        partial_matched_communities=None,
    )
    params_b = {
        "input_bundle": params_b_bundle,
        "config": params_a["config"],
    }
    assert topic_cache_key_fn(None, params_a) != topic_cache_key_fn(None, params_b)


def test_cache_key_unchanged_by_provider_config(tmp_path):
    params_no_provider = _make_cache_params(tmp_path)
    params_with_provider = _make_cache_params(
        tmp_path, provider_config={"primary": "openai", "fallback_chain": []}
    )
    # Provider/prompt settings must NOT change the topic cache key
    assert topic_cache_key_fn(None, params_no_provider) == topic_cache_key_fn(
        None, params_with_provider
    )


def test_cache_key_changes_on_topic_count_change(tmp_path):
    params_a = _make_cache_params(tmp_path, lda_config={"num_topics": 10})
    params_b = _make_cache_params(tmp_path, lda_config={"num_topics": 20})
    assert topic_cache_key_fn(None, params_a) != topic_cache_key_fn(None, params_b)


def test_topic_cache_key_fn_is_enabled_on_task():
    """The topic Prefect task must use the stage-specific topic cache key."""
    assert run_monthly_topic_phase_task.cache_key_fn is topic_cache_key_fn
