# Plan 087 — Production Stage-A Theme Clustering Robustness Promotion

Status: implemented; local validation complete; real Telegram/Twitter production revalidation pending

Owner: agent

Last updated: 2026-08-24

## 1. Objective

Promote the cross-platform Plan-086 Stage-A candidate
`unit_euclidean_leaf_ms3` into production monthly theme clustering after clean
post-Plan-085 Telegram and Twitter benchmarks showed two independent failures in
the contract-2.2 raw-Euclidean/EOM baseline:

- broad heterogeneous EOM parent clusters (Telegram July, Twitter April);
- missed semantic density under raw Euclidean geometry (Telegram October).

The promotion must reproduce the benchmark candidate exactly while preserving raw
recorded embedding artifacts, semantic-medoid representative logic, and the approved
Stage-B canonicalization contract.

## 2. Approved production contract

Production Stage A becomes:

```text
raw recorded all-MiniLM-L6-v2 float32 embeddings
  -> in-memory float64 L2-normalized copy
  -> sklearn.cluster.HDBSCAN
       min_cluster_size = configured value (default 2)
       min_samples = min_cluster_size + 1 (default 3)
       metric = euclidean
       cluster_selection_method = leaf
       allow_single_cluster = false
```

The raw embedding artifact remains unnormalized. Monthly semantic medoids and Stage-B
representative resolution continue to use the recorded raw vectors; only the matrix
passed to Stage-A HDBSCAN is normalized.

## 3. Frozen contracts

No changes to:

- IF/WIF (`shared_post`, `weighted_post`) metrics;
- graph thresholds, Louvain, community matching/evolution;
- LDA defaults;
- translation or theme-generation provider behavior;
- embedding model/revision or recorded embedding dtype/normalization contract;
- `min_cluster_size` default `2`;
- sklearn-inclusive `min_samples=3` at the default cluster size;
- HDBSCAN metric `euclidean`;
- `allow_single_cluster=false`;
- Stage-B contract `4.0`: monthly semantic representative -> L2 normalize -> cosine
  complete-linkage agglomerative clustering at similarity `0.65`;
- API/frontend analytical behavior or output categories.

## 4. Contract and cache versions

- `MONTHLY_CLUSTER_CONTRACT_VERSION`: `2.2 -> 3.0` because Stage-A analytical geometry
  and cluster selection change.
- `CANONICALIZATION_CONTRACT_VERSION`: remains `4.0`.
- `THEME_STAGE_CACHE_VERSION`: `2.3.0 -> 3.0.0` so pre-promotion Stage-A artifacts
  cannot be restored.
- Theme-stage cache identity explicitly includes Stage-A normalization, effective
  `min_samples`, selection method, and `allow_single_cluster` alongside the contract
  versions and configured metric/cluster size.

## 5. Artifact provenance

Keep `embedding_normalized=false` because it describes the persisted/raw recorded
embedding artifact. Add explicit Stage-A provenance to monthly summary, observation,
and canonical-family artifacts:

- `clustering_input_normalized=true`;
- `hdbscan_min_samples=<min_cluster_size + 1>`;
- `hdbscan_cluster_selection_method="leaf"`;
- `hdbscan_allow_single_cluster=false`.

Existing `clustering_metric="euclidean"`, HDBSCAN implementation/version, model
metadata, contract versions, and Stage-B provenance remain present.

These fields are additive in the newly produced clustering dataframes. The global
historical artifact-reader required-column set is not tightened by this plan, so older
contract-2.2 run bundles remain readable/validatable after the production upgrade.

## 6. Historical Plan-086 benchmark stability

Plan 086 remains a read-only benchmark over contract-2.2 evidence. It must not silently
reinterpret its raw-Euclidean/EOM baseline after production moves to contract `3.0`.
The benchmark therefore pins its accepted source monthly-cluster contract to `2.2` and
explicitly requests EOM for baseline reconstruction. The promoted
`unit_euclidean_leaf_ms3` candidate reuses the same production L2-normalization helper
so production/benchmark geometry cannot drift silently.

## 7. Regression coverage

Required tests cover:

- production contract version `3.0`, unit-vector clustering input, leaf selection, and
  unchanged raw embedder output;
- zero/non-finite vector rejection before Stage-A HDBSCAN;
- default sklearn-inclusive `min_samples=3`, Euclidean metric, and
  `allow_single_cluster=false`;
- artifact provenance differentiating raw recorded embeddings from normalized clustering
  input;
- direct production-vs-Plan-086 `unit_euclidean_leaf_ms3` labels/probabilities parity for
  the same raw matrix;
- historical contract-2.2 benchmark baseline preservation;
- theme cache invalidation for `2.2 -> 3.0`, Stage-A geometry/selection changes, and
  theme-stage semantic version `3.0.0`;
- unchanged Stage-B representative/cosine/complete-linkage `0.65` behavior.

No automated test may call TEI, OpenAI, translation providers, or other external
services.

## 8. Validation

Run where dependencies are available:

```bash
python -m compileall -q src tests
PYTHONPATH=. pytest -q \
  tests/unit/test_theme_clustering.py \
  tests/unit/test_monthly_cluster_benchmark.py \
  tests/unit/test_canonical_theme_benchmark.py \
  tests/unit/test_orchestration_hashing.py
python -m src.cli validate-config --config tests/configs/test_single_month.yml
make format
make lint
make test
git diff --check
```

After local validation, run fresh Telegram and Twitter production evolution pipelines
with unchanged analytical configuration and verify the contract-3.0 provenance,
month-level Stage-A behavior, identical-vector consistency, and fixed Stage-B health.

## 9. Progress log

- 2026-08-24: Treated `community-analysis-full-review-20260824-0610.zip` as source of
  truth (branch `feature/frontend-ui-upgrade`, HEAD
  `c5ee46215b43618ac58c39fd8416f155c3e07bcf`) with Plans 085-086 and the Plan-086
  identical-embedding hardening applied.
- 2026-08-24: Re-read the prescribed repository contracts and active Plan 086 before
  editing. Confirmed production contract `2.2` was raw Euclidean + EOM and Stage B was
  contract `4.0` representative + cosine complete linkage at `0.65`.
- 2026-08-24: Promoted only the approved Stage-A benchmark behavior: an in-memory
  float64 L2-normalized copy is passed to HDBSCAN and selection changes to `leaf`.
  Recorded float32 embeddings remain raw and semantic-medoid/Stage-B calculations retain
  the original recorded vectors.
- 2026-08-24: Bumped monthly clustering contract to `3.0` and theme-stage cache version
  to `3.0.0`; added explicit Stage-A cache identity/provenance fields. Stage-B contract
  remains `4.0`.
- 2026-08-24: Froze Plan-086 benchmark source compatibility to contract `2.2`, kept its
  historical EOM baseline explicit, and shared the production L2 normalization helper
  with the unit-Euclidean benchmark candidate.
- 2026-08-24: Focused Stage-A/Stage-B/benchmark/cache/output-schema regression suite
  passed: 95 tests across monthly production clustering, the Plan-086 Stage-A benchmark,
  the canonical Stage-B benchmark, orchestration hashing, and the direct cluster-schema
  contract assertion. `python -m compileall -q src tests scripts`, direct CLI config
  validation, and `git diff --check` also passed.
- 2026-08-24: Full Parquet-writing validation is blocked in this review runtime because
  `pyarrow`/`fastparquet` is unavailable. `python -m black` is unavailable, and
  `make lint` could not resolve the frozen environment because outbound package-download
  DNS failed while fetching an existing scikit-learn dependency. No dependency or source
  behavior was changed to bypass those environment limits.
