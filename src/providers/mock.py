"""Mock and baseline providers for offline testing and benchmark evaluation.

Classes:
  MockProvider            — theme pipeline mock (used in unit tests and offline CI).
  BenchmarkMockProvider   — benchmark pipeline mock (deterministic structured output).
  KeywordBaselineProvider — non-LLM keyword grouping baseline for benchmark comparison.
"""

from __future__ import annotations

from typing import Any

from src.providers.base import BaseLLMProvider
from src.themes.benchmark.contracts import ProviderMetadata, ThemeBenchmarkRequest


class MockProvider(BaseLLMProvider):
    """Simple mock provider for offline theme pipeline testing.

    Returns a configurable static response dict. Used in unit tests
    (test_longitudinal_sample.py, test_theme_pipeline.py) and as the default
    primary provider in providers.yml during development runs.

    NOT used in benchmark evaluation — use BenchmarkMockProvider for that.
    """

    metadata = ProviderMetadata(
        provider_id="mock",
        model_id="deterministic-mock-theme-v2",
        parameters={"temperature": 0, "offline": True},
    )
    rate_limit_rpm = 1000

    def __init__(self, static_response: dict | None = None) -> None:
        self.static_response = static_response or {
            "Mock Theme": ["mock keyword 1", "mock keyword 2"]
        }

    def generate(self, request: ThemeBenchmarkRequest) -> dict[str, Any]:
        themes = [
            {"name": k, "keywords": v if isinstance(v, list) else v.split(", ")}
            for k, v in self.static_response.items()
        ]
        return {"themes": themes}

    def generate_theme(self, text: str) -> dict:
        return self.static_response

    def generate_text(self, prompt: str) -> str:
        import json
        return json.dumps(
            {"reason": "Mock evaluation from deterministic provider", "score": 5, "verdict": "yes"}
        )


class KeywordBaselineProvider(BaseLLMProvider):
    metadata = ProviderMetadata(
        provider_id="keyword_baseline",
        model_id="deterministic-keyword-baseline-v1",
        parameters={"temperature": 0, "offline": True},
    )
    rate_limit_rpm = 1000

    def generate(self, request: ThemeBenchmarkRequest) -> dict[str, Any]:
        keywords = list(dict.fromkeys(request.keywords))
        if not keywords:
            return {"themes": []}
        group_size = max(1, min(4, len(keywords)))
        themes = []
        for index in range(0, len(keywords), group_size):
            group = keywords[index : index + group_size]
            name = " / ".join(group[:2])
            themes.append({"name": f"{request.keyword_mode.title()} Theme: {name}", "keywords": group})
        return {"themes": themes}


class BenchmarkMockProvider(BaseLLMProvider):
    metadata = ProviderMetadata(
        provider_id="mock",
        model_id="deterministic-mock-theme-v2",
        parameters={"temperature": 0, "offline": True},
    )
    rate_limit_rpm = 1000

    def generate(self, request: ThemeBenchmarkRequest) -> dict[str, Any]:
        keywords = list(dict.fromkeys(request.keywords[:3]))
        name = f"Benchmark {request.keyword_mode.title()} Theme"
        return {"themes": [{"name": name, "keywords": keywords}] if keywords else []}

    def generate_text(self, prompt: str) -> str:
        # Provide a generic valid JSON that most DeepEval GEval metrics can parse
        import json
        return json.dumps({"reason": "Mock evaluation from deterministic provider", "score": 5, "verdict": "yes"})
