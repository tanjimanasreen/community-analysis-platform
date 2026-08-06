from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


MetricName = Literal["if", "wif"]
NetworkView = Literal["users", "communities"]
SamplingStrategy = Literal["community_balanced", "strongest_edges", "full_graph"]


class NetworkNode(StrictModel):
    id: str
    community_ids: list[str]
    node_type: Literal["user", "community"] = "user"
    community_id: str | None = None
    member_count: int | None = None
    internal_edge_count: int | None = None
    internal_weight: float | None = None
    inbound_cross_community_weight: float | None = None
    outbound_cross_community_weight: float | None = None
    cross_community_neighbor_count: int | None = None
    x: float | None = None
    y: float | None = None


class NetworkEdge(StrictModel):
    source: str
    target: str
    community_id: str | None = None
    direction: str | None = None
    weight: float
    edge_count: int | None = None
    user_pair_count: int | None = None
    interaction_count: int | None = None
    source_user_count: int | None = None
    target_user_count: int | None = None


class NetworkCoverage(StrictModel):
    is_complete: bool
    scope: str
    completeness_reason: str | None = None
    available_users: int
    represented_users: int
    available_edges: int
    represented_edges: int
    available_communities: int
    represented_communities: int
    available_weight: float
    represented_weight: float
    weight_coverage_ratio: float | None = None
    cross_community_edges_available: bool = False
    cross_community_edges_reason: str | None = None


class NetworkSampling(StrictModel):
    strategy: SamplingStrategy
    deterministic: bool = True
    max_nodes: int
    max_edges: int


class NetworkResponse(StrictModel):
    run_id: str
    metric: MetricName
    period: str | None = None
    community_id: str | None = None
    view: NetworkView = "users"
    sampling_strategy: SamplingStrategy | None = None
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    available_nodes: int
    available_edges: int
    returned_nodes: int
    returned_edges: int
    sampled: bool
    coverage: NetworkCoverage | None = None
    sampling: NetworkSampling | None = None


class CentralityActor(StrictModel):
    user_id: str
    display_user_id: str
    centrality: float
    community_id: str | None = None
    community_assignment_status: Literal["available", "unavailable"]


class CentralityLeadersPeriod(StrictModel):
    period: str
    spreader: CentralityActor | None = None
    influencer: CentralityActor | None = None
    average_in_degree_centrality: float | None = None
    average_out_degree_centrality: float | None = None


class CentralityLeadersResponse(StrictModel):
    run_id: str
    metric: MetricName
    periods: list[CentralityLeadersPeriod]
    methodology_note: str = Field(
        description=(
            "Degree centrality is normalized structural reach based on distinct "
            "directed connections; it is not a message count or total edge weight."
        )
    )


class TablePage(StrictModel):
    run_id: str
    artifact_key: str
    records: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
