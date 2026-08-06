import ast
import csv
import logging
import re
from src.ingestion.schema import (
    PRIMARY_KEYS,
    TELEGRAM_RELATION_MAP,
    TWITTER_RELATION_MAP,
)

logger = logging.getLogger(__name__)


def clean_dict_string(dict_str):
    """
    Cleans the stringified neo4j dictionaries so ast.literal_eval can parse them.
    Replaces neo4j.time.DateTime(...) with a string representation.
    """
    datetime_pattern = re.compile(
        r"neo4j\.time\.DateTime\((.*?)tzinfo=<UTC>\)", re.DOTALL
    )
    cleaned = datetime_pattern.sub(r"'neo4j_time_(\1)'", dict_str)
    return cleaned


def _resolve_edge_shape(source_dict, target_dict, relation, platform):
    mapping = TELEGRAM_RELATION_MAP if platform == "telegram" else TWITTER_RELATION_MAP
    if relation not in mapping:
        logger.warning(
            "Skipping edge: unrecognized platform=%r / relation=%r. "
            "Check your config's creator_relation and spreader_relation values.",
            platform,
            relation,
        )
        return None

    source_label, target_label = mapping[relation]
    source_pk_field = PRIMARY_KEYS.get(source_label, "id")
    target_pk_field = PRIMARY_KEYS.get(target_label, "id")
    source_pk_val = (
        source_dict.get(source_pk_field)
        or source_dict.get("id")
        or source_dict.get("to_id")
        or source_dict.get("from_id")
    )
    target_pk_val = (
        target_dict.get(target_pk_field)
        or target_dict.get("id")
        or target_dict.get("to_id")
        or target_dict.get("from_id")
    )
    if not source_pk_val or not target_pk_val:
        return None
    return (
        source_label,
        target_label,
        source_pk_field,
        target_pk_field,
        source_pk_val,
        target_pk_val,
    )


def generate_batched_cypher(source_dict, target_dict, relation, platform):
    """Return a static-shape UNWIND query and one row of parameters.

    Labels and relationship types come only from the allowlisted schema maps,
    so the generated identifiers are not user-controlled. Callers may batch
    consecutive rows that return the same query without changing import order.
    """
    shape = _resolve_edge_shape(source_dict, target_dict, relation, platform)
    if shape is None:
        return None, None
    (
        source_label,
        target_label,
        source_pk_field,
        target_pk_field,
        source_pk_val,
        target_pk_val,
    ) = shape
    query = f"""
    UNWIND $rows AS row
    MERGE (s:{source_label} {{{source_pk_field}: row.source_pk}})
    SET s += row.source_props
    SET s.platform = $platform

    MERGE (t:{target_label} {{{target_pk_field}: row.target_pk}})
    SET t += row.target_props
    SET t.platform = $platform

    MERGE (s)-[r:{relation}]->(t)
    """
    return query, {
        "source_pk": source_pk_val,
        "source_props": source_dict,
        "target_pk": target_pk_val,
        "target_props": target_dict,
    }


def generate_cypher(source_dict, target_dict, relation, platform):
    shape = _resolve_edge_shape(source_dict, target_dict, relation, platform)
    if shape is None:
        return None, None
    (
        source_label,
        target_label,
        source_pk_field,
        target_pk_field,
        source_pk_val,
        target_pk_val,
    ) = shape

    query = f"""
    MERGE (s:{source_label} {{{source_pk_field}: $source_pk}})
    SET s += $source_props
    SET s.platform = $platform

    MERGE (t:{target_label} {{{target_pk_field}: $target_pk}})
    SET t += $target_props
    SET t.platform = $platform

    MERGE (s)-[r:{relation}]->(t)
    """
    return query, {
        "source_pk": source_pk_val,
        "source_props": source_dict,
        "target_pk": target_pk_val,
        "target_props": target_dict,
        "platform": platform,
    }


class MemgraphLoader:
    def __init__(self, client=None, *, batch_size: int = 1000):
        if client is None:
            from src.graph_store.memgraph_client import MemgraphClient

            client = MemgraphClient()
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self.client = client
        self.batch_size = int(batch_size)

    def load_csv(self, file_path, platform):
        """
        Loads the exported CSV and imports it into Memgraph.
        """
        success_count = 0
        error_count = 0

        current_query = None
        batch = []

        def flush() -> None:
            nonlocal success_count, batch
            if current_query is None or not batch:
                return
            self.client.execute_query(
                current_query, {"rows": batch, "platform": platform}
            )
            success_count += len(batch)
            batch = []

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    source_str = clean_dict_string(row["source"])
                    target_str = clean_dict_string(row["target"])
                    source_dict = ast.literal_eval(source_str)
                    target_dict = ast.literal_eval(target_str)
                    query, params = generate_batched_cypher(
                        source_dict, target_dict, row["relation"], platform
                    )
                    if query is None:
                        error_count += 1
                        continue
                    if current_query is not None and query != current_query:
                        flush()
                    current_query = query
                    batch.append(params)
                    if len(batch) >= self.batch_size:
                        flush()
                except Exception as exc:
                    logger.warning(
                        "memgraph_raw_row_failed relation=%s error_type=%s",
                        row.get("relation", ""),
                        type(exc).__name__,
                        exc_info=logger.isEnabledFor(logging.DEBUG),
                    )
                    error_count += 1
            flush()

        return success_count, error_count
