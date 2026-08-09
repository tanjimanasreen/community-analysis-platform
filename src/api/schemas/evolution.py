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


class EvolutionMethodology(StrictModel):
    content_type: str
    transition_threshold: float | None = None
    similarity_provider: str | None = None
    similarity_model: str | None = None
    similarity_model_revision: str | None = None


class EvolutionPathStep(StrictModel):
    step_index: int
    month: str
    community_key: str
    community_id: str
    member_count: int
    members: list[str]
    previous_month: str | None = None
    previous_community_key: str | None = None
    previous_community_id: str | None = None
    jaccard_from_previous: float | None = None
    retained_count: int | None = None
    absolute_theme: str = ""
    weighted_theme: str = ""
    general_theme: str = ""


class EvolutionPath(StrictModel):
    path_id: str
    display_order: int
    duration: int
    transition_count: int
    average_jaccard: float
    total_retained_members: int
    months: list[str]
    steps: list[EvolutionPathStep]


class EvolutionPathsResponse(StrictModel):
    run_id: str
    paths: list[EvolutionPath]
    total: int
    methodology: EvolutionMethodology


class PathMembershipRecord(StrictModel):
    path_id: str
    display_order: int
    step_index: int
    month: str
    community_key: str
    community_id: str
    member_count: int
    size_delta: int | None = None
    existing_count: int
    new_count: int
    lost_count: int
    reappearing_count: int
    members: list[str]
    existing_members: list[str]
    new_members: list[str]
    lost_members: list[str]
    reappearing_members: list[str]


class PathMembershipResponse(StrictModel):
    run_id: str
    path_id: str
    records: list[PathMembershipRecord]


class PathThemeSimilarityResponse(StrictModel):
    run_id: str
    path_id: str
    theme_type: str
    months: list[str]
    communities: list[str]
    themes: list[str]
    matrix: list[list[float]]
    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_model_revision: str | None = None
