"""OpenAI LLM provider — theme pipeline interface.

This provider is used for non-benchmark theme generation (run_theme_analysis).
It wraps the OpenAI Chat Completions API and implements BaseLLMProvider.

Model and API key are read from environment at construction time.
No model is hardcoded here — the caller or factory selects the model
via providers.yml (theme_provider.primary: "openai:<model>").
"""

from __future__ import annotations

import json
import os

from src.providers.base import BaseLLMProvider
from src.themes.benchmark.contracts import ProviderMetadata, ThemeBenchmarkRequest

OPENAI_PROVIDER_PREFIX = "openai"

_SYSTEM_PROMPT = (
    "You are an expert who can find meaningful themes from a list of keywords, "
    "that may contain specific events, people, locations, or topics."
)

_USER_PROMPT_TEMPLATE = (
    "Based on the list of the keywords given below, provide only the exact theme "
    "and the corresponding keywords in a coherent short sentence in a JSON. "
    "The keys of the json should be theme names and values should be corresponding "
    "keywords. There could be one theme or multiple themes for each set of keywords. "
    "Here is the list of keywords: {text}"
)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Chat Completions provider for non-benchmark theme generation.

    Not wired into the benchmark pipeline — use GeminiBenchmarkProvider /
    LLM7BenchmarkProvider / NvidiaBenchmarkProvider for benchmarking.
    """

    def __init__(
        self,
        *,
        model_id: str = "gpt-4o",
        api_key: str | None = None,
        rate_limit_rpm: int = 60,
    ) -> None:
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise ImportError("openai package is required for OpenAIProvider") from exc

        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model_id = model_id
        self.rate_limit_rpm = rate_limit_rpm
        self._client = OpenAI(api_key=self._api_key)
        self.metadata = ProviderMetadata(
            provider_id=f"{OPENAI_PROVIDER_PREFIX}__{model_id}",
            model_id=model_id,
            parameters={"temperature": 0, "seed": 42, "response_format": "json_object"},
        )

    def generate(self, request: ThemeBenchmarkRequest) -> dict:
        """Thin generate() implementation — delegates to generate_theme()."""
        themes_dict = self.generate_theme(request.user_prompt)
        return {"themes": [{"name": k, "keywords": v} for k, v in themes_dict.items()]}

    def generate_theme(self, text: str) -> dict:
        completion = self._client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _USER_PROMPT_TEMPLATE.format(text=text)},
            ],
            seed=42,
            temperature=0,
            response_format={"type": "json_object"},
        )
        return json.loads(completion.choices[0].message.content)

    def generate_text(self, prompt: str) -> str:
        completion = self._client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return completion.choices[0].message.content or ""
