from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


MetricName = Literal["if", "wif"]


class NetworkNode(StrictModel):
    id: str
    community_ids: list[str]


class NetworkEdge(StrictModel):
    source: str
    target: str
    community_id: str | None = None
    direction: str | None = None
    weight: float


class NetworkResponse(StrictModel):
    run_id: str
    metric: MetricName
    community_id: str | None = None
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    available_nodes: int
    available_edges: int
    returned_nodes: int
    returned_edges: int
    sampled: bool


class TablePage(StrictModel):
    run_id: str
    artifact_key: str
    records: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
