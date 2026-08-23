# Plan 083 — Stage-B Representation Robustness Benchmark

## 1. Objective
Benchmark whether Stage-B monthly-cluster representation, rather than the fixed grouping algorithm, is responsible for the remaining cross-month over-merging observed after Plan 082.

The production Telegram validation showed that complete-linkage cosine clustering at similarity `0.65` can still produce a semantically broad canonical family when internally heterogeneous monthly clusters are reduced to arithmetic-mean constituent centroids. Plan 083 therefore isolates representation as the experimental variable.

This plan is benchmark-only. Production canonicalization remains contract `3.0` throughout.

## 2. Source boundary
The 2026-08-22 21:25 project snapshot is the source of truth. Plans 074–082 remain intact.

The benchmark consumes only completed-run artifacts from either supported root:

- canonical published `data/themes/`: `clusters/evidence/*.parquet` plus
  `embeddings/clustering_general_themes.parquet`;
- run-local `theme_clusters/`: `evidence/*.parquet` plus
  `embeddings/clustering_general_themes.parquet`.

The older nested embedding fallback under `clusters/embeddings/` remains accepted
for backward compatibility.

It must not rerun network/community analysis, translation, LDA, GPT theme generation, TEI inference, monthly HDBSCAN, or production Stage-B canonicalization.

## 3. Frozen production contract
Plan 083 does not change:

- `CANONICALIZATION_CONTRACT_VERSION=3.0`;
- production occurrence-weighted constituent-mean representation;
- cosine complete-linkage grouping;
- production similarity threshold `0.65` / distance threshold `0.35`;
- monthly HDBSCAN contract or defaults;
- any IF/WIF, graph, Louvain, LDA, translation, theme-generation, community-matching, evolution, API, frontend, or cache contract.

A production representation change requires a later approved plan.

## 4. Fixed grouping contract for Plan-083 candidates
All new Plan-083 candidates use:

- `sklearn.cluster.AgglomerativeClustering`;
- `metric="cosine"`;
- `linkage="complete"`;
- `n_clusters=None`;
- `compute_full_tree=True`;
- similarity thresholds `0.60`, `0.65`, `0.70`, `0.75`, `0.80`;
- distance threshold exactly `1 - similarity_threshold`.

Historical Plan-079/080/081 candidates remain in the benchmark output for continuity.

## 5. Representation candidates
The controlled Plan-083 representation grid includes:

1. `representative`
   - exact recorded embedding of the existing monthly semantic medoid/representative;
   - L2-normalized by the benchmark grouping path.

2. `constituent_mean`
   - current production control;
   - every persisted non-noise constituent occurrence contributes once;
   - arithmetic mean, then L2 normalization.

3. `constituent_unit_mean`
   - L2-normalize every constituent vector individually;
   - occurrence-weighted arithmetic mean;
   - L2-normalize the resulting monthly vector before grouping.

4. `constituent_probability_weighted_mean`
   - weight each persisted constituent vector by its recorded monthly-HDBSCAN `membership_probability`;
   - divide by the exact persisted weight sum;
   - fail explicitly for missing, negative, non-finite, or zero-total weights;
   - L2-normalize before grouping.

5. `constituent_unique_mean`
   - deduplicate only exact `source_general_theme_label` values within one monthly cluster;
   - average one recorded vector per exact label;
   - L2-normalize before grouping.

All candidate vectors must come from the persisted clustering embedding artifact. Missing or conflicting recorded vectors fail explicitly; no inference fallback is permitted.

## 6. Monthly-cluster cohesion diagnostics
For every non-noise monthly cluster, persist benchmark diagnostics:

- `constituent_observation_count`;
- `constituent_unique_label_count`;
- `mean_constituent_to_centroid_cosine`;
- `minimum_constituent_to_centroid_cosine`;
- `mean_constituent_pairwise_cosine`;
- `minimum_constituent_pairwise_cosine`;
- `representative_to_centroid_cosine`;
- `mean_representative_to_constituent_cosine`;
- `minimum_representative_to_constituent_cosine`.

These metrics characterize whether a monthly cluster is sufficiently cohesive for a centroid to be semantically representative.

## 7. Stage-B family diagnostics
Retain all existing family/noise/cohesion fields and add:

- `largest_family_observation_count`;
- `largest_family_observation_share`;
- `weighted_mean_within_family_representative_cosine`;
- `minimum_within_family_representative_cosine`.

Membership output additionally records:

- `family_observation_count`;
- `family_observation_share`;
- the monthly-cluster cohesion fields above.

Grouping-space cohesion continues to use the representation actually clustered. Representative-space cohesion always uses exact recorded monthly representative embeddings, providing an independent semantic check for centroid-collapse false merges.

## 8. Artifact and CLI surface
Keep the existing benchmark command and output filenames:

```bash
make canonical-theme-benchmark THEMES_DIR=...
```

or:

```bash
python -m src.cli canonical-theme-benchmark --themes-dir ... --out-dir ...
```

Outputs remain:

- `canonicalization_benchmark_summary.csv`;
- `canonicalization_benchmark_membership.csv`.

The schema is extended additively. No production artifacts are changed.

## 9. Regression coverage
Tests must verify:

- occurrence multiplicity remains preserved by `constituent_mean`;
- individual-vector normalization occurs before `constituent_unit_mean` averaging;
- exact persisted HDBSCAN probabilities control weighted means;
- zero/invalid probability totals fail explicitly;
- exact-label deduplication controls `constituent_unique_mean`;
- exact recorded representative vectors are mandatory;
- all representation matrices remain row-aligned with monthly cluster IDs;
- monthly-cluster cohesion diagnostics are finite and bounded where defined;
- observation-weighted family concentration can differ from monthly-cluster concentration;
- representative-space cohesion is calculated independently of grouping representation;
- a synthetic centroid-collapse case merges under a constituent-centroid representation while remaining split under representative embeddings, and representative-space diagnostics expose the false merge;
- existing Plan-079/080/081 benchmark tests and Plan-082 production parity remain green;
- no test invokes TEI, an LLM provider, Azure, or AWS.

## 10. Validation datasets and decision boundary
After implementation, run the read-only benchmark on:

1. the real Telegram forwarded-message run that exposed the remaining centroid-collapse failure;
2. the historical Plan-081 corpus if its original evidence and embedding artifacts can be located, otherwise another completed evolution corpus with the required persisted artifacts.

Historical summary/membership CSVs alone are insufficient to reconstruct new representations and must not be used to invent missing vectors.

The benchmark must not automatically promote a winner. Review family count, singleton behavior, monthly-cluster and observation concentration, grouping-space cohesion, representative-space cohesion, internal monthly-cluster cohesion, semantic memberships, and cross-corpus robustness before any production change is proposed.

## 11. Validation commands
Run where dependencies are available:

```bash
python -m compileall -q src tests
python -m pytest -q tests/unit/test_canonical_theme_benchmark.py
python -m pytest -q tests/unit/test_canonical_theme_benchmark.py tests/unit/test_theme_clustering.py tests/unit/test_orchestration_hashing.py
make validate-config
make format
make lint
make test
git diff --check
```

## 12. Progress Log
- 2026-08-22: Read `HARNESS.md`, `ARCHITECTURE.md`, the required design/product/data/database/metric/pipeline/theme contracts, verification docs, and active Plan 082 before editing.
- 2026-08-22: Confirmed the 2026-08-22 21:25 archive as the source of truth and preserved production canonicalization contract `3.0` unchanged.
- 2026-08-22: Extended only the read-only canonical benchmark with the fixed complete-linkage representation grid at similarity thresholds 0.60–0.80 while retaining historical Plan-079/080/081 variants.
- 2026-08-22: Added persisted-vector reconstruction for individually normalized constituent means, HDBSCAN-membership-probability-weighted means, and exact-unique-label means; representative vectors continue to come from the recorded embedding artifact.
- 2026-08-22: Added monthly-cluster cohesion, representative-space family cohesion, and observation-weighted family concentration diagnostics to the existing benchmark CSV surfaces.
- 2026-08-22: Added regression coverage for representation construction, zero-weight rejection, recorded representative requirements, the controlled Plan-083 grid, observation-weighted concentration, and centroid-collapse false-merge detection.
- 2026-08-22: `python -m compileall -q src tests` passed. The focused canonical benchmark plus existing theme-clustering/orchestration-hashing suite passed with 58 tests.
- 2026-08-22: Direct `python -m src.cli validate-config --config tests/configs/test_single_month.yml` passed. `make validate-config` could not run because the supplied review archive intentionally excludes `.venv` and the Makefile resolves Python through `.venv/bin/python`.
- 2026-08-22: A full `tests/unit` collection attempt was environment-blocked before execution by missing archived-environment dependencies (`kneed`, `mlflow`, `prefect`, and `demoji`); the focused Plan-083 regression set remained green.
- 2026-08-22: The real Parquet benchmark was not rerun inside the review environment because neither `pyarrow` nor `fastparquet` is installed there; no dependency was installed or production code altered to bypass that environment boundary.

- 2026-08-23: Corrected the benchmark input-root resolver after real Telegram validation exposed that the run-local `theme_clusters/` layout stores evidence directly under `evidence/`, while the published `data/themes/` layout stores it under `clusters/evidence/`. Added compatibility tests for both layouts and explicit checked-path errors; production clustering remains unchanged.
- 2026-08-23: Corrective input-layout regression suite passed with 62 focused tests across canonical benchmark, production theme clustering, and orchestration hashing; `python -m compileall -q src tests` and direct config validation also passed.
- 2026-08-23: The real Parquet benchmark remains intentionally unexecuted in this review environment because `pyarrow`/`fastparquet` is unavailable; no dependency or production behavior was changed to bypass that environment boundary.
