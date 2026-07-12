"""Project-wide algorithm and provider defaults.

All values are Pydantic BaseModel instances so they can be validated,
serialised, and overridden from config dicts consistently with the rest
of the settings layer (see db_settings.py).

THESIS CONSTRAINTS — do not change defaults without documenting the experiment:
  GraphThresholds:     min_total_post=10, min_shared_post=5
  LouvainDefaults:     resolution=1.0, seed=123
  LDADefaults:         num_topics=15, random_state=100, iterations=100,
                       chunksize=20, passes=80, alpha='auto', eta='auto'
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GraphThresholds(BaseModel):
    min_total_post: int = 10
    min_shared_post: int = 5
    min_members: int = 3


class LouvainDefaults(BaseModel):
    resolution: float = 1.0
    seed: int = 123


class LDADefaults(BaseModel):
    num_topics: int = 15
    top_n_keywords: int = 50
    random_state: int = 100
    iterations: int = 100
    chunksize: int = 20
    passes: int = 80
    alpha: str = "auto"
    eta: str = "auto"


class ThemeProviderDefaults(BaseModel):
    """Default theme-generation provider settings.

    primary: the champion model spec. Use "mock" for offline/CI runs.
    fallback: whether the pipeline falls back on rate-limit or API error.
    fallback_chain: ordered list of real provider specs (no mock in production).
    """
    primary: str = "mock"
    fallback: bool = True
    fallback_chain: list[str] = Field(
        default_factory=lambda: ["llm7:fast", "nvidia:meta/llama3-70b-instruct"]
    )


class ThemeSimilarityDefaults(BaseModel):
    embedding_model: str = "paraphrase-MiniLM-L6-v2"
    reply_transition_threshold: float = 0.0
    default_transition_threshold: float = 0.5


class ProjectDefaults(BaseModel):
    graph: GraphThresholds = Field(default_factory=GraphThresholds)
    louvain: LouvainDefaults = Field(default_factory=LouvainDefaults)
    lda: LDADefaults = Field(default_factory=LDADefaults)
    theme_provider: ThemeProviderDefaults = Field(default_factory=ThemeProviderDefaults)
    similarity: ThemeSimilarityDefaults = Field(default_factory=ThemeSimilarityDefaults)


# Module-level singleton — import this in provider and pipeline code.
default_config = ProjectDefaults()
