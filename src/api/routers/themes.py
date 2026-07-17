from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_topic_service
from src.api.schemas.themes import ThemesResponse
from src.api.services.topic_service import TopicService

router = APIRouter(prefix="/runs", tags=["themes"])


@router.get("/{run_id}/themes", response_model=ThemesResponse)
def get_themes(
    run_id: str,
    month: str | None = None,
    community_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: TopicService = Depends(get_topic_service),
) -> ThemesResponse:
    return ThemesResponse(
        **service.themes(
            run_id,
            month=month,
            community_id=community_id,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/{run_id}/themes/{community_id}", response_model=ThemesResponse)
def get_community_themes(
    run_id: str,
    community_id: str,
    month: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: TopicService = Depends(get_topic_service),
) -> ThemesResponse:
    return ThemesResponse(
        **service.themes(
            run_id,
            month=month,
            community_id=community_id,
            limit=limit,
            offset=offset,
        )
    )
