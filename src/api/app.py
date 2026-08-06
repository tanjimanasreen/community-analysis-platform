from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

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
from src.api.schemas.runs import HealthResponse, ReadinessResponse
from src.api.services.artifact_reader import ArtifactReader
from src.api.services.evolution_service import EvolutionService
from src.api.services.network_service import GraphLimits, NetworkService
from src.api.services.overview_service import OverviewService
from src.api.services.run_catalog import RunCatalog
from src.api.services.topic_service import TopicService

API_PREFIX = "/api/v1"
API_SCHEMA_VERSION = "1.0"
_REQUEST_ID_HEADER = "X-Request-ID"
logger = logging.getLogger(__name__)


def create_app(
    *,
    artifact_root: str | Path | None = None,
    settings: ApiSettings | None = None,
) -> FastAPI:
    """Create a read-only API over canonical run-scoped artifacts."""
    from src.logging_config import setup_logging

    setup_logging()
    resolved = settings or ApiSettings.from_env(artifact_root)
    catalog = RunCatalog(
        resolved.artifact_root,
        refresh_seconds=resolved.catalog_refresh_seconds,
    )
    reader = ArtifactReader(
        catalog, parquet_cache_max_bytes=resolved.parquet_cache_max_bytes
    )
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
        root_path=resolved.root_path,
        docs_url="/docs" if resolved.docs_enabled else None,
        redoc_url="/redoc" if resolved.docs_enabled else None,
        openapi_url="/openapi.json" if resolved.docs_enabled else None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", _REQUEST_ID_HEADER],
        expose_headers=[_REQUEST_ID_HEADER, "Server-Timing"],
    )
    application.add_middleware(
        GZipMiddleware,
        minimum_size=resolved.gzip_minimum_size,
    )
    if resolved.allowed_hosts and "*" not in resolved.allowed_hosts:
        application.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=list(resolved.allowed_hosts),
        )

    application.state.api_settings = resolved
    application.state.run_catalog = catalog
    application.state.artifact_reader = reader
    application.state.topic_service = topic_service
    application.state.evolution_service = evolution_service
    application.state.network_service = network_service
    application.state.overview_service = overview_service

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = _request_id(request.headers.get(_REQUEST_ID_HEADER))
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "api_request_failed method=%s path=%s request_id=%s elapsed_ms=%.2f",
                request.method,
                request.url.path,
                request_id,
                elapsed_ms,
            )
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers[_REQUEST_ID_HEADER] = request_id
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.2f}"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if request.url.path.startswith(API_PREFIX):
            response.headers.setdefault("Cache-Control", "no-store")
        log_complete = (
            logger.debug
            if request.url.path in {f"{API_PREFIX}/health", f"{API_PREFIX}/ready"}
            else logger.info
        )
        log_complete(
            "api_request_complete method=%s path=%s status=%s request_id=%s elapsed_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
            elapsed_ms,
        )
        return response

    install_error_handlers(application)

    api = APIRouter(prefix=API_PREFIX)

    @api.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            read_only=True,
            schema_version=API_SCHEMA_VERSION,
        )

    @api.get(
        "/ready",
        response_model=ReadinessResponse,
        responses={503: {"model": ReadinessResponse}},
        tags=["health"],
    )
    def readiness():
        artifact_root_ready = resolved.artifact_root.is_dir()
        discovered_runs = len(catalog.list_manifests()) if artifact_root_ready else 0
        payload = ReadinessResponse(
            status="ready" if artifact_root_ready else "not_ready",
            read_only=True,
            artifact_root_ready=artifact_root_ready,
            discovered_runs=discovered_runs,
        )
        if artifact_root_ready:
            return payload
        return JSONResponse(status_code=503, content=payload.model_dump())

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


def _request_id(candidate: str | None) -> str:
    normalized = str(candidate or "").strip()
    if (
        normalized
        and len(normalized) <= 128
        and all(character.isalnum() or character in "-_." for character in normalized)
    ):
        return normalized
    return str(uuid.uuid4())


app = create_app()
