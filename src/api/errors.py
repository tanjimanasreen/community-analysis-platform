from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    """Stable error envelope returned by every API-owned failure."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    run_id: str | None = None
    artifact_key: str | None = None
    details: dict[str, Any] | None = None


class ApiError(Exception):
    """Base exception carrying an HTTP status and stable machine code."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        run_id: str | None = None,
        artifact_key: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.run_id = run_id
        self.artifact_key = artifact_key
        self.details = details

    def response(self) -> ErrorResponse:
        return ErrorResponse(
            code=self.code,
            message=self.message,
            run_id=self.run_id,
            artifact_key=self.artifact_key,
            details=self.details,
        )


class RunNotFoundError(ApiError):
    def __init__(self, run_id: str) -> None:
        super().__init__(
            code="RUN_NOT_FOUND",
            message="The requested pipeline run does not exist.",
            status_code=404,
            run_id=run_id,
        )


class InvalidManifestError(ApiError):
    def __init__(
        self, run_id: str, message: str = "The run manifest is invalid."
    ) -> None:
        super().__init__(
            code="INVALID_MANIFEST",
            message=message,
            status_code=422,
            run_id=run_id,
        )


class RunNotCompletedError(ApiError):
    def __init__(self, run_id: str, status: str) -> None:
        super().__init__(
            code="RUN_NOT_COMPLETED",
            message="Analytical artifacts are available only for completed runs.",
            status_code=409,
            run_id=run_id,
            details={"status": status},
        )


class ArtifactNotFoundError(ApiError):
    def __init__(self, run_id: str, artifact_key: str) -> None:
        super().__init__(
            code="ARTIFACT_MISSING",
            message="The requested artifact is not listed in the run manifest.",
            status_code=404,
            run_id=run_id,
            artifact_key=artifact_key,
        )


class ArtifactUnavailableError(ApiError):
    def __init__(self, run_id: str, artifact_key: str) -> None:
        super().__init__(
            code="ARTIFACT_NOT_AVAILABLE",
            message="This optional artifact is not available for the selected run.",
            status_code=404,
            run_id=run_id,
            artifact_key=artifact_key,
        )


class ArtifactValidationError(ApiError):
    def __init__(
        self,
        *,
        run_id: str,
        artifact_key: str,
        validation_message: str,
    ) -> None:
        normalized = validation_message.lower()
        if "checksum mismatch" in normalized:
            code = "ARTIFACT_CHECKSUM_MISMATCH"
            message = "The requested artifact failed checksum verification."
        elif "schema" in normalized:
            code = "ARTIFACT_SCHEMA_MISMATCH"
            message = "The requested artifact failed schema verification."
        elif "path escapes" in normalized or "outside" in normalized:
            code = "ARTIFACT_PATH_VIOLATION"
            message = "The requested artifact path is outside the configured run root."
        else:
            code = "ARTIFACT_VALIDATION_FAILED"
            message = "The requested artifact failed verification."
        super().__init__(
            code=code,
            message=message,
            status_code=409,
            run_id=run_id,
            artifact_key=artifact_key,
        )


class GraphRequestTooLargeError(ApiError):
    def __init__(
        self,
        *,
        run_id: str,
        requested_nodes: int,
        requested_edges: int,
        max_nodes: int,
        max_edges: int,
    ) -> None:
        super().__init__(
            code="GRAPH_REQUEST_TOO_LARGE",
            message="The requested graph exceeds the configured response limits.",
            status_code=413,
            run_id=run_id,
            details={
                "requested_nodes": requested_nodes,
                "requested_edges": requested_edges,
                "max_nodes": max_nodes,
                "max_edges": max_edges,
            },
        )


class InvalidFilterError(ApiError):
    def __init__(self, message: str, *, run_id: str | None = None) -> None:
        super().__init__(
            code="INVALID_FILTER",
            message=message,
            status_code=422,
            run_id=run_id,
        )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.response().model_dump(mode="json", exclude_none=True),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        payload = ErrorResponse(
            code="INVALID_FILTER",
            message="One or more request parameters are invalid.",
            details={"errors": exc.errors()},
        )
        return JSONResponse(
            status_code=422,
            content=payload.model_dump(mode="json", exclude_none=True),
        )
