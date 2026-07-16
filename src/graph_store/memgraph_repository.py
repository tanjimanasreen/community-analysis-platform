from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from src.graph_store.base import GraphRepository, PathLike, SnapshotMeta
from src.ingestion.memgraph_loader import clean_dict_string, generate_cypher
from src.ingestion.schema import (
    CHANNEL,
    FORWARD_MESSAGE,
    MESSAGE,
    PRIMARY_KEYS,
    REPLY,
    RETWEET_QUOTE,
    TWITTER_USER,
    USER,
)

INDEX_LABELS = (
    USER,
    CHANNEL,
    MESSAGE,
    FORWARD_MESSAGE,
    TWITTER_USER,
    RETWEET_QUOTE,
    REPLY,
)


class MemgraphRepository(GraphRepository):
    """Memgraph-backed implementation of the graph repository boundary."""

    def __init__(self, client: Optional[Any] = None, **client_kwargs: Any) -> None:
        if client is None:
            from src.graph_store.memgraph_client import MemgraphClient

            client = MemgraphClient(**client_kwargs)
        self.client = client

    def clear(self) -> None:
        self.client.execute_query("MATCH (n) DETACH DELETE n")

    def create_indexes(self) -> None:
        for label in INDEX_LABELS:
            property_name = PRIMARY_KEYS[label]
            try:
                self.client.execute_query(f"CREATE INDEX ON :{label}({property_name})")
            except Exception as exc:
                if not _is_existing_index_error(exc):
                    raise

    def import_raw_data(self, data_path: PathLike, platform: str) -> None:
        with Path(data_path).open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = {"source", "target", "relation"} - set(reader.fieldnames or [])
            if missing:
                raise ValueError(
                    "Raw graph CSV is missing required columns: "
                    + ", ".join(sorted(missing))
                )
            for row in reader:
                source = _parse_legacy_node(row["source"])
                target = _parse_legacy_node(row["target"])
                query, params = generate_cypher(
                    source, target, row["relation"], platform
                )
                if query is not None:
                    self.client.execute_query(query, params)

    def import_interactions(
        self, csv_path: PathLike, snapshot_meta: SnapshotMeta
    ) -> None:
        with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                source = str(row["source"])
                target = str(row["target"])
                if source == target:
                    continue

                params = _interaction_params(row, snapshot_meta)
                self.client.execute_query(IMPORT_INTERACTION_QUERY, params)

    def export_interactions(
        self, snapshot_meta: SnapshotMeta, out_path: PathLike
    ) -> None:
        rows = list(self.get_user_interactions(snapshot_meta))
        fieldnames = [
            "source",
            "target",
            "total_post",
            "shared_post",
            "weighted_post",
            "data_type",
            "content_type",
            "month",
            "year",
        ]
        with Path(out_path).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def get_user_interactions(
        self, snapshot_meta: SnapshotMeta
    ) -> Iterable[Mapping[str, Any]]:
        params = {
            "data_type": snapshot_meta["data_type"],
            "content_type": snapshot_meta["content_type"],
            "month": int(snapshot_meta["month"]),
            "year": int(snapshot_meta["year"]),
        }
        records, _summary, _keys = self.client.execute_query(
            EXPORT_INTERACTIONS_QUERY, params
        )
        for record in records:
            data = record.data() if hasattr(record, "data") else dict(record)
            yield data

    def get_distinct_users(self) -> Iterable[str]:
        records, _summary, _keys = self.client.execute_query(
            "MATCH (u:User) RETURN DISTINCT u.user_id AS user_id ORDER BY user_id"
        )
        for record in records:
            data = record.data() if hasattr(record, "data") else dict(record)
            yield data["user_id"]

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if close is not None:
            close()


def _parse_legacy_node(value: str) -> dict[str, Any]:
    import ast

    return ast.literal_eval(clean_dict_string(value))


def _interaction_params(
    row: Mapping[str, str], snapshot_meta: SnapshotMeta
) -> dict[str, Any]:
    shared_post = int(row["shared_post"])
    total_post = int(row["total_post"])
    weighted_post = (
        float(row["weighted_post"])
        if row.get("weighted_post") not in (None, "")
        else (shared_post / total_post if total_post else 0.0)
    )
    return {
        "source": str(row["source"]),
        "target": str(row["target"]),
        "shared_post": shared_post,
        "total_post": total_post,
        "weighted_post": weighted_post,
        "data_type": str(row.get("data_type") or snapshot_meta["data_type"]),
        "content_type": str(row.get("content_type") or snapshot_meta["content_type"]),
        "month": int(row.get("month") or snapshot_meta["month"]),
        "year": int(row.get("year") or snapshot_meta["year"]),
    }


def _is_existing_index_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "already exists" in message and "index" in message


IMPORT_INTERACTION_QUERY = """
MERGE (src:User {user_id: $source})
MERGE (dst:User {user_id: $target})
WITH src, dst
MERGE (src)-[e:USER_INTERACTED_WITH {
  data_type: $data_type,
  content_type: $content_type,
  month: $month,
  year: $year
}]->(dst)
ON CREATE SET e.shared_post = $shared_post,
              e.total_post = $total_post,
              e.weighted_post = $weighted_post
ON MATCH SET e.shared_post = e.shared_post + $shared_post,
             e.total_post = e.total_post + $total_post
WITH e
SET e.weighted_post = CASE
  WHEN e.total_post = 0 THEN 0.0
  ELSE toFloat(e.shared_post) / e.total_post
END
"""

EXPORT_INTERACTIONS_QUERY = """
MATCH (src:User)-[e:USER_INTERACTED_WITH {
  data_type: $data_type,
  content_type: $content_type,
  month: $month,
  year: $year
}]->(dst:User)
RETURN src.user_id AS source,
       dst.user_id AS target,
       e.total_post AS total_post,
       e.shared_post AS shared_post,
       e.weighted_post AS weighted_post,
       e.data_type AS data_type,
       e.content_type AS content_type,
       e.month AS month,
       e.year AS year
ORDER BY source, target
"""
