from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.api.schemas.networks import MetricName, NetworkResponse


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CommunitySummary(StrictModel):
    community_id: str
    node_count: int
    edge_count: int
    total_weight: float


class CommunitiesResponse(StrictModel):
    run_id: str
    metric: MetricName
    communities: list[CommunitySummary]
    total: int
    limit: int
    offset: int


class CommunityDetail(StrictModel):
    run_id: str
    metric: MetricName
    community: CommunitySummary
    graph: NetworkResponse
