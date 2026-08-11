#!/usr/bin/env python3
import json
import hashlib
import shutil
import yaml
from pathlib import Path

# Paths
source_dir = Path("twitter")
dest_root = Path("artifacts/runs/real_twitter_04")

if dest_root.exists():
    shutil.rmtree(dest_root)
dest_root.mkdir(parents=True, exist_ok=True)

(dest_root / "inputs").mkdir(exist_ok=True)
(dest_root / "data").mkdir(exist_ok=True)
(dest_root / "reports").mkdir(exist_ok=True)

# Helper functions
def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _copy_and_record(src: Path, dest_rel: str, key: str, category: str, media_type: str, stage: str) -> dict:
    dest = dest_root / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dest)
        rows = None
        if src.suffix == ".csv":
            with src.open("r", encoding="utf-8") as f:
                rows = sum(1 for _ in f) - 1 # count lines minus header
                rows = max(0, rows)
        return {
            "key": key,
            "path": dest_rel,
            "category": category,
            "media_type": media_type,
            "schema_version": "1.0",
            "sha256": _sha256(dest),
            "byte_size": dest.stat().st_size,
            "rows": rows,
            "stage": stage
        }
    else:
        print(f"WARNING: Source {src} does not exist. Skipping {key}")
        return None

records = []

# Network
r = _copy_and_record(source_dir / "network_data/reply/042017.csv", "data/network/network.csv", "network_data", "data", "text/csv", "network_community")
if r: records.append(r)

# Communities
r = _copy_and_record(source_dir / "communities/graphs/absolute/reply/04.csv", "data/communities/absolute/communities.csv", "communities_absolute", "data", "text/csv", "network_community")
if r: records.append(r)
r = _copy_and_record(source_dir / "communities/graphs/weighted/reply/04.csv", "data/communities/weighted/communities.csv", "communities_weighted", "data", "text/csv", "network_community")
if r: records.append(r)
r = _copy_and_record(source_dir / "communities/matched/reply/04.csv", "data/communities/matched/matched.csv", "communities_matched", "data", "text/csv", "network_community")
if r: records.append(r)

# Metrics
r = _copy_and_record(source_dir / "count_user_messages/reply/04.csv", "data/metrics/count_user_messages/counts.csv", "count_user_messages", "data", "text/csv", "network_community")
if r: records.append(r)
r = _copy_and_record(source_dir / "user_centrality/reply/04.csv", "data/metrics/user_centrality/centrality.csv", "user_centrality", "data", "text/csv", "network_community")
if r: records.append(r)

# Topics
r = _copy_and_record(source_dir / "LDA/scores/reply/04.csv", "data/topics/matched/topics.csv", "matched_communities_topics", "data", "text/csv", "topic")
if r: records.append(r)

# Themes
r = _copy_and_record(source_dir / "theme_analysis/reply/04_2017_with_themes.csv", "data/themes/monthly/04.csv", "themes_04", "data", "text/csv", "theme")
if r: records.append(r)
r = _copy_and_record(source_dir / "theme_analysis/reply/community_transition.csv", "data/themes/community_transition.csv", "community_transitions", "data", "text/csv", "theme")
if r: records.append(r)

# Write stubs
with open(dest_root / "inputs/datasets.json", "w") as f:
    json.dump({"schema_version": "1.0", "datasets": []}, f)

with open(dest_root / "data/themes/provider_run_summary.json", "w") as f:
    json.dump({
        "schema_version": "1.0",
        "configured_primary_provider": "local",
        "configured_primary_model": "llama-3-8b",
        "fallback_used": False
    }, f)

records.append({
    "key": "provider_run_summary",
    "path": "data/themes/provider_run_summary.json",
    "category": "data",
    "media_type": "application/json",
    "schema_version": "1.0",
    "sha256": _sha256(dest_root / "data/themes/provider_run_summary.json"),
    "byte_size": (dest_root / "data/themes/provider_run_summary.json").stat().st_size,
    "rows": None,
    "stage": "theme"
})

config = {
    "data_type": "twitter",
    "content_type": "reply",
    "month": "04",
    "year": "2017",
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
        "model": "llama-3-8b",
        "similarity_model": "fixture-similarity-v1",
    },
    "theme_provider": {"primary": "local"},
}
(dest_root / "resolved_config.yaml").write_text(
    yaml.safe_dump(config, sort_keys=True), encoding="utf-8"
)

# Write the RunManifest
manifest = {
    "run_id": "real_twitter_04",
    "status": "completed",
    "dataset": {
        "platform": "twitter",
        "content_type": "reply",
        "date_start": "2017-04-01",
        "date_end": "2017-04-28",
        "source_hash": hashlib.sha256(b"real_twitter_04").hexdigest()
    },
    "code": {
        "git_commit": "unknown",
        "config_digest": "unknown"
    },
    "pipeline": {
        "started_at": "2026-07-19T00:00:00+00:00",
        "completed_at": "2026-07-19T00:00:00+00:00",
        "prefect_flow_run_id": None,
        "mlflow_run_id": None
    },
    "artifacts": records,
    "schema_version": "1.0"
}

with open(dest_root / "manifest.json", "w") as f:
    json.dump(manifest, f, indent=2, sort_keys=True)

print("Packaged successfully to", dest_root)
