from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TransitionRecord(StrictModel):
    start_month: str
    end_month: str
    start_month_community: str | int
    end_month_community: str | int
    jaccard_score: float
    common_members: Any = None
    uncommon_members: Any = None
    start_month_members: Any = None
    total_start_month_members: int | None = None
    end_month_members: Any = None
    total_end_month_members: int | None = None
    start_month_absolute_theme: Any = None
    end_month_absolute_theme: Any = None
    start_month_weighted_theme: Any = None
    end_month_weighted_theme: Any = None
    start_month_general_theme: Any = None
    end_month_general_theme: Any = None


class TransitionsResponse(StrictModel):
    run_id: str
    records: list[TransitionRecord]
    total: int
    limit: int
    offset: int


class PersistentCommunity(StrictModel):
    persistent_id: str
    communities: list[str]
    months: list[str]
    transition_count: int
    average_jaccard: float


class PersistentCommunitiesResponse(StrictModel):
    run_id: str
    communities: list[PersistentCommunity]
    total: int


class MembershipChange(StrictModel):
    start_month: str
    end_month: str
    start_community: str
    end_community: str
    retained_count: int
    joined_count: int
    exited_count: int
    start_count: int
    end_count: int


class MembershipChangesResponse(StrictModel):
    run_id: str
    records: list[MembershipChange]
    total: int


class SimilarityArtifact(StrictModel):
    artifact_key: str
    media_type: str
    path: str


class ThemeSimilarityResponse(StrictModel):
    run_id: str
    matrix: list[list[float]] | None = None
    labels: list[str]
    artifacts: list[SimilarityArtifact]
