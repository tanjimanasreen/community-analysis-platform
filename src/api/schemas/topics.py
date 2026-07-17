from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


TopicType = Literal["matched", "partial"]


class TopicRecord(StrictModel):
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
    absolute_members: Any = None
    weighted_members: Any = None
    jaccard_score: float | None = None
    common_members: Any = None
    uncommon_members: Any = None


class TopicsResponse(StrictModel):
    run_id: str
    topic_type: TopicType
    records: list[TopicRecord]
    total: int
    limit: int
    offset: int
