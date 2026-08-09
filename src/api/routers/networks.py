from typing import Literal

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_network_service
from src.api.schemas.networks import (
    CentralityLeadersResponse,
    NetworkResponse,
    TablePage,
)
from src.api.services.network_service import NetworkService

router = APIRouter(prefix="/runs", tags=["networks"])


@router.get("/{run_id}/network", response_model=NetworkResponse)
def get_network(
    run_id: str,
    metric: Literal["if", "wif"] = "if",
    community_id: str | None = None,
    period: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    view: Literal["users", "communities"] = "users",
    sampling: (
        Literal["community_balanced", "strongest_edges", "full_graph"] | None
    ) = None,
    max_nodes: int = Query(default=200, ge=2),
    max_edges: int = Query(default=500, ge=1),
    min_weight: float = Query(default=0.0, ge=0.0),
    service: NetworkService = Depends(get_network_service),
) -> NetworkResponse:
    return NetworkResponse(
        **service.graph(
            run_id,
            metric=metric,
            community_id=community_id,
            min_weight=min_weight,
            max_nodes=max_nodes,
            max_edges=max_edges,
            period=period,
            view=view,
            sampling=sampling,
        )
    )


@router.get("/{run_id}/centrality", response_model=TablePage)
def get_centrality(
    run_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: NetworkService = Depends(get_network_service),
) -> TablePage:
    return TablePage(**service.centrality(run_id, limit=limit, offset=offset))


@router.get(
    "/{run_id}/centrality-leaders",
    response_model=CentralityLeadersResponse,
)
def get_centrality_leaders(
    run_id: str,
    metric: Literal["if", "wif"] = "if",
    period: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    service: NetworkService = Depends(get_network_service),
) -> CentralityLeadersResponse:
    return CentralityLeadersResponse(
        **service.centrality_leaders(run_id, metric=metric, period=period)
    )
