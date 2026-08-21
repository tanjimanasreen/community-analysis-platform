import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from src.config.settings import get_provider_settings
from src.config.defaults import DEFAULT_CONFIG
from src.themes.benchmark.contracts import (
    ProviderMetadata,
    ThemeBenchmarkError,
    ThemeBenchmarkRequest,
    build_theme_output_json_schema,
    normalize_indexed_theme_payload,
)
from src.themes.benchmark.live import LiveRequestBudget

MISTRAL_PROVIDER_PREFIX = "mistral"
RETRYABLE_ERROR_TYPES = {
    "rate_limit",
    "timeout",
    "transient_server",
    "network",
}


@dataclass
class MistralGenerationConfig:
    temperature: float = 0.0
    stream: bool = False
    response_format: dict[str, str] | None = None
    max_retries: int = 2
    timeout: float | None = None
    max_outbound_requests: int = 50

    def __post_init__(self) -> None:
        if self.response_format is None:
            self.response_format = {"type": "json_object"}

    def to_cache_parameters(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "stream": self.stream,
            "response_format": self.response_format,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "max_outbound_requests": self.max_outbound_requests,
            "api": "chat.completions.create",
            "base_url": (
                str(get_provider_settings().mistral_base_url)
                if get_provider_settings().mistral_base_url
                else None
            ),
        }


class MistralRequestBudget(LiveRequestBudget):
    def __init__(self, max_outbound_requests: int):
        super().__init__(
            provider_name="MISTRAL", max_outbound_requests=max_outbound_requests
        )


from src.providers.base import BaseLLMProvider


class MistralBenchmarkProvider(BaseLLMProvider):
    def __init__(
        self,
        *,
        model_id: str,
        allow_live: bool,
        rate_limit_rpm: int = 40,
        client: Any | None = None,
        api_key: str | None = None,
        max_retries: int = 2,
        timeout: float | None = None,
        max_outbound_requests: int = 50,
        request_budget: MistralRequestBudget | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ):
        if not allow_live:
            raise ThemeBenchmarkError(
                "MISTRAL benchmark provider requires --allow-live."
            )

        super().__init__()
        self.rate_limit_rpm = rate_limit_rpm
        self.model_id = model_id
        self.provider_id = f"{MISTRAL_PROVIDER_PREFIX}__{_sanitize_model_id(model_id)}"
        self.config = MistralGenerationConfig(
            temperature=0.0,
            stream=False,
            max_retries=max_retries,
            timeout=timeout,
            max_outbound_requests=max_outbound_requests,
        )
        self.client = (
            client if client is not None else _create_mistral_client(api_key=api_key)
        )
        self.request_budget = request_budget or MistralRequestBudget(
            max_outbound_requests
        )
        self.sleep_fn = sleep_fn or time.sleep

        parameters = self.config.to_cache_parameters()
        self.metadata = ProviderMetadata(
            provider_id=self.provider_id,
            model_id=self.model_id,
            parameters=parameters,
        )

    def generate(self, request: ThemeBenchmarkRequest) -> dict[str, Any]:
        # Enforce dynamic rate limit
        sleep_duration = 60.0 / max(1, self.rate_limit_rpm)
        self.sleep_fn(sleep_duration)

        attempts = 0
        last_error: Exception | None = None
        while attempts <= self.config.max_retries:
            attempts += 1
            self.request_budget.consume()
            try:
                kwargs = {
                    "model": self.model_id,
                    "messages": [
                        {"role": "system", "content": request.system_prompt},
                        {"role": "user", "content": request.user_prompt},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "theme_output",
                            "schema": build_theme_output_json_schema(
                                len(request.keywords)
                            ),
                        },
                    },
                    "temperature": self.config.temperature,
                    "stream": self.config.stream,
                }
                if self.config.timeout is not None:
                    kwargs["timeout"] = self.config.timeout

                completion = self.client.chat.completions.create(**kwargs)
                return _normalize_completion(completion, request, retries=attempts - 1)
            except Exception as exc:
                last_error = exc
                error_type = classify_mistral_error(exc)
                if (
                    error_type not in RETRYABLE_ERROR_TYPES
                    or attempts > self.config.max_retries
                ):
                    raise ThemeBenchmarkError(
                        f"MISTRAL {error_type}: {_safe_error_message(exc)}"
                    ) from exc
                self.sleep_fn(min(2 ** (attempts - 1), 8))

        raise ThemeBenchmarkError(
            f"MISTRAL request failed: {_safe_error_message(last_error)}"
        )

    def generate_text(self, prompt: str) -> str:
        sleep_duration = 60.0 / max(1, self.rate_limit_rpm)
        self.sleep_fn(sleep_duration)

        attempts = 0
        last_error = None
        while attempts <= self.config.max_retries:
            attempts += 1
            if self.request_budget:
                self.request_budget.consume()
            try:
                kwargs = {
                    "model": self.model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.config.temperature,
                    "stream": False,
                }
                if self.config.timeout is not None:
                    kwargs["timeout"] = self.config.timeout
                completion = self.client.chat.completions.create(**kwargs)
                return _message_content(_first_choice(completion)) or ""
            except Exception as exc:
                last_error = exc
                error_type = classify_mistral_error(exc)
                if (
                    error_type not in RETRYABLE_ERROR_TYPES
                    or attempts > self.config.max_retries
                ):
                    raise ThemeBenchmarkError(
                        f"MISTRAL {error_type}: {_safe_error_message(exc)}"
                    ) from exc
                self.sleep_fn(min(2 ** (attempts - 1), 8))
        raise ThemeBenchmarkError(
            f"MISTRAL text request failed: {_safe_error_message(last_error)}"
        )


def classify_mistral_error(exc: Exception) -> str:
    text = _safe_error_message(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)

    if any(
        marker in text
        for marker in (
            "not allowed by policy",
            "blocked by policy",
            "network egress",
            "outbound request blocked",
        )
    ):
        return "network_policy"

    if "api key" in text or "credential" in text or status == 401:
        return "authentication"
    if "permission" in text or status == 403:
        return "permission"
    if "not found" in text or "invalid model" in text or status == 404:
        return "invalid_model"
    if "rate" in text or status == 429:
        return "rate_limit"
    if "timeout" in text:
        return "timeout"
    if "response_format" in text or "json" in text and "unsupported" in text:
        return "schema_configuration"
    if status in {500, 502, 503, 504}:
        return "transient_server"
    if "network" in text or "connection" in text:
        return "network"
    return "provider_error"


def _create_mistral_client(*, api_key: str | None):
    settings = get_provider_settings()
    resolved_api_key = api_key or (
        settings.mistral_api_key.get_secret_value()
        if settings.mistral_api_key
        else None
    )
    if not resolved_api_key:
        raise ThemeBenchmarkError(
            "MISTRAL_API_KEY must be set for live MISTRAL benchmark commands."
        )
    resolved_base_url = (
        str(settings.mistral_base_url) if settings.mistral_base_url else None
    )
    if not resolved_base_url:
        raise ThemeBenchmarkError("MISTRAL_BASE_URL must be set in .env")
    try:
        import openai
    except ModuleNotFoundError as exc:
        raise ThemeBenchmarkError(
            "MISTRAL benchmark support requires the openai dependency."
        ) from exc
    return openai.OpenAI(base_url=resolved_base_url, api_key=resolved_api_key)


def _normalize_completion(
    completion: Any,
    request: ThemeBenchmarkRequest,
    *,
    retries: int,
) -> dict[str, Any]:
    choice = _first_choice(completion)
    content = _message_content(choice)
    if not content:
        raise ThemeBenchmarkError(
            "MISTRAL empty_response: response did not include message content"
        )
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ThemeBenchmarkError(
            f"MISTRAL invalid_json: {exc} | Content: {content}"
        ) from exc
    normalized = _normalize_theme_payload(parsed, request, content)
    usage = _jsonable(_attr(completion, "usage", None))
    metadata_payload = _raw_metadata(completion, choice)

    usage_dict = usage or {}

    return {
        "themes": normalized,
        "_benchmark_metadata": {
            "parsed_successfully": True,
            "schema_valid": True,
            "retries": retries,
            "usage": usage_dict,
            "estimated_cost": None,  # Not tracked natively here unless cataloged
            "finish_reason": _jsonable(_attr(choice, "finish_reason", None)),
            "safety_metadata": None,
            "raw_metadata": metadata_payload,
        },
    }


def _normalize_theme_payload(
    parsed: Any, request: ThemeBenchmarkRequest, content: str = ""
) -> list[dict[str, Any]]:
    del content
    if not isinstance(parsed, Mapping):
        raise ThemeBenchmarkError(
            "MISTRAL schema_invalid: response did not match normalized theme schema."
        )
    return normalize_indexed_theme_payload(
        parsed, request.keywords, provider_name="MISTRAL"
    )


def _raw_metadata(completion: Any, choice: Any) -> dict[str, Any]:
    return _redact_secrets(
        {
            "id": _attr(completion, "id", None),
            "model": _attr(completion, "model", None),
            "created": _attr(completion, "created", None),
            "object": _attr(completion, "object", None),
            "system_fingerprint": _attr(completion, "system_fingerprint", None),
            "finish_reason": _attr(choice, "finish_reason", None),
            "usage": _jsonable(_attr(completion, "usage", None)),
        }
    )


def _first_choice(completion: Any) -> Any:
    choices = _attr(completion, "choices", [])
    if not choices:
        raise ThemeBenchmarkError(
            "MISTRAL empty_response: response did not include choices"
        )
    return choices[0]


def _message_content(choice: Any) -> str | None:
    message = _attr(choice, "message", None)
    content = _attr(message, "content", None)
    if isinstance(content, list):
        return "".join(
            str(item.get("text", "")) if isinstance(item, Mapping) else str(item)
            for item in content
        )
    return content


def _sanitize_model_id(model_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model_id).strip("_")


def _attr(obj: Any, snake: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(snake, default)
    return getattr(obj, snake, default)


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(val)
            for key, val in value.items()
            if "key" not in str(key).lower()
        }
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return str(value)


def _redact_secrets(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): (
                "<redacted>" if _secret_key_name(str(key)) else _redact_secrets(val)
            )
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    if isinstance(value, str):
        return _safe_error_message(value)
    return value


def _secret_key_name(name: str) -> bool:
    lowered = name.lower()
    return "api_key" in lowered or lowered in {"authorization", "token", "secret"}


def _safe_error_message(exc: Exception | str | None) -> str:
    if exc is None:
        return "unknown error"
    text = str(exc)
    text = re.sub(
        r"(key=|api[_-]?key[=:]\s*)[A-Za-z0-9._-]+",
        r"\1<redacted>",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(bearer\s+)[A-Za-z0-9._-]+", r"\1<redacted>", text, flags=re.IGNORECASE
    )
    return text
