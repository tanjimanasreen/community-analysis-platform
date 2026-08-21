from __future__ import annotations

from typing import Any, Mapping

from src.graph_store.base import GraphRepository
from src.graph_store.memgraph_repository import MemgraphRepository

SUPPORTED_GRAPH_DATABASE_ENGINES = ("memgraph",)


def create_graph_repository(database_config: Mapping[str, Any]) -> GraphRepository:
    """Create the configured graph repository from resolved runtime settings."""
    engine = str(database_config.get("engine") or "memgraph").strip().lower()
    if engine == "memgraph":
        return MemgraphRepository(
            uri=database_config.get("uri"),
            user=database_config.get("user"),
            password=database_config.get("password"),
        )

    supported = ", ".join(SUPPORTED_GRAPH_DATABASE_ENGINES)
    raise ValueError(
        f"Graph database backend {engine!r} is not currently implemented. "
        f"Supported backend(s): {supported}."
    )
