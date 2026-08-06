from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

import pandas as pd

from src.config.loader import normalize_month
from src.graph_store.base import GraphRepository, PathLike
from src.ingestion.network_data_extractor import (
    create_user_df,
    get_creator_spreader,
    parse_node_dict,
)
from src.ingestion.schema import (
    INTERACTION_EDGE_COLUMNS,
    LEGACY_EXPORT_COLUMNS,
    RAW_TO_DERIVED_MAPPINGS,
    RawToDerivedMapping,
)
from src.network.follower_followee import get_follower_followee_network


@dataclass(frozen=True)
class IngestionPipelineResult:
    """Artifacts produced by the raw-to-derived ingestion pipeline."""

    users: pd.DataFrame
    network: pd.DataFrame
    interactions: pd.DataFrame
    output_path: Optional[Path]


def build_snapshot_meta(config: Mapping[str, Any]) -> dict[str, Any]:
    """Build repository snapshot metadata from a run config."""
    return {
        "data_type": str(config["data_type"]),
        "content_type": str(config["content_type"]),
        "month": normalize_month(config["month"]),
        "year": int(config["year"]),
    }


def resolve_raw_to_derived_mapping(config: Mapping[str, Any]) -> RawToDerivedMapping:
    """Return an explicit mapping for the configured platform/content type."""
    data_type = str(config["data_type"])
    content_type = str(config["content_type"])
    key = f"{data_type}_{content_type}"
    if key in RAW_TO_DERIVED_MAPPINGS:
        return RAW_TO_DERIVED_MAPPINGS[key]

    required = (
        "creator_relation",
        "spreader_relation",
        "creator_node_column",
        "spreader_node_column",
        "text_node_column",
        "date_column",
    )
    missing = [name for name in required if name not in config]
    if missing:
        raise ValueError(
            "No raw-to-derived mapping constant exists for "
            f"{key!r}, and config is missing: {', '.join(missing)}"
        )

    return RawToDerivedMapping(
        content_type=content_type,
        creator_relation=str(config["creator_relation"]),
        spreader_relation=str(config["spreader_relation"]),
        source_user_column=str(config["creator_node_column"]),
        target_user_column=str(config["spreader_node_column"]),
        message_node_column=str(config["text_node_column"]),
        date_field=str(config["date_column"]),
    )


def load_legacy_relationship_csv(csv_path: PathLike) -> pd.DataFrame:
    """Load and validate a legacy `source,target,relation` graph export."""
    df = pd.read_csv(csv_path, low_memory=False)
    missing = [column for column in LEGACY_EXPORT_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            "Legacy relationship CSV is missing required columns: " + ", ".join(missing)
        )
    return df


def derive_network_dataframe(
    df_raw: pd.DataFrame, mapping: RawToDerivedMapping
) -> pd.DataFrame:
    """Create message-level rows with thesis `from_id` and `forwarder_id` fields."""
    df_creator, df_spreader = get_creator_spreader(
        df_raw, mapping.creator_relation, mapping.spreader_relation
    )
    creator_records = _relationship_records(
        df_creator,
        user_column=mapping.source_user_column,
        role="creator",
    )
    spreader_records = _relationship_records(
        df_spreader,
        user_column=mapping.target_user_column,
        role="spreader",
    )

    rows: list[dict[str, Any]] = []
    spreaders_by_message: dict[str, list[dict[str, Any]]] = {}
    for record in spreader_records:
        spreaders_by_message.setdefault(record["message_id"], []).append(record)

    for creator in creator_records:
        for spreader in spreaders_by_message.get(creator["message_id"], []):
            message = dict(creator["message"])
            message.update(
                {
                    "from_id": creator["user_id"],
                    "forwarder_id": spreader["user_id"],
                }
            )
            rows.append(message)

    if rows:
        return pd.DataFrame(rows).reset_index(drop=True)
    return pd.DataFrame(columns=["from_id", "forwarder_id"])


def build_interaction_dataframe(
    df_raw: pd.DataFrame, config: Mapping[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Convert raw graph relationships into users, network rows, and IF/WIF edges."""
    mapping = resolve_raw_to_derived_mapping(config)
    df_creator, df_spreader = get_creator_spreader(
        df_raw, mapping.creator_relation, mapping.spreader_relation
    )
    df_users = create_user_df(
        df_spreader,
        df_creator,
        mapping.source_user_column,
        mapping.target_user_column,
    )
    df_network = derive_network_dataframe(df_raw, mapping)
    df_interactions = get_follower_followee_network(df_network)
    return df_users, df_network, _with_snapshot_columns(df_interactions, config)


def write_interactions(df_interactions: pd.DataFrame, output_path: PathLike) -> Path:
    """Write derived edges in the format declared by the file extension."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        column for column in INTERACTION_EDGE_COLUMNS if column in df_interactions
    ]
    frame = df_interactions[columns]
    if path.suffix.lower() == ".parquet":
        frame.to_parquet(path, index=False)
    elif path.suffix.lower() == ".csv":
        frame.to_csv(path, index=False)
    else:
        raise ValueError(
            f"Unsupported interaction output format {path.suffix!r}; "
            "expected .csv or .parquet"
        )
    return path


def write_interactions_csv(
    df_interactions: pd.DataFrame, output_path: PathLike
) -> Path:
    """Backward-compatible alias for format-aware interaction output."""
    return write_interactions(df_interactions, output_path)


def run_ingestion_pipeline(
    config: Mapping[str, Any],
    repository: Optional[GraphRepository] = None,
    raw_csv_path: Optional[PathLike] = None,
    output_csv_path: Optional[PathLike] = None,
    import_to_repository: bool = True,
) -> IngestionPipelineResult:
    """Run the raw legacy CSV -> derived monthly interaction ingestion flow."""
    input_path = Path(raw_csv_path or config["input_path"])
    df_raw = load_legacy_relationship_csv(input_path)
    df_users, df_network, df_interactions = build_interaction_dataframe(df_raw, config)

    output_path = (
        Path(output_csv_path)
        if output_csv_path is not None
        else _default_interaction_output_path(config)
    )

    written_path: Optional[Path] = None
    if output_path is not None:
        written_path = write_interactions(df_interactions, output_path)

    if import_to_repository:
        if repository is None:
            raise ValueError("repository is required when import_to_repository=True")
        if written_path is None:
            raise ValueError("output_csv_path is required for repository import")
        repository.import_interactions(written_path, build_snapshot_meta(config))

    return IngestionPipelineResult(
        users=df_users,
        network=df_network,
        interactions=df_interactions,
        output_path=written_path,
    )


def _relationship_records(
    df: pd.DataFrame, user_column: str, role: str
) -> list[dict[str, Any]]:
    """Parse relationship rows while caching repeated serialized nodes."""
    other_columns = [column for column in ("source", "target") if column != user_column]
    selected_columns = [user_column, *other_columns]
    missing = [column for column in selected_columns if column not in df.columns]
    if missing:
        raise ValueError(
            "Relationship dataframe is missing required columns: " + ", ".join(missing)
        )

    parse_cache: dict[str, dict[str, Any]] = {}

    def parse_cached(value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            cached = parse_cache.get(value)
            if cached is None:
                cached = parse_node_dict(value)
                parse_cache[value] = cached
            return cached
        return parse_node_dict(value)

    records: list[dict[str, Any]] = []
    for values in df.loc[:, selected_columns].itertuples(index=False, name=None):
        user = parse_cached(values[0])
        message: dict[str, Any] = {}
        for value in values[1:]:
            candidate = parse_cached(value)
            if candidate and "user_id" not in candidate:
                message = candidate
                break

        user_id = user.get("user_id") or user.get("id") or user.get("from_id")
        message_id = (
            message.get("unique_id")
            or message.get("message_id")
            or message.get("reply_id")
            or message.get("tweet_id")
            or message.get("id")
        )
        if user_id in (None, "") or message_id in (None, ""):
            continue
        records.append(
            {
                "role": role,
                "user_id": user_id,
                "message_id": str(message_id),
                "message": message,
            }
        )
    return records


def _with_snapshot_columns(
    df_interactions: pd.DataFrame, config: Mapping[str, Any]
) -> pd.DataFrame:
    snapshot = build_snapshot_meta(config)
    df = df_interactions.copy()
    for column in ("source", "target", "total_post", "shared_post", "weighted_post"):
        if column not in df.columns:
            df[column] = pd.Series(dtype="object")
    df["data_type"] = snapshot["data_type"]
    df["content_type"] = snapshot["content_type"]
    df["month"] = snapshot["month"]
    df["year"] = snapshot["year"]
    return df[list(INTERACTION_EDGE_COLUMNS)]


def _default_interaction_output_path(config: Mapping[str, Any]) -> Path:
    snapshot = build_snapshot_meta(config)
    return (
        Path(str(config.get("output_base_path", "results")))
        / "ingestion"
        / snapshot["data_type"]
        / snapshot["content_type"]
        / f"{snapshot['month']:02d}_{snapshot['year']}_interactions.parquet"
    )
