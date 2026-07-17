from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ThemeRecord(StrictModel):
    month: str | None = None
    absolute_community: str | int | None = None
    absolute_unigram_topic: Any = None
    absolute_unigram_keywords: Any = None
    weighted_community: str | int | None = None
    weighted_unigram_topic: Any = None
    weighted_unigram_keywords: Any = None
    absolute_bigram_topic: Any = None
    absolute_bigram_keywords: Any = None
    weighted_bigram_topic: Any = None
    weighted_bigram_keywords: Any = None
    members: Any = None
    general_theme_gpt: Any = None
    general_theme_names: Any = None
    absolute_theme_gpt: Any = None
    absolute_theme_names: Any = None
    weighted_theme_gpt: Any = None
    weighted_theme_names: Any = None
    all_keywords: Any = None
    absolute_keywords: Any = None
    weighted_keywords: Any = None


class ThemesResponse(StrictModel):
    run_id: str
    records: list[ThemeRecord]
    total: int
    limit: int
    offset: int
    provider_metadata: dict[str, Any] | None = None
