from typing import Literal

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_topic_service
from src.api.schemas.topics import TopicsResponse
from src.api.services.topic_service import TopicService

router = APIRouter(prefix="/runs", tags=["topics"])


@router.get("/{run_id}/topics", response_model=TopicsResponse)
def get_topics(
    run_id: str,
    type: Literal["matched", "partial"] = "matched",
    community_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: TopicService = Depends(get_topic_service),
) -> TopicsResponse:
    return TopicsResponse(
        **service.topics(
            run_id,
            topic_type=type,
            community_id=community_id,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/{run_id}/topics/{community_id}", response_model=TopicsResponse)
def get_community_topics(
    run_id: str,
    community_id: str,
    type: Literal["matched", "partial"] = "matched",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: TopicService = Depends(get_topic_service),
) -> TopicsResponse:
    return TopicsResponse(
        **service.topics(
            run_id,
            topic_type=type,
            community_id=community_id,
            limit=limit,
            offset=offset,
        )
    )
