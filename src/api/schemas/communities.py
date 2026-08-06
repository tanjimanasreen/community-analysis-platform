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
    inbound_cross_community_weight: float | None = None
    outbound_cross_community_weight: float | None = None
    cross_community_neighbor_count: int | None = None


class CommunitiesResponse(StrictModel):
    run_id: str
    metric: MetricName
    period: str | None = None
    communities: list[CommunitySummary]
    total: int
    limit: int
    offset: int


class CommunityDetail(StrictModel):
    run_id: str
    metric: MetricName
    period: str | None = None
    community: CommunitySummary
    graph: NetworkResponse
