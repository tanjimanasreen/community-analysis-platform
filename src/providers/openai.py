"""OpenAI provider for theme generation.

The provider is intentionally isolated from analytical stages. It consumes the
canonical ordered LDA keyword request and returns validated theme JSON. Routing,
budgets, retries, and reasoning effort are configured through providers.yml.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Mapping
from typing import Any

from src.config.settings import get_provider_settings
from src.providers.base import BaseLLMProvider, ProviderSafetyError
from src.themes.benchmark.contracts import (
    ProviderMetadata,
    ThemeBenchmarkError,
    build_theme_output_json_schema,
    ThemeBenchmarkRequest,
    normalize_indexed_theme_payload,
)

OPENAI_PROVIDER_PREFIX = "openai"
logger = logging.getLogger(__name__)


def _strict_theme_output_schema(keyword_count: int) -> dict:
    """Return a request-bounded theme schema in OpenAI strict-output form."""
    schema = build_theme_output_json_schema(keyword_count)
    schema["additionalProperties"] = False
    items = schema["properties"]["themes"]["items"]
    items["additionalProperties"] = False
    return schema


def _read_value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _extract_text_from_response(response) -> str:
    """Extract output text from OpenAI Responses SDK objects safely."""
    output_text = _read_value(response, "output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = _read_value(response, "output")
    if not isinstance(output, list):
        return ""
    parts: list[str] = []
    for item in output:
        content = _read_value(item, "content")
        if not isinstance(content, list):
            continue
        for block in content:
            text = _read_value(block, "text")
            if isinstance(text, str) and text:
                parts.append(text)
    return "".join(parts)


def _incomplete_reason(response) -> str | None:
    details = _read_value(response, "incomplete_details")
    reason = _read_value(details, "reason") if details is not None else None
    return str(reason) if reason else None


def _extract_content_filter_annotations(response) -> list[dict[str, Any]]:
    """Normalize Microsoft Foundry ``content_filters`` extension fields.

    Azure exposes these annotations through ``response.model_extra`` rather
    than the typed OpenAI SDK response model. Only category, severity, and
    boolean decision fields are retained so logs never contain raw prompts or
    completions.
    """
    model_extra = _read_value(response, "model_extra")
    if not isinstance(model_extra, Mapping):
        return []
    raw_annotations = model_extra.get("content_filters", [])
    if not isinstance(raw_annotations, list):
        return []

    annotations: list[dict[str, Any]] = []
    for raw_annotation in raw_annotations:
        if not isinstance(raw_annotation, Mapping):
            continue
        raw_results = raw_annotation.get("content_filter_results", {})
        categories: dict[str, dict[str, Any]] = {}
        if isinstance(raw_results, Mapping):
            for category, raw_result in sorted(raw_results.items()):
                if not isinstance(raw_result, Mapping):
                    continue
                details: dict[str, Any] = {}
                severity = raw_result.get("severity")
                if severity is not None:
                    details["severity"] = str(severity).lower()
                for field in ("filtered", "detected"):
                    value = raw_result.get(field)
                    if value is not None:
                        details[field] = bool(value)
                if details:
                    categories[str(category)] = details
        annotations.append(
            {
                "source_type": str(raw_annotation.get("source_type", "unknown")),
                "blocked": bool(raw_annotation.get("blocked", False)),
                "categories": categories,
            }
        )
    return annotations


def _content_filter_summary(annotations: list[dict[str, Any]]) -> str:
    """Return a compact, non-sensitive summary for text logs."""
    parts: list[str] = []
    for annotation in annotations:
        source = str(annotation.get("source_type", "unknown"))
        blocked = bool(annotation.get("blocked", False))
        categories = annotation.get("categories", {})
        if not isinstance(categories, Mapping):
            continue
        for category, details in categories.items():
            if not isinstance(details, Mapping):
                continue
            severity = str(details.get("severity", "unknown"))
            filtered = bool(details.get("filtered", False))
            detected = bool(details.get("detected", False))
            notable = blocked or filtered or detected or severity in {"medium", "high"}
            if not notable:
                continue
            outcome = "blocked" if blocked or filtered else "allowed"
            parts.append(f"{source}:{category}:{severity}:{outcome}")
    return ",".join(parts) if parts else "none"


def _api_error_code(error: Exception) -> str | None:
    code = _read_value(error, "code")
    if code:
        return str(code)
    body = _read_value(error, "body")
    if isinstance(body, Mapping):
        nested = body.get("error", body)
        if isinstance(nested, Mapping) and nested.get("code"):
            return str(nested["code"])
    return None


def _api_error_request_id(error: Exception) -> str:
    request_id = _read_value(error, "request_id")
    if request_id:
        return str(request_id)
    response = _read_value(error, "response")
    headers = _read_value(response, "headers")
    if isinstance(headers, Mapping):
        for name in ("x-request-id", "apim-request-id"):
            if headers.get(name):
                return str(headers[name])
    return "unknown"


def _extract_refusal_from_response(response) -> str | None:
    output = _read_value(response, "output")
    if not isinstance(output, list):
        return None
    for item in output:
        content = _read_value(item, "content")
        if not isinstance(content, list):
            continue
        for block in content:
            if _read_value(block, "type") != "refusal":
                continue
            refusal = _read_value(block, "refusal")
            if isinstance(refusal, str) and refusal.strip():
                return refusal.strip()
    return None


def _output_item_types(response) -> list[str]:
    output = _read_value(response, "output")
    if not isinstance(output, list):
        return []
    values: list[str] = []
    for item in output:
        item_type = _read_value(item, "type")
        if item_type:
            values.append(str(item_type))
        content = _read_value(item, "content")
        if isinstance(content, list):
            values.extend(
                str(block_type)
                for block in content
                if (block_type := _read_value(block, "type"))
            )
    return values


def _strip_markdown_fence(content: str) -> str:
    text = content.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].strip().lower() in {"```", "```json"}:
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _decode_json_object(content: str) -> dict:
    """Decode one JSON object, tolerating a fenced or prefixed response."""
    text = _strip_markdown_fence(content)
    if not text:
        raise ThemeBenchmarkError("OpenAI returned an empty theme response.")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as first_error:
        decoder = json.JSONDecoder()
        payload = None
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                payload = candidate
                break
        if payload is None:
            raise ThemeBenchmarkError(
                "OpenAI returned non-JSON theme output " f"(characters={len(text)})."
            ) from first_error
    if not isinstance(payload, dict):
        raise ThemeBenchmarkError("OpenAI theme output must be a JSON object.")
    return payload


def _normalize_theme_payload(parsed: dict, allowed_keywords: list[str]) -> list[dict]:
    """Validate the V2 wire schema and reconstruct exact request keywords."""
    return normalize_indexed_theme_payload(
        parsed, allowed_keywords, provider_name="OpenAI"
    )


def _extract_usage_from_response(response) -> dict[str, int]:
    """Normalize token usage, including hidden reasoning tokens when exposed."""
    usage = _read_value(response, "usage")
    if usage is None:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
        }

    def read(source: Any, *names: str) -> int:
        for name in names:
            value = _read_value(source, name)
            if value is not None:
                return int(value)
        return 0

    prompt_tokens = read(usage, "input_tokens", "prompt_tokens")
    completion_tokens = read(usage, "output_tokens", "completion_tokens")
    output_details = _read_value(usage, "output_tokens_details")
    reasoning_tokens = read(output_details, "reasoning_tokens")
    total_tokens = read(usage, "total_tokens") or prompt_tokens + completion_tokens
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
    }


def _safe_response_diagnostics(
    response,
    *,
    content: str,
    request: ThemeBenchmarkRequest,
    attempt: int,
    attempts: int,
    max_output_tokens: int,
    reasoning_effort: str | None,
    elapsed_ms: float,
) -> dict[str, Any]:
    """Build non-sensitive diagnostics suitable for terminal and CloudWatch logs."""
    usage = _extract_usage_from_response(response)
    content_filter_annotations = _extract_content_filter_annotations(response)
    return {
        "provider": "openai",
        "model": str(_read_value(response, "model") or "unknown"),
        "configured_model": str(_read_value(response, "model") or "unknown"),
        "response_id": str(_read_value(response, "id") or "unknown"),
        "request_id": str(_read_value(response, "_request_id") or "unknown"),
        "status": str(_read_value(response, "status") or "unknown"),
        "incomplete_reason": _incomplete_reason(response) or "none",
        "attempt": attempt,
        "attempts": attempts,
        "max_output_tokens": max_output_tokens,
        "reasoning_effort": reasoning_effort or "default",
        "output_text_chars": len(content),
        "output_text_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()[:12],
        "output_item_types": ",".join(_output_item_types(response)) or "none",
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "reasoning_tokens": usage["reasoning_tokens"],
        "total_tokens": usage["total_tokens"],
        "elapsed_ms": round(elapsed_ms, 2),
        "input_hash": request.input_hash[:12],
        "prompt_hash": request.prompt_hash[:12],
        "content_filter_annotation_count": len(content_filter_annotations),
        "content_filter_summary": _content_filter_summary(content_filter_annotations),
        "content_filter_annotations": content_filter_annotations,
    }


def _safe_api_error_diagnostics(
    error: Exception,
    *,
    request: ThemeBenchmarkRequest,
    configured_model: str,
    attempt: int,
    attempts: int,
    max_output_tokens: int,
    reasoning_effort: str | None,
    elapsed_ms: float,
) -> dict[str, Any]:
    return {
        "provider": "openai",
        "model": "unknown",
        "configured_model": configured_model,
        "response_id": "unknown",
        "request_id": _api_error_request_id(error),
        "status": "http_error",
        "http_status": int(_read_value(error, "status_code", 0) or 0),
        "error_code": _api_error_code(error) or "unknown",
        "error_type": type(error).__name__,
        "attempt": attempt,
        "attempts": attempts,
        "max_output_tokens": max_output_tokens,
        "reasoning_effort": reasoning_effort or "default",
        "elapsed_ms": round(elapsed_ms, 2),
        "input_hash": request.input_hash[:12],
        "prompt_hash": request.prompt_hash[:12],
        "content_filter_annotation_count": 0,
        "content_filter_summary": "unavailable",
        "content_filter_annotations": [],
    }


def _diagnostic_message(event: str, diagnostics: Mapping[str, Any]) -> str:
    return (
        event
        + " "
        + " ".join(
            f"{key}={diagnostics[key]}"
            for key in sorted(diagnostics)
            if not isinstance(diagnostics[key], (Mapping, list, tuple, set))
        )
    )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Responses provider for non-benchmark theme generation."""

    def __init__(
        self,
        *,
        model_id: str = "gpt-5-nano",
        api_key: str | None = None,
        base_url: str | None = None,
        rate_limit_rpm: int = 60,
        timeout: float = 60.0,
        max_retries: int = 0,
        max_output_tokens: int = 32768,
        max_output_tokens_cap: int = 65536,
        reasoning_effort: str | None = "low",
        content_filter_retries: int = 1,
        content_filter_retry_delay_seconds: float = 8.0,
        log_content_filter_annotations: bool = True,
    ) -> None:
        super().__init__()

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise ImportError("openai package is required for OpenAIProvider") from exc

        settings = get_provider_settings()
        self._api_key = api_key or (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key
            else None
        )
        if not self._api_key:
            raise ThemeBenchmarkError(
                "OPENAI_API_KEY is required for live OpenAI requests."
            )

        resolved_base_url = base_url or (
            str(settings.openai_base_url) if settings.openai_base_url else None
        )

        self.model_id = model_id
        self.rate_limit_rpm = rate_limit_rpm
        self._response_retries = max(0, int(max_retries))
        self._max_output_tokens = max(256, int(max_output_tokens))
        self._max_output_tokens_cap = max(
            self._max_output_tokens, int(max_output_tokens_cap)
        )
        self._reasoning_effort = (
            str(reasoning_effort).strip() if reasoning_effort else None
        )
        self._content_filter_retries = max(0, int(content_filter_retries))
        self._content_filter_retry_delay_seconds = max(
            0.0, float(content_filter_retry_delay_seconds)
        )
        self._log_content_filter_annotations = bool(log_content_filter_annotations)
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=resolved_base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        parameters: dict[str, Any] = {
            "api": "responses",
            "max_output_tokens": self._max_output_tokens,
            "max_output_tokens_cap": self._max_output_tokens_cap,
            "structured_output": "json_schema_strict",
        }
        if self._reasoning_effort:
            parameters["reasoning_effort"] = self._reasoning_effort
        self.metadata = ProviderMetadata(
            provider_id=f"{OPENAI_PROVIDER_PREFIX}__{model_id}",
            model_id=model_id,
            parameters=parameters,
        )

    def generate(self, request: ThemeBenchmarkRequest) -> dict:
        combined_input = f"{request.system_prompt}\n\n{request.user_prompt}"
        attempts = 1 + self._response_retries + self._content_filter_retries
        token_budget = self._max_output_tokens
        last_error: Exception | None = None
        response_retries_used = 0
        content_filter_retries_used = 0

        for attempt in range(1, attempts + 1):
            request_kwargs: dict[str, Any] = {
                "model": self.model_id,
                "input": combined_input,
                "max_output_tokens": token_budget,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "theme_output",
                        "strict": True,
                        "schema": _strict_theme_output_schema(len(request.keywords)),
                    }
                },
            }
            if self._reasoning_effort:
                request_kwargs["reasoning"] = {"effort": self._reasoning_effort}

            started = time.monotonic()
            try:
                response = self._client.responses.create(**request_kwargs)
            except Exception as exc:
                elapsed_ms = (time.monotonic() - started) * 1000.0
                diagnostics = _safe_api_error_diagnostics(
                    exc,
                    request=request,
                    configured_model=self.model_id,
                    attempt=attempt,
                    attempts=attempts,
                    max_output_tokens=token_budget,
                    reasoning_effort=self._reasoning_effort,
                    elapsed_ms=elapsed_ms,
                )
                if (
                    diagnostics["error_code"] == "content_filter"
                    and content_filter_retries_used < self._content_filter_retries
                ):
                    content_filter_retries_used += 1
                    retry_diagnostics = dict(diagnostics)
                    retry_diagnostics["retry_delay_seconds"] = (
                        self._content_filter_retry_delay_seconds
                    )
                    logger.warning(
                        _diagnostic_message(
                            "openai_theme_prompt_filter_retry", retry_diagnostics
                        ),
                        extra={"provider_diagnostics": retry_diagnostics},
                    )
                    if self._content_filter_retry_delay_seconds:
                        time.sleep(self._content_filter_retry_delay_seconds)
                    continue
                if diagnostics["error_code"] == "content_filter":
                    logger.error(
                        _diagnostic_message(
                            "openai_theme_prompt_filter_final", diagnostics
                        ),
                        extra={"provider_diagnostics": diagnostics},
                    )
                    raise ProviderSafetyError(
                        category="content_filter",
                        stage="prompt",
                        provider_id="openai",
                        model_id=self.model_id,
                        input_hash=request.input_hash,
                        prompt_hash=request.prompt_hash,
                        diagnostics=dict(diagnostics),
                    ) from exc
                raise
            elapsed_ms = (time.monotonic() - started) * 1000.0
            content = _extract_text_from_response(response)
            diagnostics = _safe_response_diagnostics(
                response,
                content=content,
                request=request,
                attempt=attempt,
                attempts=attempts,
                max_output_tokens=token_budget,
                reasoning_effort=self._reasoning_effort,
                elapsed_ms=elapsed_ms,
            )
            diagnostics["configured_model"] = self.model_id

            status = diagnostics["status"]
            incomplete_reason = diagnostics["incomplete_reason"]
            refusal = _extract_refusal_from_response(response)

            logger.debug(
                _diagnostic_message("openai_theme_response", diagnostics),
                extra={"provider_diagnostics": diagnostics},
            )
            if (
                self._log_content_filter_annotations
                and diagnostics["content_filter_summary"] != "none"
            ):
                logger.info(
                    _diagnostic_message(
                        "openai_theme_content_filter_annotations", diagnostics
                    ),
                    extra={"provider_diagnostics": diagnostics},
                )

            if refusal:
                logger.error(
                    _diagnostic_message("openai_theme_refusal", diagnostics),
                    extra={"provider_diagnostics": diagnostics},
                )
                raise ProviderSafetyError(
                    category="policy_refusal",
                    stage="completion",
                    provider_id="openai",
                    model_id=self.model_id,
                    input_hash=request.input_hash,
                    prompt_hash=request.prompt_hash,
                    diagnostics=dict(diagnostics),
                )

            if status == "incomplete":
                last_error = ThemeBenchmarkError(
                    "OpenAI returned an incomplete theme response. "
                    + _diagnostic_message("diagnostics", diagnostics)
                )
                if (
                    incomplete_reason == "max_output_tokens"
                    and response_retries_used < self._response_retries
                ):
                    next_budget = min(token_budget * 2, self._max_output_tokens_cap)
                    if next_budget > token_budget:
                        response_retries_used += 1
                        retry_diagnostics = dict(diagnostics)
                        retry_diagnostics["next_max_output_tokens"] = next_budget
                        logger.warning(
                            _diagnostic_message(
                                "openai_theme_incomplete_retry", retry_diagnostics
                            ),
                            extra={"provider_diagnostics": retry_diagnostics},
                        )
                        token_budget = next_budget
                        continue
                if (
                    incomplete_reason == "content_filter"
                    and content_filter_retries_used < self._content_filter_retries
                ):
                    content_filter_retries_used += 1
                    retry_diagnostics = dict(diagnostics)
                    retry_diagnostics["retry_delay_seconds"] = (
                        self._content_filter_retry_delay_seconds
                    )
                    logger.warning(
                        _diagnostic_message(
                            "openai_theme_content_filter_retry", retry_diagnostics
                        ),
                        extra={"provider_diagnostics": retry_diagnostics},
                    )
                    if self._content_filter_retry_delay_seconds:
                        time.sleep(self._content_filter_retry_delay_seconds)
                    continue
                logger.error(
                    _diagnostic_message("openai_theme_incomplete_final", diagnostics),
                    extra={"provider_diagnostics": diagnostics},
                )
                if incomplete_reason == "content_filter":
                    raise ProviderSafetyError(
                        category="content_filter",
                        stage="completion",
                        provider_id="openai",
                        model_id=self.model_id,
                        input_hash=request.input_hash,
                        prompt_hash=request.prompt_hash,
                        diagnostics=dict(diagnostics),
                    )
                raise last_error

            try:
                parsed = _decode_json_object(content)
                themes = _normalize_theme_payload(parsed, request.keywords)
            except ThemeBenchmarkError as exc:
                last_error = exc
                if response_retries_used >= self._response_retries:
                    logger.error(
                        _diagnostic_message("openai_theme_invalid_final", diagnostics),
                        extra={"provider_diagnostics": diagnostics},
                    )
                    raise ThemeBenchmarkError(
                        "OpenAI theme response remained invalid after "
                        f"{attempts} attempt(s). "
                        + _diagnostic_message("diagnostics", diagnostics)
                    ) from exc
                response_retries_used += 1
                logger.warning(
                    _diagnostic_message("openai_theme_invalid_retry", diagnostics),
                    extra={"provider_diagnostics": diagnostics},
                )
                continue

            usage_dict = _extract_usage_from_response(response)
            if attempt > 1:
                logger.info(
                    _diagnostic_message("openai_theme_retry_recovered", diagnostics),
                    extra={"provider_diagnostics": diagnostics},
                )
            return {
                "themes": themes,
                "_benchmark_metadata": {
                    "parsed_successfully": True,
                    "schema_valid": True,
                    "usage": usage_dict,
                    "finish_reason": status,
                    "incomplete_reason": (
                        None if incomplete_reason == "none" else incomplete_reason
                    ),
                    "max_output_tokens": token_budget,
                    "reasoning_effort": self._reasoning_effort,
                    "response_id": diagnostics["response_id"],
                    "request_id": diagnostics["request_id"],
                    "outbound_attempts": attempt,
                    "retries": attempt - 1,
                    "content_filter_retries": content_filter_retries_used,
                    "content_filter_summary": diagnostics["content_filter_summary"],
                    "content_filter_annotations": diagnostics[
                        "content_filter_annotations"
                    ],
                },
            }

        raise ThemeBenchmarkError("OpenAI theme generation failed.") from last_error

    def generate_text(self, prompt: str) -> str:
        response = self._client.responses.create(
            model=self.model_id,
            input=prompt,
        )
        return _extract_text_from_response(response)
