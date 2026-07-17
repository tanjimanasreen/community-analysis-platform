from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI

from src.api.dependencies import ApiSettings
from src.api.errors import install_error_handlers
from src.api.routers import (
    communities,
    evolution,
    networks,
    overview,
    reports,
    runs,
    themes,
    topics,
)
from src.api.schemas.runs import HealthResponse
from src.api.services.artifact_reader import ArtifactReader
from src.api.services.evolution_service import EvolutionService
from src.api.services.network_service import GraphLimits, NetworkService
from src.api.services.overview_service import OverviewService
from src.api.services.run_catalog import RunCatalog
from src.api.services.topic_service import TopicService

API_PREFIX = "/api/v1"
API_SCHEMA_VERSION = "1.0"


def create_app(
    *,
    artifact_root: str | Path | None = None,
    settings: ApiSettings | None = None,
) -> FastAPI:
    """Create a read-only API over canonical run-scoped artifacts."""
    resolved = settings or ApiSettings.from_env(artifact_root)
    catalog = RunCatalog(
        resolved.artifact_root,
        refresh_seconds=resolved.catalog_refresh_seconds,
    )
    reader = ArtifactReader(catalog)
    topic_service = TopicService(reader)
    evolution_service = EvolutionService(reader)
    network_service = NetworkService(
        reader,
        GraphLimits(
            max_nodes=resolved.max_graph_nodes,
            max_edges=resolved.max_graph_edges,
        ),
    )
    overview_service = OverviewService(reader, topic_service, evolution_service)

    application = FastAPI(
        title="Community Analysis Dashboard API",
        version=API_SCHEMA_VERSION,
        description=(
            "Read-only access to validated community-analysis pipeline artifacts. "
            "This service never executes analytical stages."
        ),
    )
    application.state.api_settings = resolved
    application.state.run_catalog = catalog
    application.state.artifact_reader = reader
    application.state.topic_service = topic_service
    application.state.evolution_service = evolution_service
    application.state.network_service = network_service
    application.state.overview_service = overview_service

    install_error_handlers(application)

    api = APIRouter(prefix=API_PREFIX)

    @api.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            read_only=True,
            schema_version=API_SCHEMA_VERSION,
        )

    api.include_router(runs.router)
    api.include_router(overview.router)
    api.include_router(networks.router)
    api.include_router(communities.router)
    api.include_router(topics.router)
    api.include_router(themes.router)
    api.include_router(evolution.router)
    api.include_router(reports.router)
    application.include_router(api)
    return application


app = create_app()
