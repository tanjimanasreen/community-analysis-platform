"""Exact-request cache wrapper for theme-generation providers."""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any

from src.providers.base import BaseLLMProvider, build_theme_request
from src.providers.cache_backends import ThemeResponseCache
from src.themes.benchmark.contracts import ProviderMetadata, ThemeBenchmarkRequest


class CachedProvider(BaseLLMProvider):
    def __init__(self, provider: BaseLLMProvider, cache: ThemeResponseCache) -> None:
        self._provider = provider
        self._cache = cache
        self._logical_theme_requests = 0
        self._metrics_lock = threading.Lock()
        self.rate_limit_rpm = getattr(provider, "rate_limit_rpm", 0)
        inner = getattr(provider, "metadata", None)
        self.metadata = inner or ProviderMetadata(
            provider_id="unknown", model_id="unknown", parameters={}
        )

    @property
    def run_metrics(self) -> dict[str, Any]:
        metrics = dict(getattr(self._provider, "run_metrics", {}))
        with self._metrics_lock:
            logical_requests = self._logical_theme_requests
        metrics["logical_theme_requests"] = logical_requests
        metrics["cache_hits"] = self._cache.hit_count
        metrics["cache_misses"] = self._cache.miss_count
        metrics["cache_writes"] = self._cache.write_count
        metrics["cache_errors"] = self._cache.error_count
        return metrics

    def _compute_cache_key(self, request: ThemeBenchmarkRequest) -> str:
        payload = {
            "cache_schema_version": 1,
            "normalizer_version": 1,
            "request_schema_version": request.schema_version,
            "output_schema_version": request.output_schema_version,
            "ordered_keywords": request.keywords,
            "input_hash": request.input_hash,
            "prompt_hash": request.prompt_hash,
            "provider_id": self.metadata.provider_id,
            "model_id": self.metadata.model_id,
            "generation_parameters": self.metadata.parameters,
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _is_valid_response(response: dict) -> bool:
        if not isinstance(response, dict) or not response:
            return False
        for name, keywords in response.items():
            if not str(name).strip() or not isinstance(keywords, list):
                return False
            if any(not isinstance(keyword, str) for keyword in keywords):
                return False
        return True

    def generate(self, request: ThemeBenchmarkRequest) -> dict[str, Any]:
        return self._provider.generate(request)

    def generate_theme(self, keywords: list[str]) -> dict:
        with self._metrics_lock:
            self._logical_theme_requests += 1
        request = build_theme_request(keywords)
        key = self._compute_cache_key(request)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        response = self._provider.generate_theme(keywords)
        if self._is_valid_response(response):
            generated_by = getattr(
                self._provider, "last_generation_metadata", self.metadata
            )
            self._cache.put(key, response, request, generated_by)
        return response

    def generate_text(self, prompt: str) -> str:
        return self._provider.generate_text(prompt)
