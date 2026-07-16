from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

SCHEMA_VERSION = 1

ABSOLUTE_COMMUNITY_MESSAGES_FILE = "absolute_community_messages.csv"
WEIGHTED_COMMUNITY_MESSAGES_FILE = "weighted_community_messages.csv"
MATCHED_COMMUNITIES_FILE = "matched_communities.csv"
PARTIAL_MATCHED_COMMUNITIES_FILE = "partial_matched_communities.csv"
MANIFEST_FILE = "manifest.json"

COMMUNITY_MESSAGE_COLUMNS = [
    "community_number",
    "messages",
    "messages_ids",
    "total_messages",
]
MATCHED_COMMUNITY_COLUMNS = [
    "abs_community",
    "per_community",
    "jaccard_score",
    "members",
]
PARTIAL_MATCHED_COMMUNITY_COLUMNS = [
    "abs_community",
    "absolute_members",
    "per_community",
    "weighted_members",
    "jaccard_score",
    "common_members",
    "uncommon_members",
]

LIST_COLUMNS = {
    "messages",
    "messages_ids",
    "members",
    "absolute_members",
    "weighted_members",
    "common_members",
    "uncommon_members",
}


class TopicInputError(ValueError):
    """Raised when saved topic-input artifacts are missing or invalid."""


@dataclass(frozen=True)
class TopicInputBundle:
    absolute_community_messages: pd.DataFrame
    weighted_community_messages: pd.DataFrame
    matched_communities: pd.DataFrame
    partial_matched_communities: pd.DataFrame
    manifest: dict[str, Any]


def build_topic_input_dir(
    config_or_params: Mapping[str, Any] | None = None,
    *,
    output_base_path: str | None = None,
    data_type: str | None = None,
    content_type: str | None = None,
    month: str | int | None = None,
    year: str | int | None = None,
) -> Path:
    params = dict(config_or_params or {})
    base = (
        output_base_path
        or params.get("output_base_path")
        or params.get("output_dir")
        or "results/"
    )
    data = data_type or params.get("data_type", "twitter")
    content = content_type or params.get("content_type", "reply")
    month_value = str(month if month is not None else params.get("month", "march"))
    year_value = str(year if year is not None else params.get("year", "2017"))

    return (
        Path(base)
        / str(data)
        / "_intermediate"
        / "topic_inputs"
        / str(content)
        / f"{month_value}_{year_value}"
    )


def save_topic_inputs(
    *,
    absolute_community_messages: pd.DataFrame,
    weighted_community_messages: pd.DataFrame,
    matched_communities: pd.DataFrame,
    partial_matched_communities: pd.DataFrame,
    output_base_path: str,
    data_type: str,
    content_type: str,
    month: str | int,
    year: str | int,
) -> Path:
    output_dir = build_topic_input_dir(
        output_base_path=output_base_path,
        data_type=data_type,
        content_type=content_type,
        month=month,
        year=year,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_dataframe(
        absolute_community_messages,
        output_dir / ABSOLUTE_COMMUNITY_MESSAGES_FILE,
        COMMUNITY_MESSAGE_COLUMNS,
    )
    _write_dataframe(
        weighted_community_messages,
        output_dir / WEIGHTED_COMMUNITY_MESSAGES_FILE,
        COMMUNITY_MESSAGE_COLUMNS,
    )
    _write_dataframe(
        matched_communities,
        output_dir / MATCHED_COMMUNITIES_FILE,
        MATCHED_COMMUNITY_COLUMNS,
    )
    _write_dataframe(
        partial_matched_communities,
        output_dir / PARTIAL_MATCHED_COMMUNITIES_FILE,
        PARTIAL_MATCHED_COMMUNITY_COLUMNS,
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "data_type": str(data_type),
        "content_type": str(content_type),
        "month": str(month),
        "year": str(year),
        "files": {
            "absolute_community_messages": ABSOLUTE_COMMUNITY_MESSAGES_FILE,
            "weighted_community_messages": WEIGHTED_COMMUNITY_MESSAGES_FILE,
            "matched_communities": MATCHED_COMMUNITIES_FILE,
            "partial_matched_communities": PARTIAL_MATCHED_COMMUNITIES_FILE,
        },
    }
    (output_dir / MANIFEST_FILE).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return output_dir


def load_topic_inputs(
    config_or_params: Mapping[str, Any] | None = None,
    *,
    output_base_path: str | None = None,
    data_type: str | None = None,
    content_type: str | None = None,
    month: str | int | None = None,
    year: str | int | None = None,
) -> TopicInputBundle:
    input_dir = build_topic_input_dir(
        config_or_params,
        output_base_path=output_base_path,
        data_type=data_type,
        content_type=content_type,
        month=month,
        year=year,
    )
    manifest_path = input_dir / MANIFEST_FILE
    if not manifest_path.exists():
        raise TopicInputError(
            f"Topic input manifest not found at {manifest_path}. "
            "Run run-social-network first to create topic prerequisites."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = _expected_metadata(
        config_or_params, output_base_path, data_type, content_type, month, year
    )
    _validate_manifest(manifest, expected, manifest_path)

    bundle = TopicInputBundle(
        absolute_community_messages=_read_dataframe(
            input_dir / ABSOLUTE_COMMUNITY_MESSAGES_FILE,
            COMMUNITY_MESSAGE_COLUMNS,
        ),
        weighted_community_messages=_read_dataframe(
            input_dir / WEIGHTED_COMMUNITY_MESSAGES_FILE,
            COMMUNITY_MESSAGE_COLUMNS,
        ),
        matched_communities=_read_dataframe(
            input_dir / MATCHED_COMMUNITIES_FILE,
            MATCHED_COMMUNITY_COLUMNS,
        ),
        partial_matched_communities=_read_dataframe(
            input_dir / PARTIAL_MATCHED_COMMUNITIES_FILE,
            PARTIAL_MATCHED_COMMUNITY_COLUMNS,
        ),
        manifest=manifest,
    )
    validate_topic_inputs(bundle)
    return bundle


def validate_topic_inputs(bundle: TopicInputBundle) -> None:
    _ensure_columns(
        bundle.absolute_community_messages,
        COMMUNITY_MESSAGE_COLUMNS,
        ABSOLUTE_COMMUNITY_MESSAGES_FILE,
    )
    _ensure_columns(
        bundle.weighted_community_messages,
        COMMUNITY_MESSAGE_COLUMNS,
        WEIGHTED_COMMUNITY_MESSAGES_FILE,
    )
    _ensure_columns(
        bundle.matched_communities, MATCHED_COMMUNITY_COLUMNS, MATCHED_COMMUNITIES_FILE
    )
    _ensure_columns(
        bundle.partial_matched_communities,
        PARTIAL_MATCHED_COMMUNITY_COLUMNS,
        PARTIAL_MATCHED_COMMUNITIES_FILE,
    )
    for name, df in [
        (ABSOLUTE_COMMUNITY_MESSAGES_FILE, bundle.absolute_community_messages),
        (WEIGHTED_COMMUNITY_MESSAGES_FILE, bundle.weighted_community_messages),
        (MATCHED_COMMUNITIES_FILE, bundle.matched_communities),
        (PARTIAL_MATCHED_COMMUNITIES_FILE, bundle.partial_matched_communities),
    ]:
        for column in LIST_COLUMNS.intersection(df.columns):
            invalid = [
                value for value in df[column].tolist() if not isinstance(value, list)
            ]
            if invalid:
                raise TopicInputError(
                    f"{name} column {column!r} must contain list values."
                )


def _write_dataframe(df: pd.DataFrame, path: Path, required_columns: list[str]) -> None:
    frame = df.copy() if df is not None else pd.DataFrame()
    for column in required_columns:
        if column not in frame.columns:
            frame[column] = pd.Series(dtype="object")
    frame = frame[
        required_columns
        + [column for column in frame.columns if column not in required_columns]
    ]
    for column in LIST_COLUMNS.intersection(frame.columns):
        frame[column] = frame[column].apply(_json_dumps)
    frame.to_csv(path, index=False)


def _read_dataframe(path: Path, required_columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise TopicInputError(
            f"Required topic input file not found at {path}. "
            "Run run-social-network first to create topic prerequisites."
        )
    frame = pd.read_csv(path, low_memory=False)
    _ensure_columns(frame, required_columns, path.name)
    for column in LIST_COLUMNS.intersection(frame.columns):
        frame[column] = frame[column].apply(_parse_list)
    return frame


def _ensure_columns(df: pd.DataFrame, required_columns: list[str], name: str) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise TopicInputError(f"{name} is missing required columns: {missing}")


def _json_dumps(value: Any) -> str:
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return json.dumps([value])
    if isinstance(value, (tuple, set)):
        value = list(value)
    if not isinstance(value, list):
        if pd.isna(value):
            value = []
        else:
            value = [value]
    return json.dumps([_to_jsonable(item) for item in value])


def _parse_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if pd.isna(value) or value == "":
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                return [value]
        if isinstance(parsed, list):
            return parsed
        return [parsed]
    return [value]


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value


def _expected_metadata(
    config_or_params: Mapping[str, Any] | None,
    output_base_path: str | None,
    data_type: str | None,
    content_type: str | None,
    month: str | int | None,
    year: str | int | None,
) -> dict[str, str]:
    params = dict(config_or_params or {})
    return {
        "data_type": str(data_type or params.get("data_type", "twitter")),
        "content_type": str(content_type or params.get("content_type", "reply")),
        "month": str(month if month is not None else params.get("month", "march")),
        "year": str(year if year is not None else params.get("year", "2017")),
    }


def _validate_manifest(
    manifest: Mapping[str, Any], expected: Mapping[str, str], path: Path
) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise TopicInputError(
            f"{path} has unsupported schema_version={manifest.get('schema_version')!r}; "
            f"expected {SCHEMA_VERSION}."
        )
    mismatches = {
        key: {"expected": value, "actual": str(manifest.get(key))}
        for key, value in expected.items()
        if str(manifest.get(key)) != value
    }
    if mismatches:
        raise TopicInputError(
            f"{path} metadata does not match requested run: {mismatches}"
        )
