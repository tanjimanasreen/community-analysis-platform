from __future__ import annotations

from pathlib import Path

import pytest

import src.preflight as preflight
from src.preflight import PipelinePreflightError, PreflightCheck


def test_project_dependency_lock_matches_pyproject_and_has_no_external_hdbscan():
    result = preflight._lock_check(Path(__file__).resolve().parents[2])
    assert result.ok, result.detail


def test_requirement_marker_parser_handles_python_310_compatibility(monkeypatch):
    class VersionInfo:
        major = 3
        minor = 10
        micro = 14

    monkeypatch.setattr(preflight.sys, "version_info", VersionInfo())
    assert preflight._marker_applies("python_version < '3.11'", extras=())
    assert preflight._marker_applies("python_full_version < '3.11'", extras=())
    assert not preflight._marker_applies("python_version >= '3.11'", extras=())


def test_profile_contract_requires_exact_model_and_revision():
    good = preflight._profile_contract_check(
        "clustering",
        actual_model="sentence-transformers/all-MiniLM-L6-v2",
        actual_revision="rev-a",
        expected_model="sentence-transformers/all-MiniLM-L6-v2",
        expected_revision="rev-a",
    )
    bad = preflight._profile_contract_check(
        "clustering",
        actual_model="sentence-transformers/all-MiniLM-L6-v2",
        actual_revision="rev-b",
        expected_model="sentence-transformers/all-MiniLM-L6-v2",
        expected_revision="rev-a",
    )
    assert good.ok
    assert not bad.ok
    assert "does not match" in bad.detail


def test_live_provider_preflight_requires_credentials_and_provider_endpoint(
    monkeypatch,
):
    from pydantic import SecretStr
    from types import SimpleNamespace

    monkeypatch.setattr(
        preflight,
        "get_provider_settings",
        lambda: SimpleNamespace(
            openai_api_key=None,
            gemini_api_key=None,
            llm7_api_key=SecretStr("token"),
            llm7_base_url=None,
            mistral_api_key=None,
            mistral_base_url=None,
            nvidia_api_key=None,
            nvidia_base_url=None,
        ),
    )

    openai = preflight._credential_checks(
        {"theme_provider": {"primary": "openai:gpt-5-nano"}}
    )
    llm7 = preflight._credential_checks(
        {"theme_provider": {"primary": "llm7:some-model"}}
    )

    assert len(openai) == 1 and not openai[0].ok
    assert "OPENAI_API_KEY" in openai[0].detail
    assert len(llm7) == 1 and not llm7[0].ok
    assert "LLM7_BASE_URL" in llm7[0].detail


def test_pipeline_preflight_fails_before_run_when_relationship_csv_is_missing(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        preflight,
        "_dependency_checks",
        lambda config: [PreflightCheck("python-dependencies", True, "test")],
    )
    monkeypatch.setattr(
        preflight,
        "_lock_check",
        lambda root, **kwargs: PreflightCheck("dependency-lock", True, "test"),
    )
    monkeypatch.setattr(preflight, "_credential_checks", lambda config: [])
    monkeypatch.setattr(
        preflight,
        "_embedding_profile_checks",
        lambda config, check_services: [],
    )
    config = {
        "output_base_path": str(tmp_path / "out"),
        "longitudinal_datasets": [
            {"month": "01", "input_path": str(tmp_path / "missing.csv")}
        ],
    }

    with pytest.raises(PipelinePreflightError) as exc_info:
        preflight.run_pipeline_preflight(config, project_root=tmp_path)

    failed = [check for check in exc_info.value.checks if not check.ok]
    assert [check.name for check in failed] == ["input-01"]


def test_pipeline_preflight_passes_with_mocked_external_checks(tmp_path, monkeypatch):
    input_path = tmp_path / "input.csv"
    input_path.write_text("source,target\n1,2\n", encoding="utf-8")
    monkeypatch.setattr(
        preflight,
        "_dependency_checks",
        lambda config: [PreflightCheck("python-dependencies", True, "test")],
    )
    monkeypatch.setattr(
        preflight,
        "_lock_check",
        lambda root, **kwargs: PreflightCheck("dependency-lock", True, "test"),
    )
    monkeypatch.setattr(preflight, "_credential_checks", lambda config: [])
    monkeypatch.setattr(
        preflight,
        "_embedding_profile_checks",
        lambda config, check_services: [],
    )
    config = {
        "output_base_path": str(tmp_path / "out"),
        "longitudinal_datasets": [{"month": "01", "input_path": str(input_path)}],
    }

    checks = preflight.run_pipeline_preflight(config, project_root=tmp_path)

    assert checks
    assert all(check.ok for check in checks)
