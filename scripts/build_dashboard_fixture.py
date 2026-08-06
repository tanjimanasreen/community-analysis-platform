#!/usr/bin/env python3
"""Build deterministic, offline dashboard artifacts for frontend/API tests.

The generator writes canonical run manifests and small CSV/JSON/report artifacts.
It does not import pipeline, database, provider, embedding, or visualization code.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from src.artifacts.models import (
    ArtifactCategory,
    ArtifactRecord,
    RunManifest,
    RunStatus,
)
from src.artifacts.run_manifest import validate_run_manifest
from src.reporting import output_contract as contract

_SCHEMA_VERSION = "1"
_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@dataclass(frozen=True)
class RunSpec:
    run_id: str
    platform: str
    content_type: str
    year: int
    month: int
    started_at: str
    sampled_graph: bool = False
    include_optional: bool = True
    empty_semantics: bool = False
    tamper_after_validation: bool = False

    @property
    def month_text(self) -> str:
        return f"{self.month:02d}"


RUN_SPECS = (
    RunSpec(
        run_id="twitter-2017-04",
        platform="twitter",
        content_type="reply",
        year=2017,
        month=4,
        started_at="2026-07-18T06:00:00+00:00",
        sampled_graph=True,
    ),
    RunSpec(
        run_id="twitter-2017-04-reply",
        platform="twitter",
        content_type="reply",
        year=2017,
        month=4,
        started_at="2026-07-18T05:45:00+00:00",
        sampled_graph=True,
    ),
    RunSpec(
        run_id="twitter-2017-04-retweet",
        platform="twitter",
        content_type="retweet_quote",
        year=2017,
        month=4,
        started_at="2026-07-18T05:30:00+00:00",
        sampled_graph=True,
    ),
    RunSpec(
        run_id="twitter-2017-07-tampered",
        platform="twitter",
        content_type="reply",
        year=2017,
        month=7,
        started_at="2026-07-18T05:00:00+00:00",
        tamper_after_validation=True,
    ),
    RunSpec(
        run_id="twitter-2017-06-empty",
        platform="twitter",
        content_type="reply",
        year=2017,
        month=6,
        started_at="2026-07-18T04:00:00+00:00",
        empty_semantics=True,
    ),
    RunSpec(
        run_id="twitter-2017-05-missing",
        platform="twitter",
        content_type="reply",
        year=2017,
        month=5,
        started_at="2026-07-18T03:00:00+00:00",
        include_optional=False,
    ),
    RunSpec(
        run_id="telegram-2017-03",
        platform="telegram",
        content_type="forward",
        year=2017,
        month=3,
        started_at="2026-07-18T02:00:00+00:00",
    ),
    RunSpec(
        run_id="twitter-2017-03",
        platform="twitter",
        content_type="reply",
        year=2017,
        month=3,
        started_at="2026-07-18T01:00:00+00:00",
    ),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()



def _write_parquet(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=columns).to_parquet(path)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _artifact_record(
    root: Path,
    *,
    key: str,
    relative_path: str,
    category: ArtifactCategory,
    media_type: str,
    stage: str,
) -> ArtifactRecord:
    path = root / relative_path
    rows = len(pd.read_parquet(path)) if path.suffix == ".parquet" else None
    return ArtifactRecord(
        key=key,
        path=relative_path,
        category=category,
        media_type=media_type,
        schema_version=_SCHEMA_VERSION,
        sha256=_sha256(path),
        rows=rows,
        byte_size=path.stat().st_size,
        stage=stage,
    )


def _graph_rows(spec: RunSpec, *, weighted: bool) -> list[dict]:
    edge_count = 1005 if spec.sampled_graph else 8
    rows: list[dict] = []
    for index in range(1, edge_count + 1):
        community = 1 + ((index - 1) % 3)
        weight = round((index % 9 + 1) / 10, 3) if weighted else float(index % 9 + 1)
        rows.append(
            {
                "source": f"{spec.platform[:2]}-u{index:03d}",
                "target": f"{spec.platform[:2]}-u{index + 1:03d}",
                "community_number": community,
                "direction": "out",
                "weight": weight,
            }
        )
    return rows


def _topic_rows(spec: RunSpec, *, partial: bool) -> list[dict]:
    if spec.empty_semantics:
        return []
    theme_word = "Policy" if spec.platform == "twitter" else "Coordination"
    base = {
        "absolute_community": 1,
        "absolute_unigram_topic": f"{theme_word.lower()} discussion",
        "absolute_unigram_keywords": "['policy', 'community', 'discussion']",
        "weighted_community": 1,
        "weighted_unigram_topic": f"weighted {theme_word.lower()}",
        "weighted_unigram_keywords": "['policy', 'interaction']",
        "absolute_bigram_topic": f"{theme_word.lower()} debate",
        "absolute_bigram_keywords": "['public policy', 'community debate']",
        "weighted_bigram_topic": f"weighted {theme_word.lower()} debate",
        "weighted_bigram_keywords": "['weighted interaction']",
        "members": "['u1', 'u2', 'u3']",
    }
    if partial:
        return [
            {
                **base,
                "weighted_community": 2,
                "absolute_members": "['u1', 'u2', 'u3']",
                "weighted_members": "['u2', 'u3', 'u4']",
                "jaccard_score": 0.5,
                "common_members": "['u2', 'u3']",
                "uncommon_members": "['u1', 'u4']",
            }
        ]
    return [base, {**base, "absolute_community": 2, "weighted_community": 2}]


def _theme_rows(spec: RunSpec) -> list[dict]:
    if spec.empty_semantics:
        return []
    label = "Policy" if spec.platform == "twitter" else "Coordination"
    rows = []
    for community in (1, 2):
        rows.append(
            {
                "absolute_community": community,
                "absolute_unigram_topic": f"{label.lower()} discussion",
                "absolute_unigram_keywords": "['policy', 'community']",
                "weighted_community": community,
                "weighted_unigram_topic": f"weighted {label.lower()}",
                "weighted_unigram_keywords": "['policy', 'interaction']",
                "absolute_bigram_topic": f"{label.lower()} debate",
                "absolute_bigram_keywords": "['public policy']",
                "weighted_bigram_topic": f"weighted {label.lower()} debate",
                "weighted_bigram_keywords": "['weighted interaction']",
                "members": "['u1', 'u2', 'u3']",
                "all_keywords": "['policy', 'community', 'interaction']",
                "absolute_keywords": "['policy', 'community']",
                "weighted_keywords": "['policy', 'interaction']",
                "general_theme_gpt": json.dumps({label: ["policy", "community"]}),
                "general_theme_names": json.dumps([label]),
                "absolute_theme_gpt": json.dumps({label: ["policy"]}),
                "absolute_theme_names": json.dumps([label]),
                "weighted_theme_gpt": json.dumps({label: ["interaction"]}),
                "weighted_theme_names": json.dumps([label]),
            }
        )
    return rows


def _transition_rows(spec: RunSpec) -> list[dict]:
    previous = max(1, spec.month - 1)
    return [
        {
            "start_month": f"{previous:02d}",
            "end_month": spec.month_text,
            "start_month_community": 1,
            "end_month_community": 1,
            "jaccard_score": 0.75,
            "common_members": "['u1', 'u2', 'u3']",
            "uncommon_members": "['u4', 'u5']",
            "start_month_members": "['u1', 'u2', 'u3', 'u4']",
            "total_start_month_members": 4,
            "end_month_members": "['u1', 'u2', 'u3', 'u5']",
            "total_end_month_members": 4,
            "start_month_absolute_theme": "Policy",
            "end_month_absolute_theme": "Policy",
            "start_month_weighted_theme": "Policy",
            "end_month_weighted_theme": "Policy",
            "start_month_general_theme": "Policy",
            "end_month_general_theme": "Policy",
        },
        {
            "start_month": f"{previous:02d}",
            "end_month": spec.month_text,
            "start_month_community": 2,
            "end_month_community": 3,
            "jaccard_score": 0.4,
            "common_members": "['u7']",
            "uncommon_members": "['u6', 'u8', 'u9']",
            "start_month_members": "['u6', 'u7']",
            "total_start_month_members": 2,
            "end_month_members": "['u7', 'u8', 'u9']",
            "total_end_month_members": 3,
            "start_month_absolute_theme": "Coordination",
            "end_month_absolute_theme": "Coordination",
            "start_month_weighted_theme": "Coordination",
            "end_month_weighted_theme": "Coordination",
            "start_month_general_theme": "Coordination",
            "end_month_general_theme": "Coordination",
        },
    ]


def _build_run(artifact_root: Path, spec: RunSpec) -> Path:
    root = artifact_root / "runs" / spec.run_id
    root.mkdir(parents=True, exist_ok=True)
    (root / "inputs").mkdir(exist_ok=True)

    config = {
        "data_type": spec.platform,
        "content_type": spec.content_type,
        "month": spec.month_text,
        "year": str(spec.year),
        "graph_thresholds": {"min_total_post": 10, "min_shared_post": 5},
        "louvain": {"resolution": 1, "seed": 123},
        "lda": {
            "num_topics": 15,
            "random_state": 100,
            "iterations": 100,
            "chunksize": 20,
            "passes": 80,
            "alpha": "auto",
            "eta": "auto",
        },
        "theme": {
            "model": "fixture-theme-v1",
            "similarity_model": "fixture-similarity-v1",
        },
        "theme_provider": {"primary": "offline-fixture"},
    }
    (root / "resolved_config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=True), encoding="utf-8"
    )
    _write_json(
        root / "inputs/datasets.json",
        {"schema_version": "1.0", "datasets": []},
    )

    network_rows = [
        {
            "unique_id": f"{spec.run_id}-m{index}",
            "from_id": f"u{index}",
            "forwarder_id": f"u{index + 1}",
            "text": f"Fixture message {index}",
            "created_at": f"{spec.year}-{spec.month_text}-{min(index, 28):02d}",
        }
        for index in range(1, 11 + spec.month)
    ]
    _write_parquet(root / "data/network/network.parquet", network_rows, contract.NETWORK_DATA_COLUMNS)
    _write_parquet(
        root / "data/communities/absolute/communities.parquet",
        _graph_rows(spec, weighted=False),
        contract.COMMUNITY_GRAPH_COLUMNS,
    )
    _write_parquet(
        root / "data/communities/weighted/communities.parquet",
        _graph_rows(spec, weighted=True),
        contract.COMMUNITY_GRAPH_COLUMNS,
    )
    _write_parquet(
        root / "data/communities/matched/matched.parquet",
        [{
            "month": spec.month_text,
            "total_matched": 2,
            "total_absolute": 3,
            "total_weighted": 3,
        }],
        contract.MATCHED_COMMUNITY_SUMMARY_COLUMNS,
    )
    _write_parquet(
        root / "data/metrics/count_user_messages/counts.parquet",
        [{
            "month": spec.month_text,
            "user": repr({"absolute": 20 + spec.month, "weighted": 18 + spec.month}),
            "messages": repr({"absolute": 100 + spec.month * 10, "weighted": 90 + spec.month * 10}),
        }],
        contract.COUNT_USER_MESSAGES_COLUMNS,
    )
    _write_parquet(
        root / "data/metrics/user_centrality/centrality.parquet",
        [{
            "month": spec.month_text,
            "absolute": repr({"u1": 0.5, "u2": 0.25}),
            "weighted": repr({"u1": 0.4, "u2": 0.2}),
        }],
        contract.USER_CENTRALITY_COLUMNS,
    )
    _write_parquet(
        root / "data/topics/matched/topics.parquet",
        _topic_rows(spec, partial=False),
        contract.MATCHED_LDA_COLUMNS,
    )

    if spec.include_optional:
        _write_parquet(
            root / "data/topics/partial/topics.parquet",
            _topic_rows(spec, partial=True),
            contract.PARTIAL_MATCHED_LDA_COLUMNS,
        )

    _write_parquet(
        root / f"data/themes/monthly/{spec.month_text}.parquet",
        _theme_rows(spec),
        contract.THEMED_OUTPUT_COLUMNS,
    )
    _write_json(
        root / "data/themes/provider_run_summary.json",
        {
            "schema_version": "1",
            "configured_primary_provider": "offline-fixture",
            "configured_primary_model": "fixture-theme-v1",
            "fallback_used": False,
        },
    )

    if spec.include_optional:
        _write_parquet(
            root / "data/themes/community_transition.parquet",
            _transition_rows(spec),
            contract.COMMUNITY_TRANSITION_COLUMNS,
        )
        similarity_path = root / "reports/figures/theme_similarity/general.png"
        similarity_path.parent.mkdir(parents=True, exist_ok=True)
        similarity_path.write_bytes(_PNG_1X1)

    report_path = root / "reports/report.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        f"<html><body><h1>{spec.run_id}</h1><p>Deterministic dashboard fixture report.</p></body></html>",
        encoding="utf-8",
    )
    debug_path = root / "_intermediate/debug.json"
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    debug_path.write_text(json.dumps({"kind": "offline fixture intermediate data"}), encoding="utf-8")

    records = [
        _artifact_record(root, key="network_data", relative_path="data/network/network.parquet", category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
        _artifact_record(root, key="communities_absolute", relative_path="data/communities/absolute/communities.parquet", category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
        _artifact_record(root, key="communities_weighted", relative_path="data/communities/weighted/communities.parquet", category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
        _artifact_record(root, key="communities_matched", relative_path="data/communities/matched/matched.parquet", category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
        _artifact_record(root, key="count_user_messages", relative_path="data/metrics/count_user_messages/counts.parquet", category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
        _artifact_record(root, key="user_centrality", relative_path="data/metrics/user_centrality/centrality.parquet", category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
        _artifact_record(root, key="matched_communities_topics", relative_path="data/topics/matched/topics.parquet", category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="topic"),
        _artifact_record(root, key=f"themes_{spec.month_text}", relative_path=f"data/themes/monthly/{spec.month_text}.parquet", category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="theme"),
        _artifact_record(root, key="provider_run_summary", relative_path="data/themes/provider_run_summary.json", category=ArtifactCategory.DATA, media_type="application/json", stage="theme"),
        _artifact_record(root, key="report_html", relative_path="reports/report.html", category=ArtifactCategory.REPORT, media_type="text/html", stage="report"),
        _artifact_record(root, key="fixture_debug", relative_path="_intermediate/debug.json", category=ArtifactCategory.INTERMEDIATE, media_type="application/json", stage="fixture"),
    ]
    if spec.include_optional:
        records.extend(
            [
                _artifact_record(root, key="partial_matched_communities_topics", relative_path="data/topics/partial/topics.parquet", category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="topic"),
                _artifact_record(root, key="community_transitions", relative_path="data/themes/community_transition.parquet", category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="theme"),
                _artifact_record(root, key="visualization_theme_similarity_general.png", relative_path="reports/figures/theme_similarity/general.png", category=ArtifactCategory.REPORT, media_type="image/png", stage="theme"),
            ]
        )

    manifest = RunManifest(
        run_id=spec.run_id,
        status=RunStatus.COMPLETED,
        dataset={
            "platform": spec.platform,
            "content_type": spec.content_type,
            "date_start": f"{spec.year}-{spec.month_text}-01",
            "date_end": f"{spec.year}-{spec.month_text}-28",
            "source_hash": hashlib.sha256(spec.run_id.encode("utf-8")).hexdigest(),
        },
        code={"git_commit": "dashboard-fixture", "config_digest": "deterministic"},
        pipeline={
            "started_at": spec.started_at,
            "completed_at": spec.started_at,
            "prefect_flow_run_id": None,
            "mlflow_run_id": None,
        },
        artifacts=tuple(records),
    )
    _write_json(root / "manifest.json", manifest.to_dict())
    validate_run_manifest(root)

    if spec.tamper_after_validation:
        # Tamper with the artifact
        target = root / "data/communities/absolute/communities.parquet"
        with open(target, "ab") as f:
            f.write(b"tampered_row\n")
        try:
            validate_run_manifest(root)
        except ValueError:
            pass
        else:  # pragma: no cover - protects the fixture invariant
            raise AssertionError("tampered fixture unexpectedly passed manifest validation")

    return root


def _copy_selected_runs(source: Path, destination: Path, run_ids: Iterable[str]) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    (destination / "runs").mkdir(parents=True, exist_ok=True)
    for run_id in run_ids:
        shutil.copytree(source / "runs" / run_id, destination / "runs" / run_id)


def build_fixture(output_root: Path) -> dict[str, str]:
    output_root = output_root.expanduser().resolve()
    if output_root.exists():
        shutil.rmtree(output_root)
    default_root = output_root / "default"
    default_root.mkdir(parents=True, exist_ok=True)

    for spec in RUN_SPECS:
        _build_run(default_root, spec)

    no_runs = output_root / "variants/no-runs"
    (no_runs / "runs").mkdir(parents=True, exist_ok=True)
    _copy_selected_runs(
        default_root,
        output_root / "variants/optional-missing",
        ["twitter-2017-05-missing"],
    )
    _copy_selected_runs(
        default_root,
        output_root / "variants/empty-table",
        ["twitter-2017-06-empty"],
    )
    _copy_selected_runs(
        default_root,
        output_root / "variants/tampered",
        ["twitter-2017-07-tampered"],
    )
    _copy_selected_runs(
        default_root,
        output_root / "variants/sampled-graph",
        ["twitter-2017-04-reply"],
    )

    summary = {
        "default": str(default_root),
        "no_runs": str(no_runs),
        "optional_missing": str(output_root / "variants/optional-missing"),
        "empty_table": str(output_root / "variants/empty-table"),
        "tampered": str(output_root / "variants/tampered"),
        "sampled_graph": str(output_root / "variants/sampled-graph"),
    }
    _write_json(output_root / "fixture-index.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/tmp/community-dashboard-fixture"),
        help="Output directory. Existing contents are replaced.",
    )
    args = parser.parse_args()
    summary = build_fixture(args.out)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
