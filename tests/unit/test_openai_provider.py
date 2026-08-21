from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from src.providers.base import BaseLLMProvider, ProviderSafetyError, build_theme_request
from src.providers.openai import (
    OpenAIProvider,
    _decode_json_object,
    _extract_content_filter_annotations,
    _extract_text_from_response,
)
from src.themes.benchmark.contracts import ThemeBenchmarkError


class _Responses:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.calls = 0
        self.kwargs = []

    def create(self, **kwargs):
        self.kwargs.append(kwargs)
        self.calls += 1
        response = next(self._responses)
        if isinstance(response, Exception):
            raise response
        return response


class _Client:
    def __init__(self, responses):
        self.responses = _Responses(responses)


def _response(
    text: str,
    *,
    input_tokens: int = 5,
    output_tokens: int = 3,
    reasoning_tokens: int = 0,
    status: str = "completed",
    incomplete_reason: str | None = None,
    response_id: str = "resp_test",
    request_id: str = "req_test",
    output=None,
    model_extra=None,
):
    return SimpleNamespace(
        id=response_id,
        _request_id=request_id,
        model="gpt-5-nano-2025-08-07",
        output_text=text,
        output=[] if output is None else output,
        status=status,
        incomplete_details=(
            SimpleNamespace(reason=incomplete_reason) if incomplete_reason else None
        ),
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            output_tokens_details=SimpleNamespace(reasoning_tokens=reasoning_tokens),
        ),
        model_extra=model_extra or {},
    )


def _provider(responses, *, retries: int = 2) -> OpenAIProvider:
    provider = OpenAIProvider.__new__(OpenAIProvider)
    BaseLLMProvider.__init__(provider)
    provider.model_id = "gpt-5-nano"
    provider._response_retries = retries
    provider._max_output_tokens = 32768
    provider._max_output_tokens_cap = 65536
    provider._reasoning_effort = "low"
    provider._content_filter_retries = 1
    provider._content_filter_retry_delay_seconds = 0.0
    provider._log_content_filter_annotations = True
    provider._client = _Client(responses)
    return provider


def _azure_filter_annotations(*, severity: str = "medium", blocked: bool = False):
    return {
        "content_filters": [
            {
                "source_type": "prompt",
                "blocked": blocked,
                "content_filter_results": {
                    "hate": {"filtered": blocked, "severity": severity},
                    "violence": {"filtered": False, "severity": "safe"},
                },
            }
        ]
    }


class _ContentFilterError(Exception):
    code = "content_filter"
    status_code = 400
    request_id = "req_blocked_prompt"
    body = {"error": {"code": "content_filter"}}


def test_extracts_output_text_shortcut():
    assert _extract_text_from_response(_response('{"themes": []}')) == '{"themes": []}'


def test_decodes_fenced_and_prefixed_json_objects():
    fenced = '```json\n{"themes": [{"name": "Travel", ' '"keyword_indices": [0]}]}\n```'
    assert _decode_json_object(fenced)["themes"][0]["name"] == "Travel"

    prefixed = (
        'Here is the result: {"themes": [{"name": "Policy", '
        '"keyword_indices": []}]} done'
    )
    assert _decode_json_object(prefixed)["themes"][0]["name"] == "Policy"


def test_extracts_azure_content_filter_annotations_from_model_extra():
    annotations = _extract_content_filter_annotations(
        _response(
            '{"themes": []}',
            model_extra=_azure_filter_annotations(severity="medium"),
        )
    )

    assert annotations == [
        {
            "source_type": "prompt",
            "blocked": False,
            "categories": {
                "hate": {"filtered": False, "severity": "medium"},
                "violence": {"filtered": False, "severity": "safe"},
            },
        }
    ]


def test_empty_response_is_retried_and_success_is_returned():
    provider = _provider(
        [
            _response(""),
            _response(
                '{"themes": [{"name": "Travel Policy", "keyword_indices": [0]}]}'
            ),
        ]
    )

    result = provider.generate(build_theme_request(["travel ban"]))

    assert provider._client.responses.calls == 2
    assert result["themes"] == [{"name": "Travel Policy", "keywords": ["travel ban"]}]
    assert result["_benchmark_metadata"]["outbound_attempts"] == 2
    assert result["_benchmark_metadata"]["retries"] == 1


def test_invalid_responses_fail_after_bounded_retries():
    provider = _provider([_response(""), _response("not json")], retries=1)

    with pytest.raises(ThemeBenchmarkError, match="remained invalid"):
        provider.generate(build_theme_request(["travel ban"]))

    assert provider._client.responses.calls == 2


def test_generate_theme_counts_provider_level_retries_and_usage():
    provider = _provider(
        [
            _response(""),
            _response(
                '{"themes": [{"name": "Travel Policy", "keyword_indices": [0]}]}',
                input_tokens=11,
                output_tokens=7,
                reasoning_tokens=4,
            ),
        ]
    )

    result = provider.generate_theme(["travel ban"])

    assert result == {"Travel Policy": ["travel ban"]}
    assert provider.run_metrics["logical_theme_requests"] == 1
    assert provider.run_metrics["outbound_requests"] == 2
    assert provider.run_metrics["calls"] == 1
    assert provider.run_metrics["total_prompt_tokens"] == 11
    assert provider.run_metrics["total_completion_tokens"] == 7


def test_requests_strict_structured_output_with_reasoning_and_safe_budget():
    provider = _provider(
        [_response('{"themes": [{"name": "Policy", "keyword_indices": [0]}]}')]
    )

    provider.generate(build_theme_request(["policy"]))

    request = provider._client.responses.kwargs[0]
    assert request["max_output_tokens"] == 32768
    assert request["reasoning"] == {"effort": "low"}
    output_format = request["text"]["format"]
    assert output_format["type"] == "json_schema"
    assert output_format["strict"] is True
    assert output_format["schema"]["additionalProperties"] is False
    assert (
        output_format["schema"]["properties"]["themes"]["items"]["additionalProperties"]
        is False
    )
    item_properties = output_format["schema"]["properties"]["themes"]["items"][
        "properties"
    ]
    assert "keyword_indices" in item_properties
    assert "keywords" not in item_properties
    assert item_properties["keyword_indices"]["items"]["maximum"] == 0


def test_requests_schema_maximum_tracks_request_keyword_count():
    provider = _provider(
        [_response('{"themes": [{"name": "Policy", "keyword_indices": [11]}]}')]
    )
    keywords = [f"keyword-{index}" for index in range(12)]

    provider.generate(build_theme_request(keywords))

    request = provider._client.responses.kwargs[0]
    index_items = request["text"]["format"]["schema"]["properties"]["themes"][
        "items"
    ]["properties"]["keyword_indices"]["items"]
    assert index_items["minimum"] == 0
    assert index_items["maximum"] == 11


def test_max_output_token_incomplete_response_retries_once_at_bounded_cap():
    provider = _provider(
        [
            _response(
                "",
                status="incomplete",
                incomplete_reason="max_output_tokens",
                output_tokens=32768,
                reasoning_tokens=32760,
            ),
            _response(
                '{"themes": [{"name": "Policy", "keyword_indices": [0]}]}',
                output_tokens=60,
                reasoning_tokens=30,
            ),
        ]
    )

    result = provider.generate(build_theme_request(["policy"]))

    assert result["themes"][0]["name"] == "Policy"
    assert [
        call["max_output_tokens"] for call in provider._client.responses.kwargs
    ] == [32768, 65536]
    assert result["_benchmark_metadata"]["max_output_tokens"] == 65536
    assert result["_benchmark_metadata"]["reasoning_effort"] == "low"


def test_incomplete_at_budget_cap_fails_without_identical_retry():
    provider = _provider(
        [
            _response(
                "",
                status="incomplete",
                incomplete_reason="max_output_tokens",
            ),
            _response(
                "",
                status="incomplete",
                incomplete_reason="max_output_tokens",
            ),
        ]
    )

    with pytest.raises(ThemeBenchmarkError, match="max_output_tokens=65536"):
        provider.generate(build_theme_request(["policy"]))

    assert provider._client.responses.calls == 2


def test_content_filter_incomplete_response_retries_once_and_recovers():
    provider = _provider(
        [
            _response(
                "",
                status="incomplete",
                incomplete_reason="content_filter",
                model_extra=_azure_filter_annotations(blocked=True),
            ),
            _response(
                '{"themes": [{"name": "Policy", "keyword_indices": [0]}]}',
                model_extra=_azure_filter_annotations(severity="medium"),
            ),
        ]
    )

    result = provider.generate(build_theme_request(["policy"]))

    assert provider._client.responses.calls == 2
    assert result["themes"][0]["name"] == "Policy"
    assert result["_benchmark_metadata"]["content_filter_retries"] == 1
    assert (
        result["_benchmark_metadata"]["content_filter_summary"]
        == "prompt:hate:medium:allowed"
    )


def test_persistent_content_filter_fails_after_one_dedicated_retry():
    provider = _provider(
        [
            _response(
                "",
                status="incomplete",
                incomplete_reason="content_filter",
            ),
            _response(
                "",
                status="incomplete",
                incomplete_reason="content_filter",
            ),
        ]
    )

    with pytest.raises(ProviderSafetyError) as exc_info:
        provider.generate(build_theme_request(["policy"]))

    assert exc_info.value.category == "content_filter"
    assert exc_info.value.stage == "completion"
    assert provider._client.responses.calls == 2


def test_http_400_prompt_filter_retries_once_and_recovers():
    provider = _provider(
        [
            _ContentFilterError("blocked"),
            _response('{"themes": [{"name": "Policy", "keyword_indices": [0]}]}'),
        ]
    )

    result = provider.generate(build_theme_request(["policy"]))

    assert provider._client.responses.calls == 2
    assert result["themes"][0]["name"] == "Policy"


def test_persistent_http_prompt_filter_is_typed_after_one_retry():
    provider = _provider(
        [_ContentFilterError("blocked"), _ContentFilterError("blocked")]
    )

    with pytest.raises(ProviderSafetyError) as exc_info:
        provider.generate(build_theme_request(["policy"]))

    assert exc_info.value.category == "content_filter"
    assert exc_info.value.stage == "prompt"
    assert provider._client.responses.calls == 2


def test_failure_log_contains_safe_provider_diagnostics(caplog):
    provider = _provider(
        [
            _response(
                "partial sensitive-looking output",
                status="incomplete",
                incomplete_reason="content_filter",
                input_tokens=44,
                output_tokens=9,
                reasoning_tokens=7,
                response_id="resp_123",
                request_id="req_456",
            ),
            _response(
                "partial sensitive-looking output",
                status="incomplete",
                incomplete_reason="content_filter",
                input_tokens=44,
                output_tokens=9,
                reasoning_tokens=7,
                response_id="resp_123",
                request_id="req_456",
            ),
        ]
    )

    with caplog.at_level(logging.ERROR, logger="src.providers.openai"):
        with pytest.raises(ThemeBenchmarkError):
            provider.generate(build_theme_request(["policy"]))

    text = caplog.text
    assert "openai_theme_incomplete_final" in text
    assert "response_id=resp_123" in text
    assert "request_id=req_456" in text
    assert "incomplete_reason=content_filter" in text
    assert "reasoning_tokens=7" in text
    assert "output_text_chars=32" in text
    assert "partial sensitive-looking output" not in text


def test_allowed_medium_hate_annotation_is_logged_without_raw_payload(caplog):
    provider = _provider(
        [
            _response(
                '{"themes": [{"name": "Hate crime analysis", "keyword_indices": [0]}]}',
                model_extra=_azure_filter_annotations(severity="medium"),
            )
        ]
    )

    with caplog.at_level(logging.INFO, logger="src.providers.openai"):
        provider.generate(build_theme_request(["policy"]))

    assert "openai_theme_content_filter_annotations" in caplog.text
    assert "content_filter_summary=prompt:hate:medium:allowed" in caplog.text
    assert "Hate crime analysis" not in caplog.text


def test_explicit_refusal_is_typed_policy_safety_outcome():
    refusal_output = [
        SimpleNamespace(
            type="message",
            content=[SimpleNamespace(type="refusal", refusal="cannot comply")],
        )
    ]
    provider = _provider([_response("", output=refusal_output)])

    with pytest.raises(ProviderSafetyError) as exc_info:
        provider.generate(build_theme_request(["policy"]))

    assert exc_info.value.category == "policy_refusal"
    assert exc_info.value.stage == "completion"
    assert provider._client.responses.calls == 1
