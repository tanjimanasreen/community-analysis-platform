from __future__ import annotations

import json
import builtins
from pathlib import Path

import pytest

from src.themes.benchmark.contracts import (
    THEME_OUTPUT_JSON_SCHEMA,
    build_theme_output_json_schema,
    ProviderMetadata,
    ThemeBenchmarkError,
    read_jsonl,
)
from src.themes.benchmark.dataset import build_dataset
from src.providers.gemini import (
    GEMINI_INSTALL_MESSAGE,
    GeminiBenchmarkProvider,
    build_gemini_model_catalog,
    discover_gemini_models,
)
from src.themes.benchmark.runner import run_benchmark
from src.themes.theme_inputs import save_theme_inputs

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "theme_benchmark"
    / "matched_lda.parquet"
)


class FakeInteraction:
    output_text = json.dumps({"themes": [{"name": "Fruit", "keyword_indices": [0, 1]}]})
    id = "interaction-1"
    status = "completed"
    usage_metadata = {
        "input_token_count": 10,
        "output_token_count": 5,
        "total_token_count": 15,
    }
    finish_reason = "STOP"
    safety_metadata = {"blocked": False}


class FakeInteractions:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = list(responses or [FakeInteraction()])

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0) if self.responses else FakeInteraction()
        if isinstance(response, Exception):
            raise response
        return response


class FakeModels:
    def __init__(self, models):
        self._models = models

    def list(self):
        return self._models


class FakeClient:
    def __init__(self, responses=None, models=None):
        self.interactions = FakeInteractions(responses)
        self.models = FakeModels(models or [])


class FakeStatusError(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


def _config(tmp_path):
    return {
        "data_type": "twitter",
        "content_type": "reply",
        "month": "03",
        "year": "2017",
        "input_path": "unused.csv",
        "output_base_path": str(tmp_path / "outputs"),
        "creator_relation": "REPLIED_TO",
        "spreader_relation": "REPLIED_BY",
        "creator_node_column": "target",
        "spreader_node_column": "target",
        "text_node_column": "source",
        "date_column": "created_at",
    }


def _save_theme_fixture(config):
    return save_theme_inputs(
        matched_lda_csv=FIXTURE,
        output_base_path=config["output_base_path"],
        data_type=config["data_type"],
        content_type=config["content_type"],
        month="03",
        year=config["year"],
    )


def _request(tmp_path):
    config = _config(tmp_path)
    _save_theme_fixture(config)
    result = build_dataset(config, run_id="gemini-request", limit=1)
    return read_jsonl(result["output_dir"] / "requests.jsonl")[0]


def test_gemini_provider_requires_allow_live_before_client_creation():
    with pytest.raises(ThemeBenchmarkError, match="--allow-live"):
        GeminiBenchmarkProvider(
            model_id="gemini-3.5-flash", allow_live=False, client=FakeClient()
        )


def test_gemini_provider_missing_key_fails_clearly(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from src.config.settings import ProviderSettings

    isolated_settings = ProviderSettings(_env_file=None, gemini_api_key=None)
    monkeypatch.setattr(
        "src.providers.gemini.get_provider_settings", lambda: isolated_settings
    )

    with pytest.raises(ThemeBenchmarkError, match="GEMINI_API_KEY"):
        GeminiBenchmarkProvider(model_id="gemini-3.5-flash", allow_live=True)


@pytest.mark.parametrize(
    "import_error",
    [
        ModuleNotFoundError("No module named 'google.genai'"),
        ImportError("cannot import name 'genai' from 'google'"),
    ],
)
def test_gemini_provider_missing_sdk_has_install_message(monkeypatch, import_error):
    monkeypatch.setenv("GEMINI_API_KEY", "not-persisted")
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "google" and "genai" in fromlist:
            raise import_error
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ThemeBenchmarkError, match="benchmark-gemini") as exc:
        GeminiBenchmarkProvider(model_id="gemini-3.5-flash", allow_live=True)

    assert GEMINI_INSTALL_MESSAGE in str(exc.value)


def test_gemini_request_construction_preserves_roles_and_settings(tmp_path):
    request_row = _request(tmp_path)
    client = FakeClient()
    provider = GeminiBenchmarkProvider(
        model_id="gemini-3.5-flash",
        allow_live=True,
        client=client,
        sdk_version="2.3.0",
    )

    provider.generate(type("Request", (), request_row)())

    call = client.interactions.calls[0]
    assert call["model"] == "gemini-3.5-flash"
    assert call["system_instruction"] == request_row["system_prompt"]
    assert call["input"] == request_row["user_prompt"]
    assert call["generation_config"] == {"temperature": 0.0}
    assert call["store"] is False
    assert call["response_format"] == {
        "type": "text",
        "mime_type": "application/json",
        "schema": build_theme_output_json_schema(len(request_row["keywords"])),
    }
    assert "not-persisted" not in json.dumps(call)


def test_gemini_model_discovery_normalizes_and_classifies_without_secrets(tmp_path):
    models = [
        {
            "name": "models/gemini-3.1-flash-lite",
            "display_name": "Gemini 3.1 Flash-Lite",
            "supported_actions": ["generateContent"],
        },
        {
            "name": "models/gemini-3.5-flash",
            "display_name": "Gemini 3.5 Flash",
            "supported_actions": ["generateContent"],
        },
        {
            "name": "models/gemini-3.5-flash-latest",
            "display_name": "Gemini Latest",
            "supported_actions": ["generateContent"],
        },
        {
            "name": "models/gemini-3.5-pro-preview",
            "display_name": "Gemini Preview",
            "supported_actions": ["generateContent"],
            "description": "Preview model",
        },
        {
            "name": "models/text-embedding-001",
            "display_name": "Embedding",
            "supported_actions": ["embedContent"],
        },
    ]
    path = discover_gemini_models(
        tmp_path,
        allow_live=True,
        client=FakeClient(models=models),
        sdk_version="2.3.0",
    )
    catalog = json.loads(path.read_text(encoding="utf-8"))

    assert catalog["sdk_version"] == "2.3.0"
    assert catalog["contains_secrets"] is False
    assert {item["model_id"] for item in catalog["selected_candidates"]} == {
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
    }
    latest = next(
        model
        for model in catalog["models"]
        if model["model_id"] == "gemini-3.5-flash-latest"
    )
    assert latest["is_latest_alias"] is True
    preview = next(
        model
        for model in catalog["models"]
        if model["model_id"] == "gemini-3.5-pro-preview"
    )
    assert preview["is_preview"] is True
    embedding = next(
        model
        for model in catalog["models"]
        if model["model_id"] == "text-embedding-001"
    )
    assert embedding["generate_content_capable"] is False
    assert "not-persisted" not in json.dumps(catalog)


def test_gemini_catalog_records_ambiguous_candidates(monkeypatch):
    from src.providers.gemini import DOCUMENTED_INTERACTIONS_MODELS

    monkeypatch.setattr(
        "src.providers.gemini.DOCUMENTED_INTERACTIONS_MODELS",
        DOCUMENTED_INTERACTIONS_MODELS | {"gemini-3-flash", "gemini-3.5-flash"},
    )
    catalog = build_gemini_model_catalog(
        [
            {
                "model_id": "gemini-3.5-flash",
                "supported_actions": ["generateContent"],
                "description": "",
            },
            {
                "model_id": "gemini-3-flash",
                "supported_actions": ["generateContent"],
                "description": "",
            },
        ],
        sdk_version="2.3.0",
        retrieved_at="2026-07-08T00:00:00+00:00",
    )

    assert catalog["selected_candidates"] == []
    assert catalog["ambiguous_candidates"][0]["candidate_class"] == "flash"


def test_gemini_response_normalization_and_usage_metadata(tmp_path):
    request_row = _request(tmp_path)
    provider = GeminiBenchmarkProvider(
        model_id="gemini-3.5-flash",
        allow_live=True,
        client=FakeClient(),
        sdk_version="2.3.0",
    )

    result = provider.generate(type("Request", (), request_row)())

    assert result["themes"] == [{"name": "Fruit", "keywords": ["apple", "banana"]}]
    metadata = result["_benchmark_metadata"]
    assert metadata["parsed_successfully"] is True
    assert metadata["schema_valid"] is True
    assert metadata["usage"]["total_token_count"] == 15
    assert metadata["finish_reason"] == "STOP"


@pytest.mark.parametrize(
    "output_text,error",
    [
        ("not-json", "invalid_json"),
        (json.dumps({"bad": []}), "schema_invalid"),
        ("", "empty_response"),
    ],
)
def test_gemini_invalid_responses_fail_clearly(tmp_path, output_text, error):
    request_row = _request(tmp_path)
    interaction = FakeInteraction()
    interaction.output_text = output_text
    provider = GeminiBenchmarkProvider(
        model_id="gemini-3.5-flash",
        allow_live=True,
        client=FakeClient([interaction]),
        sdk_version="2.3.0",
    )

    with pytest.raises(ThemeBenchmarkError, match=error):
        provider.generate(type("Request", (), request_row)())


def test_gemini_retries_rate_limit_and_enforces_request_cap(tmp_path):
    request_row = _request(tmp_path)
    client = FakeClient([FakeStatusError("rate limited", 429), FakeInteraction()])
    provider = GeminiBenchmarkProvider(
        model_id="gemini-3.5-flash",
        allow_live=True,
        client=client,
        sdk_version="2.3.0",
        sleep_fn=lambda seconds: None,
    )

    result = provider.generate(type("Request", (), request_row)())

    assert result["_benchmark_metadata"]["retries"] == 1
    assert len(client.interactions.calls) == 2

    capped = GeminiBenchmarkProvider(
        model_id="gemini-3.5-flash",
        allow_live=True,
        client=FakeClient([FakeStatusError("rate limited", 429), FakeInteraction()]),
        sdk_version="2.3.0",
        max_outbound_requests=1,
        sleep_fn=lambda seconds: None,
    )
    with pytest.raises(ThemeBenchmarkError, match="request cap exhausted"):
        capped.generate(type("Request", (), request_row)())


def test_gemini_non_retryable_auth_error_is_not_retried(tmp_path):
    request_row = _request(tmp_path)
    client = FakeClient([FakeStatusError("bad key", 401), FakeInteraction()])
    provider = GeminiBenchmarkProvider(
        model_id="gemini-3.5-flash",
        allow_live=True,
        client=client,
        sdk_version="2.3.0",
        sleep_fn=lambda seconds: None,
    )

    with pytest.raises(ThemeBenchmarkError, match="authentication"):
        provider.generate(type("Request", (), request_row)())

    assert len(client.interactions.calls) == 1


def test_gemini_runner_cache_reuse_with_fake_client(monkeypatch, tmp_path):
    from src.themes.benchmark import runner

    config = _config(tmp_path)
    _save_theme_fixture(config)
    build_dataset(config, run_id="gemini-cache", limit=1)
    client = FakeClient()
    monkeypatch.setattr(
        runner,
        "get_provider",
        lambda *args, **kwargs: GeminiBenchmarkProvider(
            model_id="gemini-3.5-flash",
            allow_live=True,
            client=client,
            sdk_version="2.3.0",
            request_budget=kwargs.get("request_budget"),
        ),
    )

    first = run_benchmark(
        config,
        run_id="gemini-cache",
        provider_ids=["gemini:gemini-3.5-flash"],
        allow_live=True,
        keyword_modes=["general"],
    )
    second = run_benchmark(
        config,
        run_id="gemini-cache",
        provider_ids=["gemini:gemini-3.5-flash"],
        allow_live=True,
        keyword_modes=["general"],
    )

    assert first.provider_executions == 1
    assert first.outbound_requests == 1
    assert first.cache_hits == 0
    assert second.provider_executions == 0
    assert second.outbound_requests == 0
    assert second.cache_hits == 1
    assert len(client.interactions.calls) == 1
    assert "2.3.0" in json.dumps(
        (
            Path(config["output_base_path"])
            / "_experiments"
            / "theme_model_benchmark"
            / "gemini-cache"
            / "manifest.json"
        ).read_text()
    )


def test_live_preflight_prints_safe_gemini_fields(tmp_path, capsys):
    from src.cli import _print_live_benchmark_preflight

    config = _config(tmp_path)
    _save_theme_fixture(config)
    build_dataset(config, run_id="gemini-preflight", limit=1)

    _print_live_benchmark_preflight(
        config=config,
        run_id="gemini-preflight",
        provider_ids=["gemini:gemini-3.5-flash"],
        keyword_modes=["general"],
        max_examples=1,
        allow_live=True,
        max_outbound_requests=6,
        max_retries=2,
        timeout=None,
        max_concurrency=1,
    )

    output = capsys.readouterr().out
    assert "Live benchmark preflight:" in output
    assert "Selected model IDs: gemini-3.5-flash" in output
    assert "Example count: 1" in output
    assert "Keyword modes: general" in output
    assert "Normal request count: 1" in output
    assert "Max outbound requests: 6" in output
    assert "Gemini store=False" in output
    assert "API_KEY" not in output
    assert "not-persisted" not in output


def test_gemini_model_change_invalidates_cache(monkeypatch, tmp_path):
    from src.themes.benchmark import runner

    config = _config(tmp_path)
    _save_theme_fixture(config)
    build_dataset(config, run_id="gemini-model-change", limit=1)
    first_client = FakeClient()
    second_client = FakeClient()

    providers = [
        GeminiBenchmarkProvider(
            model_id="gemini-3.5-flash",
            allow_live=True,
            client=first_client,
            sdk_version="2.3.0",
        ),
        GeminiBenchmarkProvider(
            model_id="gemini-3.1-flash-lite",
            allow_live=True,
            client=second_client,
            sdk_version="2.3.0",
        ),
    ]
    monkeypatch.setattr(
        runner, "get_provider", lambda *args, **kwargs: providers.pop(0)
    )

    first = run_benchmark(
        config,
        run_id="gemini-model-change",
        provider_ids=["gemini:gemini-3.5-flash"],
        allow_live=True,
        keyword_modes=["general"],
    )
    second = run_benchmark(
        config,
        run_id="gemini-model-change",
        provider_ids=["gemini:gemini-3.1-flash-lite"],
        allow_live=True,
        keyword_modes=["general"],
    )

    assert first.provider_executions == 1
    assert second.provider_executions == 1
    assert len(first_client.interactions.calls) == 1
    assert len(second_client.interactions.calls) == 1
