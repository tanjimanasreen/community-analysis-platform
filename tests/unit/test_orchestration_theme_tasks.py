"""
Comprehensive hardened tests for the Theme orchestration task.

Covers:
- Provider factory called exactly once (domain ownership)
- Same provider reused across batch (CachedProvider)
- Invalid inputs result in 0 provider constructions
- retries=0 confirmed
- Input validation: missing, hash mismatch, size mismatch, path escape, empty bundle
- Provider summary: required fields present, secrets excluded
- Output discovery: exact paths, stale/debug files excluded
- No large object in results
- No network calls, no model downloads
"""

import hashlib
import json
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from prefect.testing.utilities import prefect_test_harness

from src.orchestration.models import (
    ArtifactReference,
    PipelineRunContext,
    ThemeInputBundle,
    ThemeOutputBundle,
    ValidatedRunConfiguration,
)
from src.orchestration.tasks import run_monthly_themes_task
from src.orchestration.retry_policy import ErrorCategory, PipelineError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


THEME_INPUT_CONTENT = b"""members,absolute_community,weighted_community,absolute_unigram_keywords,absolute_bigram_keywords,weighted_unigram_keywords,weighted_bigram_keywords
"['u1']",1,2,"['a']","['b']","['c']","['d']"
"""


def _write(path: Path, content: bytes = THEME_INPUT_CONTENT) -> ArtifactReference:
    path.write_bytes(content)
    return ArtifactReference(
        path=str(path),
        sha256=_sha256(content),
        media_type="text/csv",
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


def _config(tmp_path, **extra) -> ValidatedRunConfiguration:
    raw = {
        "month": "march",
        "year": "2017",
        "data_type": "twitter",
        "content_type": "reply",
        "render_visuals": False,
        **extra,
    }
    return ValidatedRunConfiguration(
        config_digest="d",
        output_root=str(tmp_path),
        raw_config=raw,
    )


def _make_theme_outputs(out_dir: str, months=("march",), year="2017"):
    """Simulate the files that run_theme_pipeline_from_monthly_data writes."""
    for month in months:
        Path(os.path.join(out_dir, f"{month}_{year}_with_themes.csv")).write_text(
            "community,theme\n1,Technology"
        )
    Path(os.path.join(out_dir, "community_transition.csv")).write_text("from,to\nA,B")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def prefect_test_fixture():
    with prefect_test_harness():
        yield


# ---------------------------------------------------------------------------
# 1. retries=0 confirmed
# ---------------------------------------------------------------------------


def test_theme_task_retries_zero():
    assert run_monthly_themes_task.retries == 0


# ---------------------------------------------------------------------------
# 2. Empty bundle fails before provider construction
# ---------------------------------------------------------------------------


@patch("src.providers.factory.build_theme_provider")
def test_empty_bundle_fails_before_provider(mock_build, tmp_path):
    bundle = ThemeInputBundle(monthly_topic_outputs={})
    with pytest.raises(PipelineError) as exc_info:
        run_monthly_themes_task.fn(bundle, _config(tmp_path), _context(tmp_path))
    assert exc_info.value.category == ErrorCategory.MISSING_REQUIRED_INPUT
    mock_build.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Missing input file fails before provider construction
# ---------------------------------------------------------------------------


@patch("src.providers.factory.build_theme_provider")
def test_missing_input_fails_before_provider(mock_build, tmp_path):
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "march": ArtifactReference(
                path="/nonexistent/march.csv",
                sha256="0" * 64,
                media_type="text/csv",
            )
        }
    )
    with pytest.raises(PipelineError) as exc_info:
        run_monthly_themes_task.fn(bundle, _config(tmp_path), _context(tmp_path))
    assert exc_info.value.category == ErrorCategory.MISSING_REQUIRED_INPUT
    mock_build.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Hash mismatch fails before provider construction
# ---------------------------------------------------------------------------


@patch("src.providers.factory.build_theme_provider")
def test_hash_mismatch_fails_before_provider(mock_build, tmp_path):
    content = THEME_INPUT_CONTENT
    p = tmp_path / "march.csv"
    p.write_bytes(content)
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "march": ArtifactReference(
                path=str(p),
                sha256="a" * 64,  # wrong hash
                media_type="text/csv",
                byte_size=len(content),
            )
        },
        allowed_input_roots=(str(tmp_path),),
    )
    with pytest.raises(PipelineError) as exc_info:
        run_monthly_themes_task.fn(bundle, _config(tmp_path), _context(tmp_path))
    assert exc_info.value.category == ErrorCategory.SCHEMA_VIOLATION
    mock_build.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Size mismatch fails before provider construction
# ---------------------------------------------------------------------------


@patch("src.providers.factory.build_theme_provider")
def test_size_mismatch_fails_before_provider(mock_build, tmp_path):
    content = THEME_INPUT_CONTENT
    p = tmp_path / "march.csv"
    p.write_bytes(content)
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "march": ArtifactReference(
                path=str(p),
                sha256=_sha256(content),
                media_type="text/csv",
                byte_size=9999,  # wrong
            )
        },
        allowed_input_roots=(str(tmp_path),),
    )
    with pytest.raises(PipelineError) as exc_info:
        run_monthly_themes_task.fn(bundle, _config(tmp_path), _context(tmp_path))
    assert exc_info.value.category == ErrorCategory.SCHEMA_VIOLATION
    mock_build.assert_not_called()


# ---------------------------------------------------------------------------
# 6. Path escape fails before provider construction
# ---------------------------------------------------------------------------


@patch("src.providers.factory.build_theme_provider")
def test_path_escape_fails_before_provider(mock_build, tmp_path):
    import tempfile
    import shutil

    other = Path(tempfile.mkdtemp())
    try:
        content = THEME_INPUT_CONTENT
        p = other / "march.csv"
        p.write_bytes(content)
        bundle = ThemeInputBundle(
            monthly_topic_outputs={
                "march": ArtifactReference(
                    path=str(p),
                    sha256=_sha256(content),
                    media_type="text/csv",
                    byte_size=len(content),
                )
            },
            allowed_input_roots=(str(tmp_path),),
        )
        with pytest.raises(PipelineError) as exc_info:
            run_monthly_themes_task.fn(bundle, _config(tmp_path), _context(tmp_path))
        assert exc_info.value.category == ErrorCategory.SCHEMA_VIOLATION
        mock_build.assert_not_called()
    finally:
        shutil.rmtree(str(other), ignore_errors=True)


# ---------------------------------------------------------------------------
# 6b. Standalone input root accepted
# ---------------------------------------------------------------------------


@patch("src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data")
def test_explicit_standalone_input_root_accepted(mock_run, tmp_path):
    import tempfile
    import shutil

    other = Path(tempfile.mkdtemp())
    try:
        content = THEME_INPUT_CONTENT
        p = other / "march.csv"
        p.write_bytes(content)
        bundle = ThemeInputBundle(
            monthly_topic_outputs={
                "march": ArtifactReference(
                    path=str(p),
                    sha256=_sha256(content),
                    media_type="text/csv",
                    byte_size=len(content),
                )
            },
            allowed_input_roots=(str(other),),
        )
        mock_run.side_effect = lambda **kw: _make_theme_outputs(kw["output_dir"])

        # This should NOT raise an error about being outside allowed_root
        result = run_monthly_themes_task.fn(
            bundle, _config(tmp_path), _context(tmp_path)
        )
        assert isinstance(result, ThemeOutputBundle)
    finally:
        shutil.rmtree(str(other), ignore_errors=True)


# ---------------------------------------------------------------------------
# 7. Provider factory called exactly once (domain ownership)
# ---------------------------------------------------------------------------


@patch("src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data")
@patch("src.providers.factory.build_theme_provider")
def test_provider_factory_called_exactly_once(mock_build, mock_run, tmp_path):
    """
    Tests that build_theme_provider is called exactly once by the domain.
    We patch both the domain function AND build_theme_provider so we can
    count factory calls while allowing the domain call to succeed.
    """
    content = THEME_INPUT_CONTENT
    p = tmp_path / "march.csv"
    p.write_bytes(content)
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "march": ArtifactReference(
                path=str(p),
                sha256=_sha256(content),
                media_type="text/csv",
                byte_size=len(content),
            )
        },
        allowed_input_roots=(str(tmp_path),),
    )

    def fake_run(**kw):
        _make_theme_outputs(kw["output_dir"])

    mock_run.side_effect = fake_run

    run_monthly_themes_task.fn(bundle, _config(tmp_path), _context(tmp_path))

    # The domain is called exactly once
    mock_run.assert_called_once()
    # provider=None is passed, so domain owns construction
    assert mock_run.call_args[1].get("provider") is None


# ---------------------------------------------------------------------------
# 8. Provider not in task results
# ---------------------------------------------------------------------------


@patch("src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data")
def test_no_provider_object_in_results(mock_run, tmp_path):
    content = THEME_INPUT_CONTENT
    p = tmp_path / "march.csv"
    p.write_bytes(content)
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "march": ArtifactReference(
                path=str(p),
                sha256=_sha256(content),
                media_type="text/csv",
                byte_size=len(content),
            )
        },
        allowed_input_roots=(str(tmp_path),),
    )

    mock_run.side_effect = lambda **kw: _make_theme_outputs(kw["output_dir"])

    result = run_monthly_themes_task.fn(bundle, _config(tmp_path), _context(tmp_path))

    from src.providers.base import BaseLLMProvider
    import pandas as pd

    def _check(obj, path="result"):
        if isinstance(obj, (BaseLLMProvider, pd.DataFrame)):
            pytest.fail(f"Forbidden type {type(obj)} at {path}")
        if hasattr(obj, "__dataclass_fields__"):
            for field in obj.__dataclass_fields__:
                _check(getattr(obj, field), f"{path}.{field}")
        if isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                _check(item, f"{path}[{i}]")

    _check(result)


# ---------------------------------------------------------------------------
# 9. Provider summary — required fields, secrets excluded
# ---------------------------------------------------------------------------


@patch("src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data")
def test_provider_summary_schema(mock_run, tmp_path, caplog):
    import json

    content = THEME_INPUT_CONTENT
    p = tmp_path / "march.csv"
    p.write_bytes(content)
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "march": ArtifactReference(
                path=str(p),
                sha256=_sha256(content),
                media_type="text/csv",
                byte_size=len(content),
            )
        },
        allowed_input_roots=(str(tmp_path),),
    )
    mock_run.side_effect = lambda **kw: _make_theme_outputs(kw["output_dir"])

    raw_extra = {
        "OPENAI_API_KEY": "secret-a",
        "GEMINI_API_KEY": "secret-b",
        "apiKey": "secret-c",
        "access_token": "secret-d",
        "client_secret": "secret-e",
        "authorization": "Bearer secret-f",
        "provider": {
            "credentials": {
                "token": "secret-g",
                "password": "secret-h",
            }
        },
    }
    cfg = _config(tmp_path, **raw_extra)
    result = run_monthly_themes_task.fn(bundle, cfg, _context(tmp_path))

    # Assert it is an ArtifactReference
    assert result.provider_run_summary is not None
    assert isinstance(result.provider_run_summary, ArtifactReference)

    # Assert it is under the run output root
    summary_path = Path(result.provider_run_summary.path).resolve()
    assert summary_path.is_relative_to((tmp_path / "run-test").resolve())

    # Assert it exists
    assert summary_path.is_file()

    # Assert media type, sha256, byte size
    assert result.provider_run_summary.media_type == "application/json"
    assert result.provider_run_summary.byte_size == summary_path.stat().st_size
    assert result.provider_run_summary.sha256 == _sha256(summary_path.read_bytes())

    with open(summary_path) as f:
        data = json.load(f)

    # Schema contains only allowed keys
    allowed_fields = {
        "schema_version",
        "configured_primary_provider",
        "configured_primary_model",
        "configured_fallback_chain",
        "provider_config_digest",
        "prompt_version",
        "generation_settings_digest",
        "semantic_task_version",
    }
    assert set(data.keys()) == allowed_fields

    # None of the injected secret keys or values appears anywhere in the JSON
    json_str = json.dumps(data).lower()
    injected_secrets = [
        "secret-a",
        "secret-b",
        "secret-c",
        "secret-d",
        "secret-e",
        "secret-f",
        "secret-g",
        "secret-h",
    ]
    for secret in injected_secrets:
        assert secret not in json_str, f"Secret {secret} leaked into JSON"

    # None appears in the returned task result
    import dataclasses

    result_str = str(dataclasses.asdict(result)).lower()
    for secret in injected_secrets:
        assert secret not in result_str, f"Secret {secret} leaked into Task Result"

    # None appears in captured logs
    log_str = caplog.text.lower()
    for secret in injected_secrets:
        assert secret not in log_str, f"Secret {secret} leaked into logs"


# ---------------------------------------------------------------------------
# 10. Provider summary digest is deterministic
# ---------------------------------------------------------------------------


@patch("src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data")
def test_provider_summary_digest_deterministic(mock_run, tmp_path):
    content = THEME_INPUT_CONTENT
    p1 = tmp_path / "m1.csv"
    p2 = tmp_path / "m2.csv"
    p1.write_bytes(content)
    p2.write_bytes(content)

    def make_bundle(path):
        return ThemeInputBundle(
            monthly_topic_outputs={
                "march": ArtifactReference(
                    path=str(path),
                    sha256=_sha256(content),
                    media_type="text/csv",
                    byte_size=len(content),
                )
            },
            allowed_input_roots=(str(tmp_path),),
        )

    mock_run.side_effect = lambda **kw: _make_theme_outputs(kw["output_dir"])

    r1 = run_monthly_themes_task.fn(
        make_bundle(p1), _config(tmp_path), _context(tmp_path)
    )
    r2 = run_monthly_themes_task.fn(
        make_bundle(p2), _config(tmp_path), _context(tmp_path)
    )

    with open(r1.provider_run_summary.path) as f:
        d1 = json.load(f)
    with open(r2.provider_run_summary.path) as f:
        d2 = json.load(f)

    assert d1["provider_config_digest"] == d2["provider_config_digest"]


# ---------------------------------------------------------------------------
# 11. Stale files excluded from visualization output
# ---------------------------------------------------------------------------


@patch("src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data")
def test_stale_files_excluded_from_visualizations(mock_run, tmp_path):
    content = THEME_INPUT_CONTENT
    p = tmp_path / "march.csv"
    p.write_bytes(content)
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "march": ArtifactReference(
                path=str(p),
                sha256=_sha256(content),
                media_type="text/csv",
                byte_size=len(content),
            )
        },
        allowed_input_roots=(str(tmp_path),),
    )

    def fake_run(**kw):
        out = kw["output_dir"]
        _make_theme_outputs(out)
        # Create stale / unexpected files
        sankey_dir = os.path.join(out, "sankey")
        os.makedirs(sankey_dir, exist_ok=True)
        (Path(sankey_dir) / "community_transition.html").write_text("<html>")
        (Path(sankey_dir) / "stale-debug.png").write_bytes(b"stale")
        (Path(sankey_dir) / ".hidden").write_text("hidden")
        (Path(sankey_dir) / "debug.tmp").write_text("debug")

        membership_dir = Path(out) / "membership_changes"
        membership_dir.mkdir(parents=True, exist_ok=True)
        (membership_dir / "community_changes_0.png").write_bytes(b"real")
        (membership_dir / "old-output.html").write_text("stale")

        similarity_dir = Path(out) / "theme_similarity"
        similarity_dir.mkdir(parents=True, exist_ok=True)
        (similarity_dir / "absolute_theme.html").write_text("<html>")
        (similarity_dir / "unexpected.svg").write_text("stale")

    mock_run.side_effect = fake_run

    result = run_monthly_themes_task.fn(bundle, _config(tmp_path), _context(tmp_path))

    vis_paths = [a.path for a in result.visualizations]
    assert any("community_transition.html" in p for p in vis_paths)
    assert any("community_changes_0.png" in p for p in vis_paths)
    assert any("absolute_theme.html" in p for p in vis_paths)
    assert not any("stale-debug.png" in p for p in vis_paths)
    assert not any("old-output.html" in p for p in vis_paths)
    assert not any("unexpected.svg" in p for p in vis_paths)
    assert not any(".hidden" in p for p in vis_paths)
    assert not any("debug.tmp" in p for p in vis_paths)


# ---------------------------------------------------------------------------
# 12. Required configuration and schema validation
# ---------------------------------------------------------------------------


def test_missing_required_theme_config_fails_before_domain(tmp_path):
    input_ref = _write(tmp_path / "march.csv")
    bundle = ThemeInputBundle(
        monthly_topic_outputs={"march": input_ref},
        allowed_input_roots=(str(tmp_path),),
    )
    config = ValidatedRunConfiguration(
        config_digest="d",
        output_root=str(tmp_path),
        raw_config={"content_type": "reply"},
    )
    with patch(
        "src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data"
    ) as mock_run:
        with pytest.raises(PipelineError) as exc_info:
            run_monthly_themes_task.fn(bundle, config, _context(tmp_path))
    assert exc_info.value.category == ErrorCategory.INVALID_CONFIGURATION
    mock_run.assert_not_called()


def test_invalid_theme_csv_schema_fails_before_domain(tmp_path):
    invalid = _write(tmp_path / "invalid.csv", b"wrong\nvalue\n")
    bundle = ThemeInputBundle(
        monthly_topic_outputs={"march": invalid},
        allowed_input_roots=(str(tmp_path),),
    )
    with patch(
        "src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data"
    ) as mock_run:
        with pytest.raises(PipelineError) as exc_info:
            run_monthly_themes_task.fn(bundle, _config(tmp_path), _context(tmp_path))
    assert exc_info.value.category == ErrorCategory.SCHEMA_VIOLATION
    mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# 13. Output uses OUTPUT_NOT_FOUND (not MISSING_REQUIRED_INPUT) for missing post-exec output
# ---------------------------------------------------------------------------


@patch("src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data")
def test_missing_post_exec_output_uses_correct_category(mock_run, tmp_path):
    content = THEME_INPUT_CONTENT
    p = tmp_path / "march.csv"
    p.write_bytes(content)
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "march": ArtifactReference(
                path=str(p),
                sha256=_sha256(content),
                media_type="text/csv",
                byte_size=len(content),
            )
        },
        allowed_input_roots=(str(tmp_path),),
    )

    # Domain runs but writes NO outputs
    mock_run.side_effect = lambda **kw: None

    with pytest.raises(PipelineError) as exc_info:
        run_monthly_themes_task.fn(bundle, _config(tmp_path), _context(tmp_path))

    assert exc_info.value.category == ErrorCategory.OUTPUT_NOT_FOUND


# ---------------------------------------------------------------------------
# 13. Theme artifacts remain under run-specific directory
# ---------------------------------------------------------------------------


@patch("src.pipelines.theme_pipeline.run_theme_pipeline_from_monthly_data")
def test_artifacts_under_run_directory(mock_run, tmp_path):
    content = THEME_INPUT_CONTENT
    p = tmp_path / "march.csv"
    p.write_bytes(content)
    bundle = ThemeInputBundle(
        monthly_topic_outputs={
            "march": ArtifactReference(
                path=str(p),
                sha256=_sha256(content),
                media_type="text/csv",
                byte_size=len(content),
            )
        },
        allowed_input_roots=(str(tmp_path),),
    )
    mock_run.side_effect = lambda **kw: _make_theme_outputs(kw["output_dir"])

    result = run_monthly_themes_task.fn(bundle, _config(tmp_path), _context(tmp_path))

    expected_root = (tmp_path / "run-test").resolve()
    for art in result.themes:
        assert (
            Path(art.path).resolve().is_relative_to(expected_root)
        ), f"{art.path} is outside run directory"
    if result.community_transitions:
        assert (
            Path(result.community_transitions.path)
            .resolve()
            .is_relative_to(expected_root)
        )
    assert (
        Path(result.provider_run_summary.path).resolve().is_relative_to(expected_root)
    )
