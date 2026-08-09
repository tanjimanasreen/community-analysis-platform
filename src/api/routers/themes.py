from fastapi import APIRouter, Depends, Query

from src.api.dependencies import (
    get_theme_cluster_service,
    get_theme_trend_service,
    get_topic_service,
)
from src.api.schemas.themes import (
    ClusteredThemeEvidenceResponse,
    ClusteredThemeTimelineResponse,
    MonthlyClusteredThemeResponse,
    MonthlyThemeTrendResponse,
    ThemesResponse,
    ThemeTimelineResponse,
)
from src.api.services.theme_trend_service import ThemeTrendService
from src.api.services.theme_cluster_service import ThemeClusterService
from src.api.services.topic_service import TopicService

router = APIRouter(prefix="/runs", tags=["themes"])


@router.get("/{run_id}/themes", response_model=ThemesResponse)
def get_themes(
    run_id: str,
    month: str | None = None,
    period: str | None = None,
    community_id: str | None = None,
    exact_theme: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: TopicService = Depends(get_topic_service),
) -> ThemesResponse:
    return ThemesResponse(
        **service.themes(
            run_id,
            month=month,
            period=period,
            community_id=community_id,
            exact_theme=exact_theme,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/{run_id}/themes/{community_id}", response_model=ThemesResponse)
def get_community_themes(
    run_id: str,
    community_id: str,
    month: str | None = None,
    period: str | None = None,
    exact_theme: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: TopicService = Depends(get_topic_service),
) -> ThemesResponse:
    return ThemesResponse(
        **service.themes(
            run_id,
            month=month,
            period=period,
            community_id=community_id,
            exact_theme=exact_theme,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/{run_id}/theme-trends/monthly",
    response_model=MonthlyThemeTrendResponse,
)
def get_monthly_theme_trends(
    run_id: str,
    period: str,
    scope: str = "matched",
    service: ThemeTrendService = Depends(get_theme_trend_service),
) -> MonthlyThemeTrendResponse:
    return MonthlyThemeTrendResponse(
        **service.monthly(run_id, period=period, scope=scope)
    )


@router.get(
    "/{run_id}/theme-trends/timeline",
    response_model=ThemeTimelineResponse,
)
def get_theme_timeline(
    run_id: str,
    period_start: str | None = None,
    period_end: str | None = None,
    scope: str = "matched",
    service: ThemeTrendService = Depends(get_theme_trend_service),
) -> ThemeTimelineResponse:
    return ThemeTimelineResponse(
        **service.timeline(
            run_id,
            period_start=period_start,
            period_end=period_end,
            scope=scope,
        )
    )


@router.get(
    "/{run_id}/theme-clusters/monthly",
    response_model=MonthlyClusteredThemeResponse,
)
def get_monthly_clustered_themes(
    run_id: str,
    period: str,
    scope: str = "matched",
    service: ThemeClusterService = Depends(get_theme_cluster_service),
) -> MonthlyClusteredThemeResponse:
    return MonthlyClusteredThemeResponse(
        **service.monthly(run_id, period=period, scope=scope)
    )


@router.get(
    "/{run_id}/theme-clusters/timeline",
    response_model=ClusteredThemeTimelineResponse,
)
def get_clustered_theme_timeline(
    run_id: str,
    period_start: str | None = None,
    period_end: str | None = None,
    scope: str = "matched",
    service: ThemeClusterService = Depends(get_theme_cluster_service),
) -> ClusteredThemeTimelineResponse:
    return ClusteredThemeTimelineResponse(
        **service.timeline(
            run_id,
            period_start=period_start,
            period_end=period_end,
            scope=scope,
        )
    )


@router.get(
    "/{run_id}/theme-clusters/evidence",
    response_model=ClusteredThemeEvidenceResponse,
)
def get_clustered_theme_evidence(
    run_id: str,
    period: str,
    canonical_theme_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: ThemeClusterService = Depends(get_theme_cluster_service),
) -> ClusteredThemeEvidenceResponse:
    return ClusteredThemeEvidenceResponse(
        **service.evidence(
            run_id,
            period=period,
            canonical_theme_id=canonical_theme_id,
            limit=limit,
            offset=offset,
        )
    )
