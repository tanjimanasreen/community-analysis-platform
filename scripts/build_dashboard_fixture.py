#!/usr/bin/env python3
"""Build deterministic, offline dashboard artifacts for frontend/API tests.

The generator writes canonical run manifests and small CSV/JSON/report artifacts.
It does not import pipeline, database, provider, embedding, or visualization code.
"""

from __future__ import annotations

import argparse
import ast
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
    longitudinal_months: tuple[int, ...] = ()

    @property
    def month_text(self) -> str:
        return f"{self.month:02d}"

    @property
    def months(self) -> tuple[int, ...]:
        return self.longitudinal_months or (self.month,)

    @property
    def is_longitudinal(self) -> bool:
        return len(self.months) > 1


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
        longitudinal_months=(1, 2, 3, 4),
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


def _graph_rows(
    spec: RunSpec, *, weighted: bool, month: int | None = None
) -> list[dict]:
    edge_count = 1005 if spec.sampled_graph else 8
    resolved_month = month or spec.month
    if spec.is_longitudinal:
        communities = (
            (resolved_month + 10, resolved_month + 110, resolved_month + 210)
            if weighted
            else (resolved_month, resolved_month + 100, resolved_month + 200)
        )
    else:
        communities = (1, 2, 3)
    rows: list[dict] = []
    for index in range(1, edge_count + 1):
        community = communities[(index - 1) % len(communities)]
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


def _topic_rows(spec: RunSpec, *, partial: bool, month: int | None = None) -> list[dict]:
    if spec.empty_semantics:
        return []
    resolved_month = month or spec.month
    theme_word = "Policy" if spec.platform == "twitter" else "Coordination"

    def topic_row(absolute: int, weighted: int) -> dict:
        return {
            "absolute_community": absolute,
            "absolute_unigram_topic": f"{theme_word.lower()} discussion",
            "absolute_unigram_keywords": "['policy', 'community', 'discussion']",
            "weighted_community": weighted,
            "weighted_unigram_topic": f"weighted {theme_word.lower()}",
            "weighted_unigram_keywords": "['policy', 'interaction']",
            "absolute_bigram_topic": f"{theme_word.lower()} debate",
            "absolute_bigram_keywords": "['public policy', 'community debate']",
            "weighted_bigram_topic": f"weighted {theme_word.lower()} debate",
            "weighted_bigram_keywords": "['weighted interaction']",
            "members": "['u1', 'u2', 'u3']",
        }

    if spec.is_longitudinal:
        first = topic_row(resolved_month, resolved_month + 10)
        second = topic_row(resolved_month + 100, resolved_month + 110)
        third = topic_row(resolved_month + 200, resolved_month + 210)
        if partial:
            return [
                {
                    **first,
                    "weighted_community": second["weighted_community"],
                    "absolute_members": "['u1', 'u2', 'u3']",
                    "weighted_members": "['u2', 'u3', 'u4']",
                    "jaccard_score": 0.5,
                    "common_members": "['u2', 'u3']",
                    "uncommon_members": "['u1', 'u4']",
                }
            ]
        return [first, second, third]

    base = topic_row(1, 1)
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


def _theme_row(
    *,
    absolute: int,
    weighted: int,
    labels: list[str],
    keywords: list[str],
) -> dict:
    provider_payload = {label: keywords for label in labels}
    return {
        "absolute_community": absolute,
        "absolute_unigram_topic": "policy discussion",
        "absolute_unigram_keywords": repr(keywords[:3]),
        "weighted_community": weighted,
        "weighted_unigram_topic": "weighted policy",
        "weighted_unigram_keywords": repr(keywords[:3]),
        "absolute_bigram_topic": "policy debate",
        "absolute_bigram_keywords": repr(keywords[1:3]),
        "weighted_bigram_topic": "weighted policy debate",
        "weighted_bigram_keywords": repr(keywords[1:3]),
        "members": "['u1', 'u2', 'u3']",
        "all_keywords": repr(keywords),
        "absolute_keywords": repr(keywords),
        "weighted_keywords": repr(keywords),
        "general_theme_gpt": json.dumps(provider_payload),
        "general_theme_names": json.dumps(labels),
        "absolute_theme_gpt": json.dumps(provider_payload),
        "absolute_theme_names": json.dumps(labels),
        "weighted_theme_gpt": json.dumps(provider_payload),
        "weighted_theme_names": json.dumps(labels),
    }


def _theme_rows(spec: RunSpec, *, month: int | None = None) -> list[dict]:
    if spec.empty_semantics:
        return []
    resolved_month = month or spec.month
    if spec.is_longitudinal:
        labels_by_month: dict[int, list[tuple[int, int, list[str], list[str]]]] = {
            1: [
                (1, 11, ["US Immigration Policy and Protests"], ["muslimban", "trump", "protest", "ban"]),
                (1, 11, ["US Immigration Policy and Protests"], ["nobannowall", "refugee"]),
                (101, 111, ["Travel and Immigration Restrictions", "Trump Administration Legal Challenges", "US Immigration Policy and Protests"], ["travel", "court", "order", "judge"]),
                (201, 211, ["Media and Finance"], ["radio", "stock", "money"]),
            ],
            2: [
                (2, 12, ["US Immigration Policy and Protests"], ["muslimban", "refugee", "protest", "law"]),
                (102, 112, ["Trump Administration Legal Challenges"], ["court", "judge", "appeal", "federal"]),
                (202, 212, ["US Immigration Policy"], ["travel", "ban", "immigration", "order"]),
            ],
            3: [
                (3, 13, [
                    "Travel Ban and Legal Challenges",
                    "Cross-platform civic discussion of public accountability and institutional response",
                ], [
                    "hawaii",
                    "judge",
                    "block",
                    "travelban",
                    "community_led_cross_platform_public_accountability_discussion",
                ]),
                (103, 113, ["US Immigration Policy Controversy"], ["muslimban", "court", "president", "policy"]),
                (203, 213, ["Media and Finance"], ["radio", "stock", "money"]),
            ],
            4: [
                (4, 14, ["Social and Political Activism"], ["activism", "protest", "petition", "rights"]),
                (104, 114, ["US Immigration Policy"], ["trump", "travelban", "refugee", "policy"]),
                (204, 214, ["Nationalism and Immigration Policies", "Refugee and Migration Issues"], ["americafirst", "border", "refugee", "solidarity"]),
            ],
        }
        return [
            _theme_row(
                absolute=absolute,
                weighted=weighted,
                labels=labels,
                keywords=keywords,
            )
            for absolute, weighted, labels, keywords in labels_by_month[resolved_month]
        ]

    label = "Policy" if spec.platform == "twitter" else "Coordination"
    return [
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
        for community in (1, 2)
    ]



def _fixture_canonical_theme(label: str) -> tuple[str, str]:
    normalized = label.casefold()
    if any(token in normalized for token in ("immigration", "travel ban", "refugee", "nationalism", "trump administration legal")):
        return "ct_fixture_immigration", "US Immigration Policy"
    if "media and finance" in normalized:
        return "ct_fixture_media_finance", "Media and Finance"
    if "activism" in normalized or "protest" in normalized:
        return "ct_fixture_activism", "Social and Political Activism"
    slug = hashlib.sha256(label.encode("utf-8")).hexdigest()[:12]
    return f"ct_fixture_{slug}", label


def _cluster_fixture_rows(spec: RunSpec, *, month: int) -> tuple[list[dict], list[dict]]:
    period = f"{spec.year:04d}-{month:02d}"
    source_rows = _theme_rows(spec, month=month)
    grouped: dict[str, dict] = {}
    evidence: list[dict] = []
    themed_pairs: set[tuple[str, str]] = set()
    for source_index, row in enumerate(source_rows):
        absolute = str(row.get("absolute_community", ""))
        weighted = str(row.get("weighted_community", ""))
        pair = (absolute, weighted)
        labels = json.loads(row.get("general_theme_names") or "[]")
        keywords = list(ast.literal_eval(row.get("all_keywords") or "[]"))
        if not labels:
            continue
        themed_pairs.add(pair)
        for label in labels:
            canonical_id, canonical_label = _fixture_canonical_theme(str(label))
            monthly_cluster_id = f"mc_fixture_{month:02d}_{hashlib.sha256(str(label).encode('utf-8')).hexdigest()[:10]}"
            item = grouped.setdefault(
                canonical_id,
                {
                    "label": canonical_label,
                    "cluster_ids": set(),
                    "representatives": set(),
                    "source_labels": set(),
                    "pairs": {},
                    "keyword_pairs": {},
                    "observations": 0,
                },
            )
            item["cluster_ids"].add(monthly_cluster_id)
            item["representatives"].add(str(label))
            item["source_labels"].add(str(label))
            item["observations"] += 1
            pair_key = f"if:{absolute}|wif:{weighted}"
            pair_item = item["pairs"].setdefault(
                pair_key,
                {
                    "absolute_community": absolute,
                    "weighted_community": weighted,
                    "source_labels": set(),
                    "keywords": [],
                },
            )
            pair_item["source_labels"].add(str(label))
            for keyword in keywords:
                if keyword not in pair_item["keywords"]:
                    pair_item["keywords"].append(keyword)
                item["keyword_pairs"].setdefault(keyword, set()).add(pair_key)
            evidence.append(
                {
                    "period": period,
                    "absolute_community": absolute,
                    "weighted_community": weighted,
                    "pair_key": pair_key,
                    "source_general_theme_label": str(label),
                    "general_keywords": json.dumps(keywords),
                    "source_index": source_index,
                    "hdbscan_label": 0,
                    "membership_probability": 0.95,
                    "is_monthly_noise": False,
                    "monthly_cluster_id": monthly_cluster_id,
                    "monthly_representative_theme": str(label),
                    "canonical_theme_id": canonical_id,
                    "canonical_theme_label": canonical_label,
                    "embedding_provider": "fixture",
                    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                    "embedding_normalized": False,
                    "hdbscan_implementation": "fixture",
                    "hdbscan_version": "fixture",
                    "clustering_min_cluster_size": 2,
                    "canonicalization_min_cluster_size": 2,
                    "clustering_metric": "euclidean",
                    "source_artifact_sha256": "fixture",
                    "monthly_cluster_contract_version": "2.1",
                    "canonicalization_contract_version": "2.1",
                }
            )

    result: list[dict] = []
    denominator = len(themed_pairs)
    for canonical_id, item in grouped.items():
        pair_values = []
        for pair_item in item["pairs"].values():
            pair_values.append(
                {
                    "absolute_community": pair_item["absolute_community"],
                    "weighted_community": pair_item["weighted_community"],
                    "source_labels": sorted(pair_item["source_labels"]),
                    "keywords": pair_item["keywords"],
                }
            )
        prominent = sorted(
            item["keyword_pairs"],
            key=lambda keyword: (-len(item["keyword_pairs"][keyword]), keyword.casefold()),
        )[:20]
        result.append(
            {
                "period": period,
                "canonical_theme_id": canonical_id,
                "canonical_theme_label": item["label"],
                "monthly_cluster_ids": json.dumps(sorted(item["cluster_ids"])),
                "monthly_representative_themes": json.dumps(sorted(item["representatives"])),
                "source_general_theme_labels": json.dumps(sorted(item["source_labels"])),
                "community_count": len(item["pairs"]),
                "total_themed_community_pairs": denominator,
                "percentage": round(100.0 * len(item["pairs"]) / denominator, 6) if denominator else 0.0,
                "prominent_keywords": json.dumps(prominent),
                "community_pairs": json.dumps(pair_values),
                "mean_membership_probability": 0.95,
                "source_observation_count": len(evidence),
                "cluster_observation_count": item["observations"],
                "monthly_cluster_count": len(item["cluster_ids"]),
                "excluded_records_missing_general_theme": 0,
                "excluded_records_ambiguous_general_theme_serialization": 0,
                "monthly_noise_observation_count": 0,
                "embedding_provider": "fixture",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_normalized": False,
                "hdbscan_implementation": "fixture",
                "hdbscan_version": "fixture",
                "clustering_min_cluster_size": 2,
                "canonicalization_min_cluster_size": 2,
                "clustering_metric": "euclidean",
                "monthly_cluster_contract_version": "2.1",
                "canonicalization_contract_version": "2.1",
                "source_artifact_sha256": "fixture",
            }
        )
    result.sort(key=lambda row: (-row["community_count"], row["canonical_theme_label"].casefold()))
    return result, evidence

def _transition_rows(spec: RunSpec) -> list[dict]:
    if spec.is_longitudinal:
        first_labels = {
            1: "US Immigration Policy and Protests",
            2: "US Immigration Policy and Protests",
            3: "Travel Ban and Legal Challenges",
            4: "Social and Political Activism",
        }
        second_labels = {
            1: "Travel and Immigration Restrictions",
            2: "Trump Administration Legal Challenges",
            3: "US Immigration Policy Controversy",
            4: "US Immigration Policy",
        }
        rows: list[dict] = []
        for start_month, end_month in zip(spec.months, spec.months[1:]):
            for start_community, end_community, labels, retained, score in (
                (start_month, end_month, first_labels, ["u1", "u2", "u3"], 0.75),
                (start_month + 100, end_month + 100, second_labels, ["u7", "u8"], 0.66),
            ):
                start_theme = labels[start_month]
                end_theme = labels[end_month]
                rows.append(
                    {
                        "start_month": f"{start_month:02d}",
                        "end_month": f"{end_month:02d}",
                        "start_month_community": start_community,
                        "end_month_community": end_community,
                        "jaccard_score": score,
                        "common_members": repr(retained),
                        "uncommon_members": "['u4', 'u5']",
                        "start_month_members": repr([*retained, "u4"]),
                        "total_start_month_members": len(retained) + 1,
                        "end_month_members": repr([*retained, "u5"]),
                        "total_end_month_members": len(retained) + 1,
                        "start_month_absolute_theme": start_theme,
                        "end_month_absolute_theme": end_theme,
                        "start_month_weighted_theme": start_theme,
                        "end_month_weighted_theme": end_theme,
                        "start_month_general_theme": start_theme,
                        "end_month_general_theme": end_theme,
                    }
                )
        return rows

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



def _evolution_artifact_rows(spec: RunSpec) -> tuple[list[dict], list[dict], list[dict]]:
    if spec.is_longitudinal:
        first_labels = {
            1: "US Immigration Policy and Protests",
            2: "US Immigration Policy and Protests",
            3: "Travel Ban and Legal Challenges",
            4: "Social and Political Activism",
        }
        second_labels = {
            1: "Travel and Immigration Restrictions",
            2: "Trump Administration Legal Challenges",
            3: "US Immigration Policy Controversy",
            4: "US Immigration Policy",
        }
        path_specs = [
            (
                "fixture-path-1",
                1,
                {
                    1: ["u1", "u2", "u3", "u4"],
                    2: ["u1", "u2", "u3", "u5"],
                    3: ["u1", "u2", "u3", "u4", "u5"],
                    4: ["u1", "u2", "u3", "u4"],
                },
                first_labels,
                0,
                0.75,
            ),
            (
                "fixture-path-2",
                2,
                {month: ["u7", "u8", f"u{8 + month}"] for month in spec.months},
                second_labels,
                100,
                0.66,
            ),
        ]
    else:
        previous = max(1, spec.month - 1)
        path_specs = [
            (
                "fixture-path-1",
                1,
                {previous: ["u1", "u2", "u3", "u4"], spec.month: ["u1", "u2", "u3", "u5"]},
                {previous: "Policy", spec.month: "Policy"},
                0,
                0.75,
            )
        ]

    path_rows: list[dict] = []
    mobility_rows: list[dict] = []
    similarity_rows: list[dict] = []
    for path_id, display_order, membership_by_month, labels, offset, jaccard in path_specs:
        seen: set[str] = set()
        previous_members: set[str] | None = None
        months = sorted(membership_by_month)
        for step_index, month in enumerate(months):
            members = list(membership_by_month[month])
            current = set(members)
            if previous_members is None:
                existing, new, lost, reappearing = current, set(), set(), set()
                previous_month = None
                previous_key = None
                score = None
                retained_count = None
                size_delta = None
            else:
                existing = current & previous_members
                new = current - previous_members
                lost = previous_members - current
                reappearing = (current & seen) - previous_members
                previous_month = f"{months[step_index - 1]:02d}"
                previous_key = str(months[step_index - 1] + offset)
                score = jaccard
                retained_count = len(existing)
                size_delta = len(current) - len(previous_members)
            community_key = str(month + offset)
            theme = labels[month]
            path_rows.append({
                "path_id": path_id, "display_order": display_order, "step_index": step_index,
                "month": f"{month:02d}", "community_key": community_key, "community_id": community_key,
                "member_count": len(members), "members": json.dumps(members),
                "previous_month": previous_month, "previous_community_key": previous_key,
                "previous_community_id": previous_key, "jaccard_from_previous": score,
                "retained_count": retained_count, "absolute_theme": theme,
                "weighted_theme": theme, "general_theme": theme,
            })
            mobility_rows.append({
                "path_id": path_id, "display_order": display_order, "step_index": step_index,
                "month": f"{month:02d}", "community_key": community_key, "community_id": community_key,
                "member_count": len(members), "size_delta": size_delta,
                "existing_count": len(existing), "new_count": len(new), "lost_count": len(lost),
                "reappearing_count": len(reappearing), "members": json.dumps(sorted(current)),
                "existing_members": json.dumps(sorted(existing)), "new_members": json.dumps(sorted(new)),
                "lost_members": json.dumps(sorted(lost)), "reappearing_members": json.dumps(sorted(reappearing)),
            })
            seen.update(current)
            previous_members = current

        for theme_type in ("general", "absolute", "weighted"):
            for left_index, left_month in enumerate(months):
                for right_index in range(left_index, len(months)):
                    right_month = months[right_index]
                    distance = right_index - left_index
                    similarity = 1.0 if distance == 0 else max(0.45, round(0.86 - 0.08 * distance - 0.03 * (display_order - 1), 2))
                    similarity_rows.append({
                        "path_id": path_id, "display_order": display_order, "theme_type": theme_type,
                        "left_step_index": left_index, "right_step_index": right_index,
                        "left_month": f"{left_month:02d}", "right_month": f"{right_month:02d}",
                        "left_community_key": str(left_month + offset),
                        "right_community_key": str(right_month + offset),
                        "left_theme": labels[left_month], "right_theme": labels[right_month],
                        "cosine_similarity": similarity, "embedding_provider": "mock",
                        "embedding_model": "sentence-transformers/paraphrase-MiniLM-L6-v2",
                        "embedding_model_revision": "c9a2bfebc254878aee8c3aca9e6844d5bbb102d1",
                    })
    return path_rows, mobility_rows, similarity_rows

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
            "implementation": "ldamulticore",
            "num_topics": 15,
            "random_state": 100,
            "iterations": 100,
            "chunksize": 20,
            "passes": 80,
            "alpha": "symmetric",
            "eta": "auto",
        },
        "theme": {
            "model": "fixture-theme-v1",
            "transition_threshold": 0.5,
            "reply_transition_threshold": 0.0,
            "evolution_similarity_enabled": True,
            "similarity_provider": "mock",
            "similarity_model": "paraphrase-MiniLM-L6-v2",
            "similarity_model_revision": "c9a2bfebc254878aee8c3aca9e6844d5bbb102d1",
        },
        "theme_provider": {"primary": "offline-fixture"},
    }
    if spec.is_longitudinal:
        config["longitudinal_datasets"] = [
            {"month": f"{month:02d}", "year": str(spec.year)}
            for month in spec.months
        ]
    (root / "resolved_config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=True), encoding="utf-8"
    )
    _write_json(
        root / "inputs/datasets.json",
        {"schema_version": "1.0", "datasets": []},
    )

    records: list[ArtifactRecord] = []
    for month in spec.months:
        month_text = f"{month:02d}"
        period = f"{spec.year}-{month_text}"
        suffix = f"_{month_text}" if spec.is_longitudinal else ""

        network_path = (
            f"data/network/{month_text}.parquet"
            if spec.is_longitudinal
            else "data/network/network.parquet"
        )
        absolute_path = (
            f"data/communities/absolute/{month_text}.parquet"
            if spec.is_longitudinal
            else "data/communities/absolute/communities.parquet"
        )
        weighted_path = (
            f"data/communities/weighted/{month_text}.parquet"
            if spec.is_longitudinal
            else "data/communities/weighted/communities.parquet"
        )
        matched_path = (
            f"data/communities/matched/{month_text}.parquet"
            if spec.is_longitudinal
            else "data/communities/matched/matched.parquet"
        )
        counts_path = (
            f"data/metrics/count_user_messages/{month_text}.parquet"
            if spec.is_longitudinal
            else "data/metrics/count_user_messages/counts.parquet"
        )
        centrality_path = (
            f"data/metrics/user_centrality/{month_text}.parquet"
            if spec.is_longitudinal
            else "data/metrics/user_centrality/centrality.parquet"
        )
        matched_topics_path = (
            f"data/topics/matched/{month_text}.parquet"
            if spec.is_longitudinal
            else "data/topics/matched/topics.parquet"
        )
        partial_topics_path = (
            f"data/topics/partial/{month_text}.parquet"
            if spec.is_longitudinal
            else "data/topics/partial/topics.parquet"
        )
        theme_path = (
            f"data/themes/monthly/{month_text}.parquet"
            if spec.is_longitudinal
            else f"data/themes/monthly/{month_text}.parquet"
        )
        cluster_path = f"data/themes/clusters/monthly/{spec.year:04d}-{month:02d}.parquet"
        cluster_evidence_path = f"data/themes/clusters/evidence/{spec.year:04d}-{month:02d}.parquet"

        network_rows = [
            {
                "unique_id": (
                    f"{spec.run_id}-{month_text}-m{index}"
                    if spec.is_longitudinal
                    else f"{spec.run_id}-m{index}"
                ),
                "from_id": f"u{index}",
                "forwarder_id": f"u{index + 1}",
                "text": (
                    f"Fixture message {index} for {period}"
                    if spec.is_longitudinal
                    else f"Fixture message {index}"
                ),
                "created_at": f"{spec.year}-{month_text}-{min(index, 28):02d}",
            }
            for index in range(1, 11 + month)
        ]
        _write_parquet(root / network_path, network_rows, contract.NETWORK_DATA_COLUMNS)
        _write_parquet(
            root / absolute_path,
            _graph_rows(spec, weighted=False, month=month),
            contract.COMMUNITY_GRAPH_COLUMNS,
        )
        _write_parquet(
            root / weighted_path,
            _graph_rows(spec, weighted=True, month=month),
            contract.COMMUNITY_GRAPH_COLUMNS,
        )
        _write_parquet(
            root / matched_path,
            [{
                "month": month_text,
                "total_matched": 3 if spec.is_longitudinal else 2,
                "total_absolute": 3,
                "total_weighted": 3,
            }],
            contract.MATCHED_COMMUNITY_SUMMARY_COLUMNS,
        )
        _write_parquet(
            root / counts_path,
            [{
                "month": month_text,
                "user": repr({"absolute": 20 + month, "weighted": 18 + month}),
                "messages": repr({"absolute": 100 + month * 10, "weighted": 90 + month * 10}),
            }],
            contract.COUNT_USER_MESSAGES_COLUMNS,
        )
        _write_parquet(
            root / centrality_path,
            [{
                "month": month_text,
                "absolute": repr({"u1": 0.5, "u2": 0.25}),
                "weighted": repr({"u1": 0.4, "u2": 0.2}),
            }],
            contract.USER_CENTRALITY_COLUMNS,
        )
        _write_parquet(
            root / matched_topics_path,
            _topic_rows(spec, partial=False, month=month),
            contract.MATCHED_LDA_COLUMNS,
        )
        if spec.include_optional:
            _write_parquet(
                root / partial_topics_path,
                _topic_rows(spec, partial=True, month=month),
                contract.PARTIAL_MATCHED_LDA_COLUMNS,
            )
        _write_parquet(
            root / theme_path,
            _theme_rows(spec, month=month),
            contract.THEMED_OUTPUT_COLUMNS,
        )
        cluster_rows, cluster_evidence_rows = _cluster_fixture_rows(spec, month=month)
        _write_parquet(
            root / cluster_path,
            cluster_rows,
            contract.THEME_CLUSTER_SUMMARY_COLUMNS,
        )
        _write_parquet(
            root / cluster_evidence_path,
            cluster_evidence_rows,
            contract.THEME_CLUSTER_OBSERVATION_COLUMNS,
        )

        theme_key = f"themes_{month_text}"
        records.extend(
            [
                _artifact_record(root, key=f"network_data{suffix}", relative_path=network_path, category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
                _artifact_record(root, key=f"communities_absolute{suffix}", relative_path=absolute_path, category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
                _artifact_record(root, key=f"communities_weighted{suffix}", relative_path=weighted_path, category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
                _artifact_record(root, key=f"communities_matched{suffix}", relative_path=matched_path, category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
                _artifact_record(root, key=f"count_user_messages{suffix}", relative_path=counts_path, category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
                _artifact_record(root, key=f"user_centrality{suffix}", relative_path=centrality_path, category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="network_community"),
                _artifact_record(root, key=f"matched_communities_topics{suffix}", relative_path=matched_topics_path, category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="topic"),
                _artifact_record(root, key=theme_key, relative_path=theme_path, category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="theme"),
                _artifact_record(root, key=f"theme_clusters_{spec.year:04d}-{month:02d}", relative_path=cluster_path, category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="theme"),
                _artifact_record(root, key=f"theme_cluster_observations_{spec.year:04d}-{month:02d}", relative_path=cluster_evidence_path, category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="theme"),
            ]
        )
        if spec.include_optional and spec.is_longitudinal:
            records.append(
                _artifact_record(
                    root,
                    key=f"partial_matched_communities_topics{suffix}",
                    relative_path=partial_topics_path,
                    category=ArtifactCategory.DATA,
                    media_type="application/vnd.apache.parquet",
                    stage="topic",
                )
            )

    family_rows: dict[str, dict] = {}
    for month in spec.months:
        cluster_rows, _ = _cluster_fixture_rows(spec, month=month)
        for row in cluster_rows:
            canonical_id = row["canonical_theme_id"]
            item = family_rows.setdefault(canonical_id, {
                "canonical_theme_id": canonical_id,
                "canonical_theme_label": row["canonical_theme_label"],
                "monthly_cluster_ids": set(),
                "monthly_representatives": set(),
                "periods": set(),
            })
            item["monthly_cluster_ids"].update(json.loads(row["monthly_cluster_ids"]))
            item["monthly_representatives"].update(json.loads(row["monthly_representative_themes"]))
            item["periods"].add(row["period"])
    family_output = [
        {
            "canonical_theme_id": item["canonical_theme_id"],
            "canonical_theme_label": item["canonical_theme_label"],
            "monthly_cluster_ids": json.dumps(sorted(item["monthly_cluster_ids"])),
            "monthly_representatives": json.dumps(sorted(item["monthly_representatives"])),
            "periods": json.dumps(sorted(item["periods"])),
            "months_present": len(item["periods"]),
            "stage_b_hdbscan_label": 0,
            "singleton_canonical_theme": len(item["periods"]) == 1,
            "embedding_provider": "fixture",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "embedding_normalized": False,
            "hdbscan_implementation": "fixture",
            "hdbscan_version": "fixture",
            "clustering_min_cluster_size": 2,
            "canonicalization_min_cluster_size": 2,
            "clustering_metric": "euclidean",
            "source_artifact_sha256s": json.dumps(["fixture"]),
            "monthly_cluster_contract_version": "1.0",
            "canonicalization_contract_version": "1.0",
        }
        for item in family_rows.values()
    ]
    _write_parquet(
        root / "data/themes/clusters/canonical_families.parquet",
        family_output,
        contract.THEME_CANONICAL_FAMILY_COLUMNS,
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
        path_rows, mobility_rows, path_similarity_rows = _evolution_artifact_rows(spec)
        _write_parquet(
            root / "data/evolution/community_paths.parquet",
            path_rows,
            contract.COMMUNITY_PATH_COLUMNS,
        )
        _write_parquet(
            root / "data/evolution/community_path_membership.parquet",
            mobility_rows,
            contract.COMMUNITY_PATH_MEMBERSHIP_COLUMNS,
        )
        _write_parquet(
            root / "data/evolution/community_path_theme_similarity.parquet",
            path_similarity_rows,
            contract.COMMUNITY_PATH_THEME_SIMILARITY_COLUMNS,
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
    debug_path.write_text(
        json.dumps({"kind": "offline fixture intermediate data"}),
        encoding="utf-8",
    )

    records.extend(
        [
            _artifact_record(root, key="theme_canonical_families", relative_path="data/themes/clusters/canonical_families.parquet", category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="theme"),
            _artifact_record(root, key="provider_run_summary", relative_path="data/themes/provider_run_summary.json", category=ArtifactCategory.DATA, media_type="application/json", stage="theme"),
            _artifact_record(root, key="report_html", relative_path="reports/report.html", category=ArtifactCategory.REPORT, media_type="text/html", stage="report"),
            _artifact_record(root, key="fixture_debug", relative_path="_intermediate/debug.json", category=ArtifactCategory.INTERMEDIATE, media_type="application/json", stage="fixture"),
        ]
    )
    if spec.include_optional:
        if not spec.is_longitudinal:
            records.append(
                _artifact_record(
                    root,
                    key="partial_matched_communities_topics",
                    relative_path="data/topics/partial/topics.parquet",
                    category=ArtifactCategory.DATA,
                    media_type="application/vnd.apache.parquet",
                    stage="topic",
                )
            )
        records.extend(
            [
                _artifact_record(
                    root,
                    key="community_transitions",
                    relative_path="data/themes/community_transition.parquet",
                    category=ArtifactCategory.DATA,
                    media_type="application/vnd.apache.parquet",
                    stage="theme",
                ),
                _artifact_record(
                    root, key="community_paths", relative_path="data/evolution/community_paths.parquet",
                    category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="theme",
                ),
                _artifact_record(
                    root, key="community_path_membership", relative_path="data/evolution/community_path_membership.parquet",
                    category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="theme",
                ),
                _artifact_record(
                    root, key="community_path_theme_similarity", relative_path="data/evolution/community_path_theme_similarity.parquet",
                    category=ArtifactCategory.DATA, media_type="application/vnd.apache.parquet", stage="theme",
                ),
                _artifact_record(
                    root,
                    key="visualization_theme_similarity_general.png",
                    relative_path="reports/figures/theme_similarity/general.png",
                    category=ArtifactCategory.REPORT,
                    media_type="image/png",
                    stage="theme",
                ),
            ]
        )

    manifest = RunManifest(
        run_id=spec.run_id,
        status=RunStatus.COMPLETED,
        dataset={
            "platform": spec.platform,
            "content_type": spec.content_type,
            "date_start": f"{spec.year}-{spec.months[0]:02d}-01",
            "date_end": f"{spec.year}-{spec.months[-1]:02d}-28",
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
