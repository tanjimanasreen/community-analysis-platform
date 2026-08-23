# Plan 081 — Canonical Theme Grouping Threshold Benchmark

## 1. Objective
Continue the read-only Stage-B canonicalization benchmark after Plan 080 showed that L2-normalized occurrence-weighted constituent centroids improve cohesion but still allow one overly broad canonical family.

Plan 081 holds that representation fixed and isolates the remaining grouping question: whether density connectivity or an explicit cosine-similarity threshold produces more defensible recurring canonical families.

## 2. Source Boundary
The 2026-08-21 21:57 project snapshot is the source of truth. Plans 074–080 remain intact.

The benchmark continues to consume only completed-run artifacts:
- `data/themes/clusters/evidence/*.parquet`;
- `data/themes/embeddings/clustering_general_themes.parquet`.

It must not rerun network analysis, community detection, translation, LDA, GPT theme generation, TEI inference, monthly HDBSCAN, or production Stage-B canonicalization.

## 3. Fixed Representation
All new Plan-081 candidates use the Plan-080 leading representation:

```text
monthly cluster
  -> every persisted constituent general-theme embedding
  -> occurrence-weighted arithmetic mean
  -> L2 normalization
```

Duplicate evidence observations retain their multiplicity. Exact recorded vectors remain mandatory; missing/conflicting vectors fail explicitly.

## 4. Grouping Candidates
The existing Plan-079/080 variants remain in the output for continuity.

Plan 081 adds two controlled candidate families:

1. HDBSCAN sensitivity with normalized constituent centroids and `min_cluster_size=2`:
   - `min_samples=1`;
   - `min_samples=2`;
   - the existing translated legacy-equivalent `min_samples=3` remains the Plan-080 reference.

2. Cosine-distance agglomerative clustering with normalized constituent centroids:
   - linkage: `average`, `complete`;
   - cosine similarity thresholds: `0.60`, `0.65`, `0.70`, `0.75`, `0.80`;
   - distance threshold is exactly `1 - similarity_threshold`;
   - singleton agglomerative groups are normalized to benchmark singleton noise so family/noise diagnostics remain comparable with production Stage B.

No threshold is promoted to production by this plan.

## 5. Diagnostics
The existing summary and membership CSVs remain the output surface.

Plan 081 adds explicit fields for:
- grouping method;
- linkage;
- similarity threshold;
- distance threshold;
- effective HDBSCAN `min_samples`;
- generic Stage-B cluster label while retaining the legacy HDBSCAN-label column for backward-compatible benchmark inspection.

Existing family count, singleton/noise count, largest-family concentration, within-family cosine cohesion, constituent evidence counts, and full memberships remain unchanged.

## 6. Protected Contracts
This plan does **not** change:
- production `CANONICALIZATION_CONTRACT_VERSION=2.1`;
- production Stage-B HDBSCAN algorithm, representative-label embeddings, parameters, or medoid naming;
- monthly HDBSCAN;
- clustering embedding inference/storage;
- LDA, translation, theme generation, IF/WIF, graph filters, Louvain, community matching, evolution, API, or frontend behavior.

A production canonicalization change remains a separate approval step after benchmark review.

## 7. Validation
- Existing Plan-079/080 benchmark tests remain green.
- Unit tests cover the fixed threshold grid, agglomerative singleton-to-noise normalization, threshold provenance, and independent HDBSCAN `min_samples` overrides.
- Complete-linkage candidates use cosine distance with the configured explicit threshold.
- No automated test calls TEI, an LLM provider, Azure, or AWS.
- `compileall`, focused canonical/clustering tests, and config validation are run where dependencies are available.

## 8. Progress Log
- 2026-08-21: Read the required repository contracts and active Plan 080 before editing.
- 2026-08-21: Kept the Plan-080 normalized constituent-centroid representation fixed for all new candidates.
- 2026-08-21: Added independent HDBSCAN `min_samples` benchmark variants and average/complete-linkage cosine threshold variants at 0.60–0.80.
- 2026-08-21: Added grouping/threshold provenance to benchmark outputs and regression coverage without changing production canonicalization.
