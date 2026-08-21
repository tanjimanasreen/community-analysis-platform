from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from src.graph_store.base import GraphRepository, PathLike, SnapshotMeta
from src.ingestion.memgraph_loader import clean_dict_string, generate_batched_cypher
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

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        client: Optional[Any] = None,
        *,
        interaction_batch_size: int = 1000,
        raw_batch_size: int = 1000,
        **client_kwargs: Any,
    ) -> None:
        if client is None:
            from src.graph_store.memgraph_client import MemgraphClient

            client = MemgraphClient(**client_kwargs)
        if interaction_batch_size < 1:
            raise ValueError("interaction_batch_size must be at least 1")
        if raw_batch_size < 1:
            raise ValueError("raw_batch_size must be at least 1")
        self.client = client
        self.interaction_batch_size = int(interaction_batch_size)
        self.raw_batch_size = int(raw_batch_size)

    def check_connectivity(self) -> None:
        self.client.execute_query("RETURN 1 AS ok")

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
        current_query: str | None = None
        batch: list[dict[str, Any]] = []
        imported_rows = 0
        skipped_rows = 0

        def flush() -> None:
            nonlocal batch, imported_rows
            if current_query is None or not batch:
                return
            self.client.execute_query(
                current_query, {"rows": batch, "platform": platform}
            )
            imported_rows += len(batch)
            batch = []

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
                query, params = generate_batched_cypher(
                    source, target, row["relation"], platform
                )
                if query is None:
                    skipped_rows += 1
                    continue
                # Batch only consecutive rows with the same static label/
                # relationship shape. Flushing on shape changes preserves the
                # legacy import order when repeated node properties differ.
                if current_query is not None and query != current_query:
                    flush()
                current_query = query
                batch.append(params)
                if len(batch) >= self.raw_batch_size:
                    flush()
            flush()

        logger.info(
            "memgraph_raw_import_completed rows=%d skipped_rows=%d batch_size=%d",
            imported_rows,
            skipped_rows,
            self.raw_batch_size,
        )

    def import_interactions(self, path: PathLike, snapshot_meta: SnapshotMeta) -> None:
        import pandas as pd

        interaction_path = Path(path)
        if interaction_path.suffix.lower() == ".parquet":
            df = pd.read_parquet(interaction_path)
        elif interaction_path.suffix.lower() == ".csv":
            df = pd.read_csv(interaction_path)
        else:
            raise ValueError(
                f"Unsupported interaction input format {interaction_path.suffix!r}; "
                "expected .csv or .parquet"
            )
        required_columns = {
            "source",
            "target",
            "total_post",
            "shared_post",
        }
        missing_columns = sorted(required_columns - set(df.columns))
        if missing_columns:
            raise ValueError(
                "Interaction data is missing required columns: "
                + ", ".join(missing_columns)
            )

        columns = list(df.columns)
        batch: list[dict[str, Any]] = []
        imported_rows = 0
        skipped_self_edges = 0
        # Stream rows from the already loaded dataframe. ``to_dict(records)``
        # duplicates the complete table as Python dictionaries and can consume
        # several additional gigabytes for full Twitter imports.
        for values in df.itertuples(index=False, name=None):
            row = dict(zip(columns, values))
            source = str(row["source"])
            target = str(row["target"])
            if source == target:
                skipped_self_edges += 1
                continue

            batch.append(_interaction_params(row, snapshot_meta))
            if len(batch) >= self.interaction_batch_size:
                self.client.execute_query(IMPORT_INTERACTIONS_QUERY, {"rows": batch})
                imported_rows += len(batch)
                batch = []
        if batch:
            self.client.execute_query(IMPORT_INTERACTIONS_QUERY, {"rows": batch})
            imported_rows += len(batch)

        logger.info(
            "memgraph_interaction_import_completed rows=%d skipped_self_edges=%d "
            "batch_size=%d",
            imported_rows,
            skipped_self_edges,
            self.interaction_batch_size,
        )

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
        import pandas as pd

        df = pd.DataFrame(rows, columns=fieldnames)
        output_path = Path(out_path)
        if output_path.suffix.lower() != ".parquet":
            raise ValueError(
                "Unsupported generated interaction export format "
                f"{output_path.suffix!r}; "
                "expected .parquet"
            )
        df.to_parquet(output_path, index=False)

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


IMPORT_INTERACTIONS_QUERY = """
UNWIND $rows AS row
MERGE (src:User {user_id: row.source})
MERGE (dst:User {user_id: row.target})
WITH src, dst, row
MERGE (src)-[e:USER_INTERACTED_WITH {
  data_type: row.data_type,
  content_type: row.content_type,
  month: row.month,
  year: row.year
}]->(dst)
ON CREATE SET e.shared_post = row.shared_post,
              e.total_post = row.total_post,
              e.weighted_post = row.weighted_post
ON MATCH SET e.shared_post = e.shared_post + row.shared_post,
             e.total_post = e.total_post + row.total_post
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
