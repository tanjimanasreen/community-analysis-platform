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
        """Minimal benchmark interface — delegates to generate_theme()."""
        themes_dict = self.generate_theme(request.user_prompt)
        return {"themes": [{"name": k, "keywords": v} for k, v in themes_dict.items()]}

    def generate_theme(self, text: str) -> dict:
        prompt = (
            "You are an expert who can find meaningful themes from a list of keywords, "
            "that may contain specific events, people, locations, or topics.\n\n"
            "Based on the list of the keywords given below, provide only the exact theme "
            "and the corresponding keywords in a coherent short sentence in a JSON. "
            "The keys of the json should be theme names and values should be corresponding "
            f"keywords. There could be one theme or multiple themes for each set of keywords.\n\n"
            f"Here is the list of keywords: {text}\n\n"
            "Output strictly valid JSON and nothing else."
        )
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
            return json.loads(result_text)
        except json.JSONDecodeError:
            if "```json" in result_text:
                clean = result_text.split("```json")[1].split("```")[0].strip()
                try:
                    return json.loads(clean)
                except json.JSONDecodeError:
                    pass
            return {"Error": "Failed to parse JSON", "Raw Output": result_text}
