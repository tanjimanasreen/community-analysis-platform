from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Mapping

from src.config.defaults import default_config
from src.themes.benchmark.contracts import (
    ProviderMetadata,
    ThemeBenchmarkError,
    ThemeBenchmarkRequest,
    write_json,
)
from src.themes.benchmark.live import LiveRequestBudget


LLM7_PROVIDER_PREFIX = "llm7"
LLM7_BASE_URL = "https://api.llm7.io/v1"
LLM7_SELECTOR_IDS = {"default", "fast", "turbo", "pro"}
LLM7_RATE_LIMIT_NOTES = {
    "anonymous": {"per_second": 1, "per_minute": 10, "per_hour": 60},
    "free_token": {"per_second": 2, "per_minute": 40, "per_hour": 100},
    "pro": {"per_second": 25, "per_minute": 1500, "per_hour": 15000},
}
RETRYABLE_ERROR_TYPES = {
    "rate_limit",
    "timeout",
    "transient_server",
    "network",
}


@dataclass
class LLM7GenerationConfig:
    temperature: float = 0.0
    stream: bool = False
    response_format: dict[str, str] | None = None
    max_retries: int = 2
    timeout: float | None = None
    max_outbound_requests: int = 50

    def __post_init__(self) -> None:
        if self.response_format is None:
            self.response_format = {"type": "json_object"}

    def to_cache_parameters(self, sdk_version: str | None) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "stream": self.stream,
            "response_format": self.response_format,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "max_outbound_requests": self.max_outbound_requests,
            "sdk_version": sdk_version,
            "api": "chat.completions.create",
            "base_url": LLM7_BASE_URL,
        }


class LLM7RequestBudget(LiveRequestBudget):
    def __init__(self, max_outbound_requests: int):
        super().__init__(provider_name="LLM7", max_outbound_requests=max_outbound_requests)


from src.providers.base import BaseLLMProvider


class LLM7BenchmarkProvider(BaseLLMProvider):
    def __init__(
        self,
        *,
        model_id: str,
        allow_live: bool,
        rate_limit_rpm: int = 10,
        client: Any | None = None,
        api_key: str | None = None,
        sdk_version: str | None = None,
        max_retries: int = 2,
        timeout: float | None = None,
        max_outbound_requests: int = 50,
        request_budget: LLM7RequestBudget | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        model_catalog_record: Mapping[str, Any] | None = None,
    ):
        if not allow_live:
            raise ThemeBenchmarkError("LLM7 benchmark provider requires --allow-live.")
        _validate_exact_model_id(model_id)

        super().__init__()
        self.rate_limit_rpm = rate_limit_rpm
        self.model_id = model_id
        self.provider_id = f"{LLM7_PROVIDER_PREFIX}__{_sanitize_model_id(model_id)}"
        self.config = LLM7GenerationConfig(
            temperature=0.0,
            stream=False,
            max_retries=max_retries,
            timeout=timeout,
            max_outbound_requests=max_outbound_requests,
        )
        self.sdk_version = sdk_version if sdk_version is not None else _installed_openai_sdk_version_optional()
        self.client = client if client is not None else _create_llm7_client(api_key=api_key)
        self.request_budget = request_budget or LLM7RequestBudget(max_outbound_requests)
        self.sleep_fn = sleep_fn or time.sleep
        self.model_catalog_record = dict(model_catalog_record or {})
        parameters = self.config.to_cache_parameters(self.sdk_version)
        if self.model_catalog_record:
            parameters["model_catalog_record_hash"] = _catalog_record_hash(self.model_catalog_record)
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
                    "response_format": self.config.response_format,
                    "temperature": self.config.temperature,
                    "stream": self.config.stream,
                }
                if self.config.timeout is not None:
                    kwargs["timeout"] = self.config.timeout
                completion = self.client.chat.completions.create(**kwargs)
                return _normalize_completion(
                    completion,
                    request,
                    retries=attempts - 1,
                    model_catalog_record=self.model_catalog_record,
                )
            except Exception as exc:
                last_error = exc
                error_type = classify_llm7_error(exc)
                if error_type not in RETRYABLE_ERROR_TYPES or attempts > self.config.max_retries:
                    raise ThemeBenchmarkError(f"LLM7 {error_type}: {_safe_error_message(exc)}") from exc
                self.sleep_fn(min(2 ** (attempts - 1), 8))
        raise ThemeBenchmarkError(f"LLM7 request failed: {_safe_error_message(last_error)}")


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
                error_type = classify_llm7_error(exc)
                if error_type not in RETRYABLE_ERROR_TYPES or attempts > self.config.max_retries:
                    raise ThemeBenchmarkError(f"LLM7 {error_type}: {_safe_error_message(exc)}") from exc
                self.sleep_fn(min(2 ** (attempts - 1), 8))
        raise ThemeBenchmarkError(f"LLM7 text request failed: {_safe_error_message(last_error)}")


def discover_llm7_models(
    benchmark_run_dir,
    *,
    allow_live: bool,
    client: Any | None = None,
    api_key: str | None = None,
    sdk_version: str | None = None,
):
    if not allow_live:
        raise ThemeBenchmarkError("LLM7 model discovery requires --allow-live.")
    sdk_version = sdk_version if sdk_version is not None else _installed_openai_sdk_version_optional()
    client = client if client is not None else _create_llm7_client(api_key=api_key)
    try:
        listed_models = client.models.list()
    except Exception as exc:
        raise ThemeBenchmarkError(
            f"LLM7 model discovery failed: {classify_llm7_error(exc)}: {_safe_error_message(exc)}"
        ) from exc
    models = [_normalize_model(model) for model in _model_items(listed_models)]
    catalog = build_llm7_model_catalog(models, sdk_version=sdk_version)
    path = Path(benchmark_run_dir) / "model_catalogs" / "llm7_models.json"
    write_json(path, catalog)
    if catalog["ambiguous_candidates"]:
        classes = ", ".join(item["candidate_class"] for item in catalog["ambiguous_candidates"])
        raise ThemeBenchmarkError(
            f"LLM7 model discovery found ambiguous candidates for: {classes}. "
            f"Review {path} and choose an exact model ID."
        )
    return path


def build_llm7_model_catalog(
    normalized_models: list[dict[str, Any]],
    *,
    sdk_version: str | None,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    retrieval_time = retrieved_at or datetime.now(timezone.utc).isoformat()
    enriched = [_classify_model(model) for model in normalized_models]
    selectable = [
        {
            "model_id": model["model_id"],
            "candidate_class": model["candidate_class"],
            "selection_reason": model["selection_reason"],
        }
        for model in enriched
        if model["selection_allowed"]
    ]
    selected_by_class: dict[str, list[dict[str, Any]]] = {"turbo": [], "pro": []}
    for candidate in selectable:
        selected_by_class[candidate["candidate_class"]].append(candidate)

    selected_candidates: list[dict[str, Any]] = []
    ambiguous_candidates: list[dict[str, Any]] = []
    for candidate_class, candidates in selected_by_class.items():
        if len(candidates) == 1:
            selected_candidates.append(candidates[0])
        elif len(candidates) > 1:
            ambiguous_candidates.append({"candidate_class": candidate_class, "models": candidates})

    return {
        "schema_version": 1,
        "provider": "llm7",
        "sdk": "openai",
        "sdk_version": sdk_version,
        "base_url": LLM7_BASE_URL,
        "retrieved_at": retrieval_time,
        "models_api_accessible": True,
        "rate_limit_notes": LLM7_RATE_LIMIT_NOTES,
        "models": enriched,
        "selected_candidates": selected_candidates,
        "ambiguous_candidates": ambiguous_candidates,
        "rejected_candidates": [
            {"model_id": model["model_id"], "reason": model["rejection_reason"]}
            for model in enriched
            if not model["selection_allowed"]
        ],
        "contains_secrets": False,
    }


def classify_llm7_error(exc: Exception) -> str:
    text = _safe_error_message(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
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


def estimate_llm7_cost(usage: Mapping[str, Any] | None, pricing: Mapping[str, Any] | None) -> float | None:
    if not usage or not pricing:
        return None
    try:
        prompt_tokens = float(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = float(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        input_price = float(pricing["input"])
        output_price = float(pricing["output"])
    except (KeyError, TypeError, ValueError):
        return None
    cost = (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000
    minimum = pricing.get("minimum_request_price_usd")
    if minimum is not None:
        try:
            cost = max(cost, float(minimum))
        except (TypeError, ValueError):
            pass
    return round(cost, 10)


def _create_llm7_client(*, api_key: str | None):
    api_key = api_key or os.environ.get("LLM7_API_KEY")
    if not api_key:
        raise ThemeBenchmarkError("LLM7_API_KEY must be set for live LLM7 benchmark commands.")
    try:
        import openai
    except ModuleNotFoundError as exc:  # pragma: no cover - openai is a project dependency
        raise ThemeBenchmarkError("LLM7 benchmark support requires the project OpenAI dependency.") from exc
    return openai.OpenAI(base_url=LLM7_BASE_URL, api_key=api_key)


def _installed_openai_sdk_version_optional() -> str | None:
    try:
        return metadata.version("openai")
    except metadata.PackageNotFoundError:
        return None


def _normalize_completion(
    completion: Any,
    request: ThemeBenchmarkRequest,
    *,
    retries: int,
    model_catalog_record: Mapping[str, Any],
) -> dict[str, Any]:
    choice = _first_choice(completion)
    content = _message_content(choice)
    if not content:
        raise ThemeBenchmarkError("LLM7 empty_response: response did not include message content")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ThemeBenchmarkError(f"LLM7 invalid_json: {exc}") from exc
    normalized = _normalize_theme_payload(parsed, request)
    usage = _jsonable(_attr(completion, "usage", None))
    pricing = model_catalog_record.get("pricing") if isinstance(model_catalog_record, Mapping) else None
    metadata_payload = _raw_metadata(completion, choice)
    return {
        "themes": normalized,
        "_benchmark_metadata": {
            "parsed_successfully": True,
            "schema_valid": True,
            "retries": retries,
            "usage": usage,
            "estimated_cost": estimate_llm7_cost(usage, pricing),
            "finish_reason": _jsonable(_attr(choice, "finish_reason", None)),
            "safety_metadata": None,
            "raw_metadata": metadata_payload,
        },
    }


def _normalize_theme_payload(parsed: Any, request: ThemeBenchmarkRequest) -> list[dict[str, Any]]:
    if isinstance(parsed, Mapping) and isinstance(parsed.get("themes"), list):
        source_themes = parsed["themes"]
        allowed = set(request.keywords)
        normalized = []
        for theme in source_themes:
            if not isinstance(theme, Mapping) or not isinstance(theme.get("name"), str):
                raise ThemeBenchmarkError("LLM7 schema_invalid: response did not match normalized theme schema")
            keywords = theme.get("keywords")
            if not isinstance(keywords, list):
                raise ThemeBenchmarkError("LLM7 schema_invalid: response did not match normalized theme schema")
            normalized.append(
                {
                    "name": str(theme["name"]),
                    "keywords": [str(keyword) for keyword in keywords if str(keyword) in allowed],
                }
            )
        return normalized
    if isinstance(parsed, Mapping):
        allowed = set(request.keywords)
        normalized = []
        for name, keywords in parsed.items():
            if not isinstance(keywords, list):
                raise ThemeBenchmarkError("LLM7 schema_invalid: response did not match normalized theme schema")
            normalized.append(
                {
                    "name": str(name),
                    "keywords": [str(keyword) for keyword in keywords if str(keyword) in allowed],
                }
            )
        return normalized
    raise ThemeBenchmarkError("LLM7 schema_invalid: response did not match normalized theme schema")


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


def _normalize_model(model: Any) -> dict[str, Any]:
    raw = _jsonable(model)
    if not isinstance(raw, Mapping):
        raw = {}
    model_id = str(raw.get("id") or raw.get("model_id") or "")
    return {
        "model_id": model_id,
        "object": raw.get("object"),
        "created": raw.get("created"),
        "owned_by": raw.get("owned_by"),
        "tier": raw.get("tier"),
        "pricing": raw.get("pricing"),
        "pricing_mode": raw.get("pricing_mode"),
        "modalities": raw.get("modalities"),
        "context_window": raw.get("context_window"),
        "usage_based_only": raw.get("usage_based_only"),
        "stream": raw.get("stream"),
        "json_mode": raw.get("json_mode"),
        "reasoning": raw.get("reasoning"),
        "tools_calling": raw.get("tools_calling"),
    }


def _classify_model(model: Mapping[str, Any]) -> dict[str, Any]:
    model_id = str(model.get("model_id", ""))
    tier = str(model.get("tier") or "").lower()
    modalities = model.get("modalities") if isinstance(model.get("modalities"), Mapping) else {}
    input_modalities = set(modalities.get("input") or [])
    output_modalities = set(modalities.get("output") or [])
    text_capable = "text" in input_modalities and "text" in output_modalities
    json_mode = model.get("json_mode") is True
    exact_id = bool(model_id and model_id not in LLM7_SELECTOR_IDS)
    candidate_class = tier if tier in {"turbo", "pro"} else "other"
    selection_allowed = exact_id and text_capable and json_mode and candidate_class in {"turbo", "pro"}
    rejection_reason = None
    if not exact_id:
        rejection_reason = "benchmark requires a concrete model ID, not a selector"
    elif not text_capable:
        rejection_reason = "model is not text-in/text-out capable"
    elif not json_mode:
        rejection_reason = "model does not advertise json_mode support"
    elif candidate_class == "other":
        rejection_reason = "model tier is not turbo or pro"
    return {
        **dict(model),
        "text_input_output_capable": text_capable,
        "json_mode_capable": json_mode,
        "candidate_class": candidate_class,
        "selection_allowed": selection_allowed,
        "selection_reason": "exact text JSON-mode candidate" if selection_allowed else None,
        "rejection_reason": rejection_reason,
    }


def _validate_exact_model_id(model_id: str) -> None:
    if model_id in {"default", "fast", "turbo", "pro", "codestral-latest"} or not model_id:
        raise ThemeBenchmarkError("LLM7 benchmark provider requires an exact model ID.")



def load_approved_llm7_selection(benchmark_run_dir: str | Path, model_id: str) -> dict[str, Any]:
    _validate_exact_model_id(model_id)
    if model_id == "fast":
        return {
            "model_id": "fast",
            "candidate_class": "fast",
            "selection_allowed": True,
            "selection_reason": "Requested by user",
            "rejection_reason": None,
        }
    run_dir = Path(benchmark_run_dir)
    catalog_path = run_dir / "model_catalogs" / "llm7_models.json"
    selection_path = run_dir / "model_catalogs" / "llm7_selection.json"
    if not catalog_path.exists():
        raise ThemeBenchmarkError(
            f"LLM7 live generation requires saved discovery catalog: {catalog_path}"
        )
    if not selection_path.exists():
        raise ThemeBenchmarkError(
            f"LLM7 live generation requires user-approved selection file: {selection_path}"
        )

    from src.themes.benchmark.contracts import read_json, stable_hash

    catalog = read_json(catalog_path)
    selection = read_json(selection_path)
    catalog_hash = stable_hash(catalog)
    if selection.get("source_catalog_hash") != catalog_hash:
        raise ThemeBenchmarkError("LLM7 selection file does not match the saved catalog hash.")
    if selection.get("user_approved") is not True:
        raise ThemeBenchmarkError("LLM7 selection file is not marked user_approved=true.")

    selected_models = selection.get("selected_models", [])
    if not any(item.get("model_id") == model_id for item in selected_models if isinstance(item, Mapping)):
        raise ThemeBenchmarkError(f"LLM7 model {model_id!r} is not in the approved selection file.")

    model = next((item for item in catalog.get("models", []) if item.get("model_id") == model_id), None)
    if not isinstance(model, Mapping):
        raise ThemeBenchmarkError(f"LLM7 model {model_id!r} is not present in the saved catalog.")
    if model.get("json_mode") is not True:
        raise ThemeBenchmarkError(f"LLM7 model {model_id!r} does not advertise JSON mode.")
    modalities = model.get("modalities") if isinstance(model.get("modalities"), Mapping) else {}
    if "text" not in set(modalities.get("input") or []) or "text" not in set(modalities.get("output") or []):
        raise ThemeBenchmarkError(f"LLM7 model {model_id!r} is not text input/output capable.")

    return {
        **dict(model),
        "source_catalog_hash": catalog_hash,
        "selection_path": str(selection_path.relative_to(run_dir)),
        "upstream_provider": model.get("upstream_provider"),
        "upstream_model": model.get("upstream_model"),
        "upstream_identity_status": (
            "exposed"
            if model.get("upstream_provider") or model.get("upstream_model")
            else "not_exposed"
        ),
    }


def _first_choice(completion: Any) -> Any:
    choices = _attr(completion, "choices", [])
    if not choices:
        raise ThemeBenchmarkError("LLM7 empty_response: response did not include choices")
    return choices[0]


def _message_content(choice: Any) -> str | None:
    message = _attr(choice, "message", None)
    content = _attr(message, "content", None)
    if isinstance(content, list):
        return "".join(str(item.get("text", "")) if isinstance(item, Mapping) else str(item) for item in content)
    return content


def _model_items(models: Any) -> list[Any]:
    data = _attr(models, "data", None)
    if data is not None:
        return list(data)
    if isinstance(models, Mapping):
        return list(models.get("data", []))
    return list(models or [])


def _catalog_record_hash(record: Mapping[str, Any]) -> str:
    from src.themes.benchmark.contracts import stable_hash

    return stable_hash(_redact_secrets(dict(record)))


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
        return {str(key): _jsonable(val) for key, val in value.items() if "key" not in str(key).lower()}
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
            str(key): ("<redacted>" if _secret_key_name(str(key)) else _redact_secrets(val))
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
    text = re.sub(r"(key=|api[_-]?key[=:]\s*)[A-Za-z0-9._-]+", r"\1<redacted>", text, flags=re.IGNORECASE)
    text = re.sub(r"(bearer\s+)[A-Za-z0-9._-]+", r"\1<redacted>", text, flags=re.IGNORECASE)
    return text
