"""Base class for all LLM providers in this project."""

from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
import json
import threading
import time
from typing import Any, Callable, TypeVar

from src.themes.benchmark.contracts import (
    OUTPUT_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    THEME_PROMPT_CONTRACT_VERSION,
    ProviderMetadata,
    ThemeBenchmarkError,
    build_theme_output_json_schema,
    ThemeBenchmarkRequest,
)

_F = TypeVar("_F", bound=Callable[..., Any])


def _optional_mlflow_trace(name: str):
    """Use MLflow tracing when the optional tracking extra is installed."""
    try:
        import mlflow
    except ModuleNotFoundError:

        def decorator(func: _F) -> _F:
            return func

        return decorator
    return mlflow.trace(name=name)


def build_theme_request(keywords: list[str]) -> ThemeBenchmarkRequest:
    """Build the canonical, rank-preserving request used by providers and cache."""
    from src.themes.benchmark.dataset import (
        RAW_SYSTEM_TEMPLATE,
        RAW_USER_TEMPLATE,
        format_indexed_keywords_for_prompt,
        get_jinja_env,
    )

    keyword_text = json.dumps(keywords, ensure_ascii=False)
    output_schema = build_theme_output_json_schema(len(keywords))
    env = get_jinja_env()
    system_prompt = env.get_template("system.jinja2").render(
        json_schema=json.dumps(output_schema, indent=2)
    )
    user_prompt = env.get_template("user.jinja2").render(
        keywords=format_indexed_keywords_for_prompt(keywords)
    )

    prompt_contract = {
        "system_template": RAW_SYSTEM_TEMPLATE,
        "user_template": RAW_USER_TEMPLATE,
        "output_schema": output_schema,
        "prompt_contract_version": THEME_PROMPT_CONTRACT_VERSION,
        "request_schema_version": REQUEST_SCHEMA_VERSION,
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
    }
    prompt_hash = hashlib.sha256(
        json.dumps(
            prompt_contract,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    input_hash = hashlib.sha256(keyword_text.encode("utf-8")).hexdigest()

    return ThemeBenchmarkRequest(
        example_id="pipeline_run",
        keyword_mode="pipeline",
        keyword_text=keyword_text,
        keywords=keywords,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        prompt_hash=prompt_hash,
        input_hash=input_hash,
        prompt_contract_version=THEME_PROMPT_CONTRACT_VERSION,
    )


class ProviderSafetyError(ThemeBenchmarkError):
    """Typed, payload-safe provider safety outcome recoverable by theme batching."""

    def __init__(
        self,
        *,
        category: str,
        stage: str,
        provider_id: str,
        model_id: str,
        input_hash: str,
        prompt_hash: str,
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        self.category = str(category)
        self.stage = str(stage)
        self.provider_id = str(provider_id)
        self.model_id = str(model_id)
        self.input_hash = str(input_hash)
        self.prompt_hash = str(prompt_hash)
        self.diagnostics = dict(diagnostics or {})
        super().__init__(
            f"Provider safety outcome category={self.category} stage={self.stage} "
            f"provider={self.provider_id} model={self.model_id} "
            f"input_hash={self.input_hash[:12]} prompt_hash={self.prompt_hash[:12]}"
        )


class BaseLLMProvider(ABC):
    metadata: ProviderMetadata
    rate_limit_rpm: int

    def __init__(self) -> None:
        self._run_metrics_lock = threading.Lock()
        self.run_metrics = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost": 0.0,
            "latency_ms_list": [],
            "ttft_ms_list": [],
            "tpot_ms_list": [],
            "prompts_and_responses": [],
            "calls": 0,
            "logical_theme_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "outbound_requests": 0,
            "cache_writes": 0,
            "cache_errors": 0,
            "fallback_attempts": 0,
        }

    @abstractmethod
    def generate(self, request: ThemeBenchmarkRequest) -> dict[str, Any]:
        """Generate structured theme JSON from a benchmark request."""
        ...

    @_optional_mlflow_trace(name="generate_theme")
    def generate_theme(self, keywords: list[str]) -> dict:
        """Generate a theme dictionary from an ordered list of keywords."""
        request = build_theme_request(keywords)
        with self._run_metrics_lock:
            self.run_metrics["logical_theme_requests"] += 1
            self.run_metrics["outbound_requests"] += 1

        start_time = time.time()
        result = self.generate(request)
        end_time = time.time()

        metadata = result.get("_benchmark_metadata", {})
        usage = metadata.get("usage", {})
        outbound_attempts = max(1, int(metadata.get("outbound_attempts", 1)))
        latency_ms = (end_time - start_time) * 1000.0
        ttft = metadata.get("ttft_ms") or latency_ms
        tpot = metadata.get("tpot_ms") or (
            latency_ms / max(1, usage.get("completion_tokens") or 1)
        )
        with self._run_metrics_lock:
            # One outbound request was recorded before generate(); include
            # additional provider-level retries caused by malformed model output.
            self.run_metrics["outbound_requests"] += outbound_attempts - 1
            self.run_metrics["total_prompt_tokens"] += usage.get("prompt_tokens") or 0
            self.run_metrics["total_completion_tokens"] += (
                usage.get("completion_tokens") or 0
            )
            self.run_metrics["total_cost"] += metadata.get("estimated_cost") or 0.0
            self.run_metrics["calls"] += 1
            self.run_metrics["latency_ms_list"].append(latency_ms)
            self.run_metrics["ttft_ms_list"].append(ttft)
            self.run_metrics["tpot_ms_list"].append(tpot)
            self.run_metrics["prompts_and_responses"].append(
                {
                    "system_prompt": request.system_prompt,
                    "user_prompt": request.user_prompt,
                    "response": result,
                    "latency_ms": latency_ms,
                    "ttft_ms": ttft,
                    "tpot_ms": tpot,
                    "prompt_tokens": usage.get("prompt_tokens") or 0,
                    "completion_tokens": usage.get("completion_tokens") or 0,
                    "cost": metadata.get("estimated_cost") or 0.0,
                }
            )

        themes = result.get("themes", [])
        return {
            theme["name"]: theme.get("keywords", [])
            for theme in themes
            if isinstance(theme, dict) and str(theme.get("name", "")).strip()
        }

    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} does not implement generate_text()."
        )
