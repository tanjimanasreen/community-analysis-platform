# Plan 080 — Canonical Theme Centroid Representation Benchmark

## 1. Objective
Extend the read-only Stage-B benchmark to test whether a monthly cluster is represented more faithfully by the mean of all constituent general-theme embeddings than by one monthly representative-theme embedding.

Plan 079 ruled out a simple geometry/`min_cluster_size` correction: normalized-Euclidean/cosine variants either over-merged the 33 monthly clusters or classified all points as noise. Plan 080 therefore changes only the benchmark representation while holding the existing Stage-B density contract fixed for the new comparison candidates.

## 2. Source Boundary
The 2026-08-21 14:53 project snapshot is the source of truth. Plans 074–079 remain intact.

The benchmark consumes only completed run artifacts:
- `data/themes/clusters/evidence/*.parquet`;
- `data/themes/embeddings/clustering_general_themes.parquet`.

It must not rerun network analysis, community detection, translation, LDA, GPT theme generation, TEI inference, monthly HDBSCAN, or production Stage-B canonicalization.

## 3. Representation Contract
The benchmark retains every Plan-079 representative-label variant and adds two isolated representation candidates using the existing Euclidean Stage-B density settings (`min_cluster_size=2`, translated `min_samples=3`, EOM, `allow_single_cluster=false`):

1. `constituent_mean_raw_euclidean_mcs2`
   - one vector per non-noise monthly cluster;
   - arithmetic mean of all persisted constituent `source_general_theme_label` embeddings;
   - each evidence observation contributes once, including duplicate labels, preserving Stage-A occurrence density;
   - no normalization after the mean.

2. `constituent_mean_normalized_euclidean_mcs2`
   - same occurrence-weighted mean vector;
   - L2-normalize the monthly-cluster mean before Stage-B HDBSCAN.

Recorded embeddings are aligned by exact source label. Missing or conflicting recorded vectors fail the benchmark explicitly rather than triggering inference or silently dropping evidence.

## 4. Diagnostics
The existing summary and membership CSVs remain the output surface. They now identify the representation used by each variant. Membership output also records:
- constituent observation count;
- constituent unique-label count.

The benchmark continues to report family count, noise, largest-family concentration, and within-family cosine cohesion for manual semantic review.

## 5. Protected Contracts
This plan does **not** change:
- production `CANONICALIZATION_CONTRACT_VERSION=2.1`;
- production Stage-B representative-label embeddings or HDBSCAN parameters;
- canonical medoid naming;
- monthly HDBSCAN;
- clustering embedding inference/storage;
- LDA or translation;
- IF/WIF metrics, graph filters, Louvain, community matching, evolution, API, or frontend behavior.

A production Stage-B representation change remains a separate approval step after the new benchmark results are reviewed.

## 6. Validation
- Existing Plan-079 baseline tests remain green.
- Unit tests verify occurrence-weighted centroid construction, exact-vector requirements, representation-specific benchmark routing, diagnostics, and non-mutation of production behavior.
- No automated test calls TEI, an LLM provider, Azure, or AWS.
- `compileall`, focused clustering tests, and config validation are run where dependencies are available.

## 7. Progress Log
- 2026-08-21: Read the required repository contracts and active Plan 079 before editing.
- 2026-08-21: Confirmed persisted cluster evidence contains exact constituent `source_general_theme_label` rows and monthly-cluster IDs, while the recorded clustering embedding artifact is exact-text addressable.
- 2026-08-21: Added occurrence-weighted constituent centroid reconstruction and raw/normalized centroid Stage-B benchmark variants without modifying production canonicalization.
- 2026-08-21: Added regression tests and documentation for the representation benchmark contract.
