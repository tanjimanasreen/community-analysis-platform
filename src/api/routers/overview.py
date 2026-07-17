from fastapi import APIRouter, Depends

from src.api.dependencies import get_overview_service
from src.api.schemas.overview import OverviewResponse
from src.api.services.overview_service import OverviewService

router = APIRouter(prefix="/runs", tags=["overview"])


@router.get("/{run_id}/overview", response_model=OverviewResponse)
def get_overview(
    run_id: str,
    service: OverviewService = Depends(get_overview_service),
) -> OverviewResponse:
    return OverviewResponse(**service.overview(run_id))
