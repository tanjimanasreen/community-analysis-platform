# Plan 079 — Canonical Theme Clustering Benchmark

## 1. Objective
Isolate and benchmark Stage-B cross-month canonical-theme clustering against persisted monthly-cluster evidence and recorded clustering embeddings before changing any production canonicalization behavior.

## 2. Source Boundary
The 2026-08-21 14:26 project snapshot is the source of truth. Plans 074–078 remain intact. The benchmark consumes completed run artifacts only and must not rerun network analysis, community detection, translation, LDA, theme generation, TEI inference, or monthly HDBSCAN.

## 3. Benchmark Contract
- Reconstruct one row per persisted non-noise monthly cluster from `data/themes/clusters/evidence/*.parquet`.
- Reuse the exact recorded `all-MiniLM-L6-v2` clustering vectors from `data/themes/embeddings/clustering_general_themes.parquet`.
- Include the current Stage-B contract as the baseline: raw embeddings, Euclidean distance, `min_cluster_size=2`, translated `min_samples=3`, EOM, and `allow_single_cluster=false`.
- Compare a deliberately small set of candidates: L2-normalized Euclidean at min cluster sizes 2/3/4 and brute-force cosine at min cluster sizes 2/3.
- Preserve current Stage-B singleton-noise reporting semantics in benchmark membership output.
- Report family count, clustered/noise monthly clusters, largest-family size/share, and within-family cosine cohesion, plus full family membership for manual semantic review.
- Benchmark outputs are CSV diagnostics under a caller-selected directory and are not run-manifest analytical artifacts.

## 4. Protected Contracts
This plan does **not** change production Stage-B parameters, Stage-B medoid naming, monthly HDBSCAN, embedding inference, LDA, translation, IF/WIF metrics, graph thresholds, Louvain, theme generation, community evolution, API/frontend behavior, or artifact schemas.

A production canonicalization change remains a separate approval step after the benchmark result is reviewed.

## 5. Validation
- Unit tests verify Stage-A representative reconstruction, exact persisted-vector alignment, baseline fidelity to the current `_fit_hdbscan` partition, normalized/cosine candidate execution, and non-mutation of benchmark input vectors.
- No automated test calls TEI or an LLM provider.
- `compileall` and focused theme-clustering tests must pass where dependencies are available.

## 6. Progress Log
- 2026-08-21: Read required repository contracts and current Plans 074–078 before editing.
- 2026-08-21: Inspected the current Stage-B implementation and confirmed production uses raw, unnormalized embeddings with Euclidean HDBSCAN while semantic-medoid selection uses cosine similarity.
- 2026-08-21: Added read-only Stage-B benchmark tooling and CLI/Make entry points without changing production canonicalization behavior.
- 2026-08-21: Added regression coverage for persisted representative/vector alignment and baseline/candidate clustering behavior.
