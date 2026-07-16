"""Base class for all LLM providers in this project.

All providers — benchmark and theme-generation — must implement this interface.
This ensures the factory, routing, and caching layers work uniformly across
both the benchmark pipeline and the theme pipeline.

Interface methods:
  generate()        — benchmark pipeline (structured ThemeBenchmarkRequest → JSON)
  generate_theme()  — theme pipeline (raw keyword text → theme dict)
  generate_text()   — evaluation/judge pipeline (free-form prompt → text)
"""

from abc import ABC, abstractmethod
from typing import Any

from src.themes.benchmark.contracts import ProviderMetadata, ThemeBenchmarkRequest


class BaseLLMProvider(ABC):
    metadata: ProviderMetadata
    rate_limit_rpm: int

    @abstractmethod
    def generate(self, request: ThemeBenchmarkRequest) -> dict[str, Any]:
        """Generate structured theme JSON from a benchmark request.

        Used exclusively by the benchmark pipeline. Each provider is evaluated
        independently — no fallback is applied at this level.
        """
        ...

    def generate_theme(self, text: str) -> dict:
        """Generate a theme dict from raw keyword text.

        Used by the theme pipeline (run_theme_analysis). The default implementation
        constructs a minimal ThemeBenchmarkRequest and delegates to generate().
        Providers that have a more efficient code path may override this.
        """
        from src.themes.benchmark.dataset import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

        request = ThemeBenchmarkRequest(
            example_id="pipeline_run",
            keyword_mode="pipeline",
            keyword_text=text,
            keywords=text.split(",") if "," in text else text.split(),
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_PROMPT_TEMPLATE.format(keywords=text),
            prompt_hash="pipeline_dummy_hash",
            input_hash="pipeline_dummy_hash",
        )
        result = self.generate(request)
        themes = result.get("themes", [])
        return {t["name"]: t.get("keywords", []) for t in themes if "name" in t}

    def generate_text(self, prompt: str) -> str:
        """Generate raw text from a prompt.

        Used by the DeepEval judge pipeline. Must respect rate_limit_rpm.
        Providers acting as DeepEval judges (gemini, nvidia, llm7, openai)
        should override this method.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement generate_text(). "
            "Override this method to use this provider as a DeepEval judge."
        )
