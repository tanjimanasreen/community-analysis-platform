"""Ollama provider — class skeleton kept for reference; NOT wired into production.

Ollama is not part of the active provider registry (providers.yml). This class
is retained for local experimentation only. Do NOT add it to the fallback_chain
or the benchmark.test_models list without explicit approval.

To experiment locally:
    from src.providers.ollama import OllamaProvider
    provider = OllamaProvider(base_url="http://localhost:11434", model="gemma4:12b")
"""

from __future__ import annotations

import json
from typing import Any

from src.providers.base import BaseLLMProvider
from src.themes.benchmark.contracts import ProviderMetadata, ThemeBenchmarkRequest

OLLAMA_PROVIDER_PREFIX = "ollama"


class OllamaProvider(BaseLLMProvider):
    """Ollama local inference provider.

    NOT integrated into the production pipeline or benchmark suite.
    Override generate_text() if you want to use Ollama as a DeepEval judge locally.
    """

    def __init__(self, *, base_url: str, model: str, rate_limit_rpm: int = 600) -> None:
        import requests  # optional dep; only checked at construction

        self._requests = requests
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.rate_limit_rpm = rate_limit_rpm
        self.metadata = ProviderMetadata(
            provider_id=f"{OLLAMA_PROVIDER_PREFIX}__{model}",
            model_id=model,
            parameters={"base_url": base_url, "temperature": 0.0},
        )

    def generate(self, request: ThemeBenchmarkRequest) -> dict[str, Any]:
        """Minimal benchmark interface."""
        prompt = f"{request.system_prompt}\n\n{request.user_prompt}"
        response = self._requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0, "seed": 42},
            },
        )
        response.raise_for_status()
        result_text = response.json().get("response", "")
        try:
            themes_dict = json.loads(result_text)
        except json.JSONDecodeError:
            if "```json" in result_text:
                clean = result_text.split("```json")[1].split("```")[0].strip()
                try:
                    themes_dict = json.loads(clean)
                except json.JSONDecodeError:
                    themes_dict = {
                        "Error": "Failed to parse JSON",
                        "Raw Output": result_text,
                    }
            else:
                themes_dict = {
                    "Error": "Failed to parse JSON",
                    "Raw Output": result_text,
                }

        if isinstance(themes_dict, dict) and "Error" in themes_dict:
            return {"themes": [], "error": themes_dict}

        return {"themes": [{"name": k, "keywords": v} for k, v in themes_dict.items()]}
