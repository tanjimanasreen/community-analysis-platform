from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.artifact_service import (
    DEFAULT_LIMIT,
    ArtifactService,
    ArtifactServiceError,
)
from backend.schemas import (
    ArtifactsResponse,
    CommunitySummaryResponse,
    FacetsResponse,
    FilesResponse,
    HealthResponse,
    RunsResponse,
    TableResponse,
    VerificationResponse,
)


def create_app(config_paths=None, configs=None) -> FastAPI:
    service = ArtifactService(config_paths=config_paths, configs=configs)
    app = FastAPI(title="Community Analysis Artifact API")
    app.state.artifact_service = service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.exception_handler(ArtifactServiceError)
    def handle_artifact_service_error(_request, exc: ArtifactServiceError):
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health():
        return service.health()

    @app.get("/api/v1/runs", response_model=RunsResponse)
    def runs():
        return {"runs": service.list_runs()}

    @app.get("/api/v1/runs/{run_id}/facets", response_model=FacetsResponse)
    def facets(run_id: str):
        return service.facets(run_id)

    @app.get("/api/v1/runs/{run_id}/verification", response_model=VerificationResponse)
    def verification(run_id: str):
        return service.verification(run_id)

    @app.get("/api/v1/runs/{run_id}/artifacts", response_model=ArtifactsResponse)
    def artifacts(run_id: str):
        return {"artifacts": service.artifacts(run_id)}

    @app.get("/api/v1/runs/{run_id}/community-summary", response_model=CommunitySummaryResponse)
    def community_summary(run_id: str, month: str):
        return service.community_summary(run_id, month)

    @app.get("/api/v1/runs/{run_id}/communities", response_model=TableResponse)
    def communities(
        run_id: str,
        month: str,
        match_type: str = Query("matched", pattern="^(matched|partial)$"),
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        return service.communities(run_id, month, match_type, limit, offset)

    @app.get("/api/v1/runs/{run_id}/topics", response_model=TableResponse)
    def topics(
        run_id: str,
        month: str,
        type: str = Query("matched", pattern="^(matched|partial|scores)$"),
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        return service.topics(run_id, month, type, limit, offset)

    @app.get("/api/v1/runs/{run_id}/themes", response_model=TableResponse)
    def themes(
        run_id: str,
        month: str,
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        return service.themes(run_id, month, limit, offset)

    @app.get("/api/v1/runs/{run_id}/transitions", response_model=TableResponse)
    def transitions(
        run_id: str,
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        return service.transitions(run_id, limit, offset)

    @app.get("/api/v1/runs/{run_id}/files", response_model=FilesResponse)
    def files(run_id: str):
        return {"files": service.files(run_id)}

    @app.get("/api/datasets")
    def legacy_datasets():
        datasets = sorted({run["data_type"] for run in service.list_runs()})
        return {"datasets": datasets}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
