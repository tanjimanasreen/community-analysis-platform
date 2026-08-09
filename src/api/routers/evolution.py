from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_evolution_service
from src.api.schemas.evolution import (
    EvolutionPathsResponse,
    MembershipChangesResponse,
    PathMembershipResponse,
    PathThemeSimilarityResponse,
    PersistentCommunitiesResponse,
    ThemeSimilarityResponse,
    TransitionsResponse,
)
from src.api.services.evolution_service import EvolutionService

router = APIRouter(prefix="/runs", tags=["evolution"])


@router.get("/{run_id}/transitions", response_model=TransitionsResponse)
def get_transitions(
    run_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: EvolutionService = Depends(get_evolution_service),
) -> TransitionsResponse:
    return TransitionsResponse(
        **service.transitions(run_id, limit=limit, offset=offset)
    )


@router.get(
    "/{run_id}/persistent-communities",
    response_model=PersistentCommunitiesResponse,
)
def get_persistent_communities(
    run_id: str,
    service: EvolutionService = Depends(get_evolution_service),
) -> PersistentCommunitiesResponse:
    return PersistentCommunitiesResponse(**service.persistent_communities(run_id))


@router.get("/{run_id}/membership-changes", response_model=MembershipChangesResponse)
def get_membership_changes(
    run_id: str,
    service: EvolutionService = Depends(get_evolution_service),
) -> MembershipChangesResponse:
    return MembershipChangesResponse(**service.membership_changes(run_id))


@router.get("/{run_id}/theme-similarity", response_model=ThemeSimilarityResponse)
def get_theme_similarity(
    run_id: str,
    service: EvolutionService = Depends(get_evolution_service),
) -> ThemeSimilarityResponse:
    return ThemeSimilarityResponse(**service.theme_similarity(run_id))


@router.get("/{run_id}/evolution/paths", response_model=EvolutionPathsResponse)
def get_evolution_paths(
    run_id: str,
    service: EvolutionService = Depends(get_evolution_service),
) -> EvolutionPathsResponse:
    return EvolutionPathsResponse(**service.paths(run_id))


@router.get(
    "/{run_id}/evolution/paths/{path_id}/mobility",
    response_model=PathMembershipResponse,
)
def get_evolution_path_mobility(
    run_id: str,
    path_id: str,
    service: EvolutionService = Depends(get_evolution_service),
) -> PathMembershipResponse:
    return PathMembershipResponse(**service.path_membership(run_id, path_id))


@router.get(
    "/{run_id}/evolution/paths/{path_id}/theme-similarity",
    response_model=PathThemeSimilarityResponse,
)
def get_evolution_path_theme_similarity(
    run_id: str,
    path_id: str,
    theme_type: str = Query(default="general", pattern="^(general|absolute|weighted)$"),
    service: EvolutionService = Depends(get_evolution_service),
) -> PathThemeSimilarityResponse:
    return PathThemeSimilarityResponse(
        **service.path_theme_similarity(run_id, path_id, theme_type=theme_type)
    )
