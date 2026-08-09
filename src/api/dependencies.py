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
from src.api.services.theme_trend_service import ThemeTrendService
from src.api.services.theme_cluster_service import ThemeClusterService


@dataclass(frozen=True)
class ApiSettings:
    artifact_root: Path
    max_graph_nodes: int = 1000
    max_graph_edges: int = 5000
    catalog_refresh_seconds: float = 1.0
    parquet_cache_max_bytes: int = 16 * 1024 * 1024
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )
    allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "testserver")
    root_path: str = ""
    docs_enabled: bool = True
    gzip_minimum_size: int = 1024

    @classmethod
    def from_env(cls, artifact_root: str | Path | None = None) -> "ApiSettings":
        from src.config.settings import get_api_settings

        env_settings = get_api_settings()
        root = artifact_root or env_settings.artifact_root or "local_output"

        raw_origins = env_settings.cors_origins or ""
        origins: tuple[str, ...] = (
            tuple(o.strip() for o in raw_origins.split(",") if o.strip())
            if raw_origins.strip()
            else (
                "http://127.0.0.1:4173",
                "http://localhost:4173",
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            )
        )
        raw_hosts = env_settings.allowed_hosts or ""
        allowed_hosts = (
            tuple(host.strip() for host in raw_hosts.split(",") if host.strip())
            if raw_hosts.strip()
            else ("127.0.0.1", "localhost", "testserver")
        )
        return cls(
            artifact_root=Path(root).expanduser(),
            max_graph_nodes=env_settings.max_graph_nodes,
            max_graph_edges=env_settings.max_graph_edges,
            catalog_refresh_seconds=env_settings.catalog_refresh_seconds,
            parquet_cache_max_bytes=env_settings.parquet_cache_max_bytes,
            cors_origins=origins,
            allowed_hosts=allowed_hosts,
            root_path=env_settings.root_path.strip(),
            docs_enabled=env_settings.docs_enabled,
            gzip_minimum_size=env_settings.gzip_minimum_size,
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


def get_theme_trend_service(request: Request) -> ThemeTrendService:
    return request.app.state.theme_trend_service


def get_theme_cluster_service(request: Request) -> ThemeClusterService:
    return request.app.state.theme_cluster_service


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
