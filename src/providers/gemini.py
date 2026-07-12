from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Mapping

from src.config.defaults import default_config
from src.themes.benchmark.contracts import (
    THEME_OUTPUT_JSON_SCHEMA,
    ProviderMetadata,
    ThemeBenchmarkError,
    ThemeBenchmarkRequest,
    write_json,
)
from src.themes.benchmark.live import LiveRequestBudget


GEMINI_PROVIDER_PREFIX = "gemini"
GEMINI_INSTALL_MESSAGE = (
    "Gemini benchmark support requires the optional dependency. Install it with: "
    ".venv/bin/python -m pip install -e '.[benchmark-gemini]'"
)
DOCUMENTED_INTERACTIONS_MODELS = {
    "gemini-3.1-flash-lite",
    "Gemma 4 31B",
    "gemini-3.5-flash",
}
RETRYABLE_ERROR_TYPES = {
    "rate_limit",
    "timeout",
    "transient_server",
    "network",
}


@dataclass
class GeminiGenerationConfig:
    temperature: float = 0.0
    store: bool = False
    max_retries: int = 2
    timeout: float | None = None
    max_outbound_requests: int = 50

    def to_cache_parameters(self, sdk_version: str | None) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "store": self.store,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "max_outbound_requests": self.max_outbound_requests,
            "sdk_version": sdk_version,
            "api": "interactions.create",
            "response_mime_type": "application/json",
        }


class GeminiRequestBudget(LiveRequestBudget):
    def __init__(self, max_outbound_requests: int):
        super().__init__(provider_name="Gemini", max_outbound_requests=max_outbound_requests)


from src.providers.base import BaseLLMProvider


class GeminiBenchmarkProvider(BaseLLMProvider):
    def __init__(
        self,
        *,
        model_id: str,
        allow_live: bool,
        rate_limit_rpm: int = 15,
        client: Any | None = None,
        api_key: str | None = None,
        sdk_version: str | None = None,
        max_retries: int = 2,
        timeout: float | None = None,
        max_outbound_requests: int = 50,
        request_budget: GeminiRequestBudget | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ):
        if not model_id or model_id.startswith("models/") or "latest" in model_id:
            raise ThemeBenchmarkError("Gemini benchmark provider requires an exact non-latest model ID.")
        if not allow_live:
            raise ThemeBenchmarkError("Gemini benchmark provider requires --allow-live.")

        super().__init__()
        self.rate_limit_rpm = rate_limit_rpm
        self.model_id = model_id
        self.provider_id = f"{GEMINI_PROVIDER_PREFIX}__{_sanitize_model_id(model_id)}"
        self.config = GeminiGenerationConfig(
            temperature=0.0,
            store=False,
            max_retries=max_retries,
            timeout=timeout,
            max_outbound_requests=max_outbound_requests,
        )
        self.sdk_version = sdk_version if sdk_version is not None else _installed_sdk_version_optional(client)
        self.client = client if client is not None else _create_gemini_client(api_key=api_key)
        self.request_budget = request_budget or GeminiRequestBudget(max_outbound_requests)
        self.sleep_fn = sleep_fn or time.sleep
        self.metadata = ProviderMetadata(
            provider_id=self.provider_id,
            model_id=self.model_id,
            parameters=self.config.to_cache_parameters(self.sdk_version),
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
                interaction = self.client.interactions.create(
                    model=self.model_id,
                    system_instruction=request.system_prompt,
                    input=request.user_prompt,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": THEME_OUTPUT_JSON_SCHEMA,
                    },
                    store=self.config.store,
                    generation_config={"temperature": self.config.temperature},
                    timeout=self.config.timeout,
                )
                return _normalize_interaction(interaction, request, retries=attempts - 1)
            except Exception as exc:
                last_error = exc
                error_type = classify_gemini_error(exc)
                if error_type not in RETRYABLE_ERROR_TYPES or attempts > self.config.max_retries:
                    raise ThemeBenchmarkError(f"Gemini {error_type}: {_safe_error_message(exc)}") from exc
                self.sleep_fn(min(2 ** (attempts - 1), 8))
        raise ThemeBenchmarkError(f"Gemini request failed: {_safe_error_message(last_error)}")


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
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config={"temperature": self.config.temperature},
                )
                return response.text
            except Exception as exc:
                last_error = exc
                error_type = classify_gemini_error(exc)
                if error_type not in RETRYABLE_ERROR_TYPES or attempts > self.config.max_retries:
                    raise ThemeBenchmarkError(f"Gemini {error_type}: {_safe_error_message(exc)}") from exc
                self.sleep_fn(min(2 ** (attempts - 1), 8))
        raise ThemeBenchmarkError(f"Gemini text request failed: {_safe_error_message(last_error)}")

def discover_gemini_models(
    benchmark_run_dir: str | Path,
    *,
    allow_live: bool,
    client: Any | None = None,
    api_key: str | None = None,
    sdk_version: str | None = None,
) -> Path:
    if not allow_live:
        raise ThemeBenchmarkError("Gemini model discovery requires --allow-live.")
    sdk_version = sdk_version if sdk_version is not None else _installed_sdk_version_optional(client)
    client = client if client is not None else _create_gemini_client(api_key=api_key)
    try:
        listed_models = client.models.list()
    except Exception as exc:
        raise ThemeBenchmarkError(
            f"Gemini model discovery failed: {classify_gemini_error(exc)}: {_safe_error_message(exc)}"
        ) from exc
    models = [_normalize_model(model) for model in listed_models]
    catalog = build_gemini_model_catalog(models, sdk_version=sdk_version)
    path = Path(benchmark_run_dir) / "model_catalogs" / "gemini_models.json"
    write_json(path, catalog)
    return path


def build_gemini_model_catalog(
    normalized_models: list[dict[str, Any]],
    *,
    sdk_version: str | None,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    retrieval_time = retrieved_at or datetime.now(timezone.utc).isoformat()
    enriched = []
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for model in normalized_models:
        item = _classify_model(model)
        enriched.append(item)
        if item["candidate_class"] in {"flash_lite", "flash"} and item["selection_allowed"]:
            selected.append(
                {
                    "model_id": item["model_id"],
                    "candidate_class": item["candidate_class"],
                    "selection_reason": item["selection_reason"],
                }
            )
        else:
            rejected.append(
                {
                    "model_id": item["model_id"],
                    "reason": item["rejection_reason"],
                }
            )

    selected_by_class: dict[str, list[dict[str, Any]]] = {"flash_lite": [], "flash": []}
    for candidate in selected:
        selected_by_class[candidate["candidate_class"]].append(candidate)

    final_selected = []
    ambiguity = []
    for candidate_class, candidates in selected_by_class.items():
        if len(candidates) == 1:
            final_selected.append(candidates[0])
        elif len(candidates) > 1:
            ambiguity.append({"candidate_class": candidate_class, "models": candidates})

    return {
        "schema_version": 1,
        "provider": "gemini",
        "sdk_version": sdk_version,
        "retrieved_at": retrieval_time,
        "models_api_accessible": True,
        "models": enriched,
        "selected_candidates": final_selected,
        "ambiguous_candidates": ambiguity,
        "rejected_candidates": rejected,
        "contains_secrets": False,
    }


def classify_gemini_error(exc: Exception) -> str:
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
    if "schema" in text:
        return "schema_configuration"
    if status in {500, 502, 503, 504}:
        return "transient_server"
    if "network" in text or "connection" in text:
        return "network"
    return "provider_error"


def _create_gemini_client(*, api_key: str | None):
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ThemeBenchmarkError("GEMINI_API_KEY must be set for live Gemini benchmark commands.")
    try:
        from google import genai
    except ModuleNotFoundError as exc:
        raise ThemeBenchmarkError(GEMINI_INSTALL_MESSAGE) from exc
    return genai.Client(api_key=api_key)


def _installed_sdk_version_optional(client: Any | None = None) -> str | None:
    if client is not None:
        return "fake-client"
    try:
        return metadata.version("google-genai")
    except metadata.PackageNotFoundError:
        return None


def _normalize_interaction(
    interaction: Any,
    request: ThemeBenchmarkRequest,
    *,
    retries: int,
) -> dict[str, Any]:
    output_text = getattr(interaction, "output_text", None)
    if not output_text:
        raise ThemeBenchmarkError("Gemini empty_response: response did not include output_text")
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise ThemeBenchmarkError(f"Gemini invalid_json: {exc}") from exc
    if not _schema_valid(parsed):
        raise ThemeBenchmarkError("Gemini schema_invalid: response did not match normalized theme schema")
    allowed = set(request.keywords)
    normalized_themes = []
    for theme in parsed.get("themes", []):
        normalized_themes.append(
            {
                "name": str(theme["name"]),
                "keywords": [
                    str(keyword)
                    for keyword in theme.get("keywords", [])
                    if str(keyword) in allowed
                ],
            }
        )
    metadata_payload = _raw_metadata(interaction)
    return {
        "themes": normalized_themes,
        "_benchmark_metadata": {
            "parsed_successfully": True,
            "schema_valid": True,
            "retries": retries,
            "usage": metadata_payload.get("usage"),
            "finish_reason": metadata_payload.get("finish_reason"),
            "safety_metadata": metadata_payload.get("safety_metadata"),
            "raw_metadata": metadata_payload,
        },
    }


def _raw_metadata(interaction: Any) -> dict[str, Any]:
    usage = _jsonable(getattr(interaction, "usage_metadata", None) or getattr(interaction, "usage", None))
    finish_reason = _jsonable(getattr(interaction, "finish_reason", None))
    safety = _jsonable(getattr(interaction, "safety_metadata", None) or getattr(interaction, "safety_ratings", None))
    return {
        "interaction_id": getattr(interaction, "id", None),
        "status": getattr(interaction, "status", None),
        "usage": usage,
        "finish_reason": finish_reason,
        "safety_metadata": safety,
    }


def _schema_valid(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    themes = value.get("themes")
    if not isinstance(themes, list):
        return False
    for theme in themes:
        if not isinstance(theme, Mapping):
            return False
        if not isinstance(theme.get("name"), str):
            return False
        if not isinstance(theme.get("keywords"), list):
            return False
    return True


def _normalize_model(model: Any) -> dict[str, Any]:
    raw_name = _attr(model, "name", "")
    exact_model_id = str(raw_name).removeprefix("models/")
    supported = _attr(model, "supported_actions", None)
    if supported is None:
        supported = _attr(model, "supportedGenerationMethods", None)
    if supported is None:
        supported = _attr(model, "supported_generation_methods", [])
    return {
        "model_id": exact_model_id,
        "resource_name": raw_name,
        "display_name": _attr(model, "display_name", _attr(model, "displayName", "")),
        "description": _attr(model, "description", ""),
        "version": _attr(model, "version", ""),
        "base_model_id": _attr(model, "base_model_id", _attr(model, "baseModelId", "")),
        "input_token_limit": _attr(model, "input_token_limit", _attr(model, "inputTokenLimit", None)),
        "output_token_limit": _attr(model, "output_token_limit", _attr(model, "outputTokenLimit", None)),
        "supported_actions": list(supported or []),
    }


def _classify_model(model: Mapping[str, Any]) -> dict[str, Any]:
    model_id = str(model.get("model_id", ""))
    lower = model_id.lower()
    generate_content = "generateContent" in model.get("supported_actions", [])
    is_latest = "latest" in lower
    is_preview = "preview" in lower or "preview" in str(model.get("description", "")).lower()
    is_experimental = "experimental" in lower or "exp" in lower
    is_flash_lite = "flash-lite" in lower
    is_flash = "flash" in lower and not is_flash_lite
    interactions_status = (
        "documented" if model_id in DOCUMENTED_INTERACTIONS_MODELS else "unknown"
    )
    candidate_class = "flash_lite" if is_flash_lite else "flash" if is_flash else "other"
    selection_allowed = (
        generate_content
        and interactions_status == "documented"
        and not is_latest
        and not is_preview
        and not is_experimental
        and candidate_class in {"flash_lite", "flash"}
    )
    rejection_reason = None
    if not generate_content:
        rejection_reason = "model does not advertise generateContent in Models API"
    elif interactions_status != "documented":
        rejection_reason = "Interactions support is unknown; compatibility probe required before selection"
    elif is_latest:
        rejection_reason = "moving latest alias excluded"
    elif is_preview:
        rejection_reason = "preview model excluded"
    elif is_experimental:
        rejection_reason = "experimental model excluded"
    elif candidate_class == "other":
        rejection_reason = "not a Flash or Flash-Lite text candidate"
    return {
        **dict(model),
        "models_api_accessible": True,
        "generate_content_capable": generate_content,
        "interactions_support_status": interactions_status,
        "is_latest_alias": is_latest,
        "is_preview": is_preview,
        "is_experimental": is_experimental,
        "candidate_class": candidate_class,
        "selection_allowed": selection_allowed,
        "selection_reason": "stable documented Interactions-capable candidate" if selection_allowed else None,
        "rejection_reason": rejection_reason,
    }


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


def _safe_error_message(exc: Exception | None) -> str:
    if exc is None:
        return "unknown error"
    text = str(exc)
    return re.sub(r"(key=|api[_-]?key[=:]\s*)[A-Za-z0-9._-]+", r"\1<redacted>", text, flags=re.IGNORECASE)
