from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from fastapi import Request

from src.api.services.artifact_reader import ArtifactReader
from src.api.services.evolution_service import EvolutionService
from src.api.services.network_service import NetworkService
from src.api.services.overview_service import OverviewService
from src.api.services.run_catalog import RunCatalog
from src.api.services.topic_service import TopicService


@dataclass(frozen=True)
class ApiSettings:
    artifact_root: Path
    max_graph_nodes: int = 1000
    max_graph_edges: int = 5000
    catalog_refresh_seconds: float = 1.0

    @classmethod
    def from_env(cls, artifact_root: str | Path | None = None) -> "ApiSettings":
        root = artifact_root or os.environ.get(
            "COMMUNITY_ANALYSIS_ARTIFACT_ROOT", "results"
        )
        return cls(
            artifact_root=Path(root).expanduser(),
            max_graph_nodes=_positive_int(
                os.environ.get("COMMUNITY_ANALYSIS_API_MAX_GRAPH_NODES"), 1000
            ),
            max_graph_edges=_positive_int(
                os.environ.get("COMMUNITY_ANALYSIS_API_MAX_GRAPH_EDGES"), 5000
            ),
            catalog_refresh_seconds=_non_negative_float(
                os.environ.get("COMMUNITY_ANALYSIS_API_CATALOG_REFRESH_SECONDS"),
                1.0,
            ),
        )


def get_settings(request: Request) -> ApiSettings:
    return request.app.state.api_settings


def get_run_catalog(request: Request) -> RunCatalog:
    return request.app.state.run_catalog


def get_artifact_reader(request: Request) -> ArtifactReader:
    return request.app.state.artifact_reader


def get_overview_service(request: Request) -> OverviewService:
    return request.app.state.overview_service


def get_network_service(request: Request) -> NetworkService:
    return request.app.state.network_service


def get_topic_service(request: Request) -> TopicService:
    return request.app.state.topic_service


def get_evolution_service(request: Request) -> EvolutionService:
    return request.app.state.evolution_service


def _positive_int(value: str | None, default: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _non_negative_float(value: str | None, default: float) -> float:
    try:
        parsed = float(value) if value is not None else default
    except ValueError:
        return default
    return parsed if parsed >= 0 else default
