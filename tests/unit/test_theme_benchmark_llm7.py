from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.themes.benchmark.dataset import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    build_dataset,
)
from src.providers.llm7 import (
    LLM7_BASE_URL,
    LLM7BenchmarkProvider,
    build_llm7_model_catalog,
    discover_llm7_models,
    estimate_llm7_cost,
    load_approved_llm7_selection,
)
from src.themes.benchmark.contracts import (
    ThemeBenchmarkError,
    read_jsonl,
    stable_hash,
    write_json,
)
from src.themes.benchmark.runner import run_benchmark
from src.themes.theme_inputs import save_theme_inputs

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "theme_benchmark"
    / "matched_lda.csv"
)


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content, finish_reason="stop"):
        self.message = FakeMessage(content)
        self.finish_reason = finish_reason


class FakeCompletion:
    def __init__(self, content=None, usage=None):
        self.id = "chatcmpl-1"
        self.model = "llm7-turbo-json"
        self.created = 1782277907
        self.object = "chat.completion"
        self.system_fingerprint = "fp-test"
        self.usage = usage or {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }
        self.choices = [] if content is None else [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = list(
            responses
            or [
                FakeCompletion(
                    json.dumps(
                        {"themes": [{"name": "Fruit", "keywords": ["apple", "banana"]}]}
                    )
                )
            ]
        )

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = (
            self.responses.pop(0)
            if self.responses
            else FakeCompletion(json.dumps({"themes": []}))
        )
        if isinstance(response, Exception):
            raise response
        return response


class FakeChat:
    def __init__(self, responses=None):
        self.completions = FakeCompletions(responses)


class FakeModels:
    def __init__(self, models):
        self._models = models

    def list(self):
        return {"object": "list", "data": self._models}


class FakeClient:
    def __init__(self, responses=None, models=None):
        self.chat = FakeChat(responses)
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
    result = build_dataset(config, run_id="llm7-request", limit=1)
    return read_jsonl(result["output_dir"] / "requests.jsonl")[0]


def test_llm7_provider_requires_allow_live_before_client_creation():
    with pytest.raises(ThemeBenchmarkError, match="--allow-live"):
        LLM7BenchmarkProvider(
            model_id="llm7-turbo-json", allow_live=False, client=FakeClient()
        )


def test_llm7_provider_requires_key_without_client(monkeypatch):
    monkeypatch.delenv("LLM7_API_KEY", raising=False)

    with pytest.raises(ThemeBenchmarkError, match="LLM7_API_KEY"):
        LLM7BenchmarkProvider(model_id="llm7-turbo-json", allow_live=True)


@pytest.mark.parametrize(
    "selector", ["default", "fast", "turbo", "pro", "codestral-latest"]
)
def test_llm7_provider_rejects_selector_model_ids(selector):
    with pytest.raises(ThemeBenchmarkError, match="exact model ID"):
        LLM7BenchmarkProvider(model_id=selector, allow_live=True, client=FakeClient())


def test_llm7_request_construction_preserves_roles_and_settings(tmp_path):
    request_row = _request(tmp_path)
    client = FakeClient()
    provider = LLM7BenchmarkProvider(
        model_id="llm7-turbo-json",
        allow_live=True,
        client=client,
        sdk_version="2.44.0",
    )

    provider.generate(type("Request", (), request_row)())

    call = client.chat.completions.calls[0]
    assert call["model"] == "llm7-turbo-json"
    assert call["messages"] == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(
                keywords=request_row["keyword_text"]
            ),
        },
    ]
    assert call["temperature"] == 0.0
    assert call["stream"] is False
    assert call["response_format"] == {"type": "json_object"}
    assert "api" not in json.dumps(call).lower()


def test_llm7_model_discovery_normalizes_filters_and_hides_secrets(tmp_path):
    models = [
        {
            "id": "llm7-turbo-json",
            "object": "model",
            "tier": "turbo",
            "pricing": {
                "input": 0.1,
                "output": 0.2,
                "currency": "USD",
                "unit": "1M tokens",
            },
            "modalities": {"input": ["text"], "output": ["text"]},
            "context_window": {"tokens": 8000, "chars": None},
            "stream": True,
            "json_mode": True,
            "reasoning": False,
            "tools_calling": False,
        },
        {
            "id": "llm7-pro-json",
            "tier": "pro",
            "pricing": {
                "input": 0.5,
                "output": 4.5,
                "currency": "USD",
                "unit": "1M tokens",
            },
            "modalities": {"input": ["text"], "output": ["text"]},
            "json_mode": True,
        },
        {
            "id": "llm7-no-json",
            "tier": "turbo",
            "modalities": {"input": ["text"], "output": ["text"]},
            "json_mode": False,
        },
        {
            "id": "default",
            "tier": "turbo",
            "modalities": {"input": ["text"], "output": ["text"]},
            "json_mode": True,
        },
    ]

    path = discover_llm7_models(
        tmp_path,
        allow_live=True,
        client=FakeClient(models=models),
        sdk_version="2.44.0",
    )
    catalog = json.loads(path.read_text(encoding="utf-8"))

    assert catalog["base_url"] == LLM7_BASE_URL
    assert catalog["contains_secrets"] is False
    assert {item["model_id"] for item in catalog["selected_candidates"]} == {
        "llm7-turbo-json",
        "llm7-pro-json",
    }
    rejected = {
        item["model_id"]: item["reason"] for item in catalog["rejected_candidates"]
    }
    assert "json_mode" in rejected["llm7-no-json"]
    assert "selector" in rejected["default"]
    assert "not-persisted" not in json.dumps(catalog)


def test_llm7_catalog_records_ambiguous_candidates():
    catalog = build_llm7_model_catalog(
        [
            {
                "model_id": "turbo-a",
                "tier": "turbo",
                "modalities": {"input": ["text"], "output": ["text"]},
                "json_mode": True,
            },
            {
                "model_id": "turbo-b",
                "tier": "turbo",
                "modalities": {"input": ["text"], "output": ["text"]},
                "json_mode": True,
            },
        ],
        sdk_version="2.44.0",
        retrieved_at="2026-07-08T00:00:00+00:00",
    )

    assert catalog["selected_candidates"] == []
    assert catalog["ambiguous_candidates"][0]["candidate_class"] == "turbo"


def test_llm7_response_normalization_usage_and_cost(tmp_path):
    request_row = _request(tmp_path)
    provider = LLM7BenchmarkProvider(
        model_id="llm7-turbo-json",
        allow_live=True,
        client=FakeClient(),
        sdk_version="2.44.0",
        model_catalog_record={
            "pricing": {
                "input": 0.1,
                "output": 0.2,
                "minimum_request_price_usd": 0.0001,
            }
        },
    )

    result = provider.generate(type("Request", (), request_row)())

    assert result["themes"] == [{"name": "Fruit", "keywords": ["apple", "banana"]}]
    metadata = result["_benchmark_metadata"]
    assert metadata["parsed_successfully"] is True
    assert metadata["schema_valid"] is True
    assert metadata["usage"]["total_tokens"] == 150
    assert metadata["estimated_cost"] == 0.0001
    assert metadata["finish_reason"] == "stop"


@pytest.mark.parametrize(
    "completion,error",
    [
        (FakeCompletion("not-json"), "invalid_json"),
        (FakeCompletion(json.dumps({"themes": [{"name": "Bad"}]})), "schema_invalid"),
        (FakeCompletion(""), "empty_response"),
        (FakeCompletion(None), "empty_response"),
    ],
)
def test_llm7_invalid_responses_fail_clearly(tmp_path, completion, error):
    request_row = _request(tmp_path)
    provider = LLM7BenchmarkProvider(
        model_id="llm7-turbo-json",
        allow_live=True,
        client=FakeClient([completion]),
        sdk_version="2.44.0",
    )

    with pytest.raises(ThemeBenchmarkError, match=error):
        provider.generate(type("Request", (), request_row)())


def test_llm7_retries_rate_limit_and_enforces_request_cap(tmp_path):
    request_row = _request(tmp_path)
    client = FakeClient(
        [
            FakeStatusError("rate limited", 429),
            FakeCompletion(json.dumps({"themes": []})),
        ]
    )
    provider = LLM7BenchmarkProvider(
        model_id="llm7-turbo-json",
        allow_live=True,
        client=client,
        sdk_version="2.44.0",
        sleep_fn=lambda seconds: None,
    )

    result = provider.generate(type("Request", (), request_row)())

    assert result["_benchmark_metadata"]["retries"] == 1
    assert len(client.chat.completions.calls) == 2

    capped = LLM7BenchmarkProvider(
        model_id="llm7-turbo-json",
        allow_live=True,
        client=FakeClient(
            [
                FakeStatusError("rate limited", 429),
                FakeCompletion(json.dumps({"themes": []})),
            ]
        ),
        sdk_version="2.44.0",
        max_outbound_requests=1,
        sleep_fn=lambda seconds: None,
    )
    with pytest.raises(ThemeBenchmarkError, match="request cap exhausted"):
        capped.generate(type("Request", (), request_row)())


def test_llm7_non_retryable_auth_error_is_not_retried(tmp_path):
    request_row = _request(tmp_path)
    client = FakeClient(
        [FakeStatusError("bad key", 401), FakeCompletion(json.dumps({"themes": []}))]
    )
    provider = LLM7BenchmarkProvider(
        model_id="llm7-turbo-json",
        allow_live=True,
        client=client,
        sdk_version="2.44.0",
        sleep_fn=lambda seconds: None,
    )

    with pytest.raises(ThemeBenchmarkError, match="authentication"):
        provider.generate(type("Request", (), request_row)())

    assert len(client.chat.completions.calls) == 1


def test_llm7_cost_estimation_handles_pricing_fields():
    cost = estimate_llm7_cost(
        {"prompt_tokens": 1000, "completion_tokens": 500},
        {"input": 0.5, "output": 4.5, "unit": "1M tokens"},
    )

    assert cost == 0.00275


def test_llm7_runner_cache_reuse_with_fake_client(monkeypatch, tmp_path):
    from src.themes.benchmark import runner

    config = _config(tmp_path)
    _save_theme_fixture(config)
    build_dataset(config, run_id="llm7-cache", limit=1)
    client = FakeClient()
    monkeypatch.setattr(
        runner,
        "get_provider",
        lambda *args, **kwargs: LLM7BenchmarkProvider(
            model_id="llm7-turbo-json",
            allow_live=True,
            client=client,
            sdk_version="2.44.0",
            request_budget=kwargs.get("request_budget"),
        ),
    )

    first = run_benchmark(
        config,
        run_id="llm7-cache",
        provider_ids=["llm7:llm7-turbo-json"],
        allow_live=True,
        keyword_modes=["general"],
    )
    second = run_benchmark(
        config,
        run_id="llm7-cache",
        provider_ids=["llm7:llm7-turbo-json"],
        allow_live=True,
        keyword_modes=["general"],
    )

    assert first.provider_executions == 1
    assert first.outbound_requests == 1
    assert first.cache_hits == 0
    assert second.provider_executions == 0
    assert second.outbound_requests == 0
    assert second.cache_hits == 1
    assert len(client.chat.completions.calls) == 1
    manifest_text = (
        Path(config["output_base_path"])
        / "_experiments"
        / "theme_model_benchmark"
        / "llm7-cache"
        / "manifest.json"
    ).read_text(encoding="utf-8")
    assert "2.44.0" in manifest_text


def test_llm7_runner_defaults_live_provider_to_general_mode(monkeypatch, tmp_path):
    from src.themes.benchmark import runner

    config = _config(tmp_path)
    _save_theme_fixture(config)
    build_dataset(config, run_id="llm7-live-default-mode", limit=1)
    provider = LLM7BenchmarkProvider(
        model_id="llm7-turbo-json",
        allow_live=True,
        client=FakeClient(),
        sdk_version="2.44.0",
    )
    monkeypatch.setattr(runner, "get_provider", lambda *args, **kwargs: provider)

    report = run_benchmark(
        config,
        run_id="llm7-live-default-mode",
        provider_ids=["llm7:llm7-turbo-json"],
        allow_live=True,
    )

    assert report.request_count == 1
    assert (
        report.results_by_provider["llm7__llm7-turbo-json"][0]["keyword_mode"]
        == "general"
    )


def test_llm7_run_requires_saved_approved_selection_artifact(tmp_path):
    config = _config(tmp_path)
    _save_theme_fixture(config)
    result = build_dataset(config, run_id="llm7-no-selection", limit=1)
    write_json(
        result["output_dir"] / "model_catalogs" / "llm7_models.json",
        {
            "schema_version": 1,
            "provider": "llm7",
            "models": [
                {
                    "model_id": "llm7-turbo-json",
                    "tier": "turbo",
                    "modalities": {"input": ["text"], "output": ["text"]},
                    "json_mode": True,
                }
            ],
            "contains_secrets": False,
        },
    )

    with pytest.raises(ThemeBenchmarkError, match="approved selection"):
        run_benchmark(
            config,
            run_id="llm7-no-selection",
            provider_ids=["llm7:llm7-turbo-json"],
            allow_live=True,
            keyword_modes=["general"],
        )


def test_llm7_selection_validation_rejects_models_without_json_or_text(tmp_path):
    root = tmp_path / "run"
    catalog = {
        "schema_version": 1,
        "provider": "llm7",
        "models": [
            {
                "model_id": "llm7-no-json",
                "tier": "turbo",
                "modalities": {"input": ["text"], "output": ["text"]},
                "json_mode": False,
            },
            {
                "model_id": "llm7-no-text",
                "tier": "turbo",
                "modalities": {"input": ["image"], "output": ["text"]},
                "json_mode": True,
            },
        ],
        "contains_secrets": False,
    }
    write_json(root / "model_catalogs" / "llm7_models.json", catalog)
    selection = {
        "schema_version": 1,
        "source_catalog_hash": stable_hash(catalog),
        "user_approved": True,
        "selected_models": [
            {"model_id": "llm7-no-json", "rationale": "test"},
            {"model_id": "llm7-no-text", "rationale": "test"},
        ],
    }
    write_json(root / "model_catalogs" / "llm7_selection.json", selection)

    with pytest.raises(ThemeBenchmarkError, match="JSON mode"):
        load_approved_llm7_selection(root, "llm7-no-json")
    with pytest.raises(ThemeBenchmarkError, match="text input/output"):
        load_approved_llm7_selection(root, "llm7-no-text")
