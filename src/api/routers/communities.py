from typing import Literal

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_network_service
from src.api.schemas.communities import CommunityDetail, CommunitiesResponse
from src.api.services.network_service import NetworkService

router = APIRouter(prefix="/runs", tags=["communities"])


@router.get("/{run_id}/communities", response_model=CommunitiesResponse)
def get_communities(
    run_id: str,
    metric: Literal["if", "wif"] = "if",
    period: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: NetworkService = Depends(get_network_service),
) -> CommunitiesResponse:
    return CommunitiesResponse(
        **service.communities(
            run_id, metric=metric, limit=limit, offset=offset, period=period
        )
    )


@router.get("/{run_id}/communities/{community_id}", response_model=CommunityDetail)
def get_community(
    run_id: str,
    community_id: str,
    metric: Literal["if", "wif"] = "if",
    period: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    max_nodes: int = Query(default=200, ge=2),
    max_edges: int = Query(default=500, ge=1),
    min_weight: float = Query(default=0.0, ge=0.0),
    service: NetworkService = Depends(get_network_service),
) -> CommunityDetail:
    return CommunityDetail(
        **service.community_detail(
            run_id,
            metric=metric,
            community_id=community_id,
            max_nodes=max_nodes,
            max_edges=max_edges,
            min_weight=min_weight,
            period=period,
        )
    )
