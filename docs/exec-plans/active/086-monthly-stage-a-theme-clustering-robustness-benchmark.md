# Plan 086 — Monthly Stage-A Theme Clustering Robustness Benchmark

Status: complete; cross-platform promotion evidence accepted by Plan 087

Owner: agent

Last updated: 2026-08-23

## 1. Objective

Add a read-only benchmark for monthly Stage-A theme clustering after Plan 085 repaired
general-theme serialization. The benchmark must explain two clean-data failure modes
before any production HDBSCAN default is changed:

- Telegram October: 29 valid observations, 29 noise, zero monthly clusters.
- Telegram July: one 76-observation monthly cluster with poor semantic cohesion.

This plan does not change production clustering, cache identity, API/frontend behavior,
or any thesis metric/default.

## 2. Frozen production contracts

Keep unchanged:

- `MONTHLY_CLUSTER_CONTRACT_VERSION=2.2`;
- `CANONICALIZATION_CONTRACT_VERSION=4.0`;
- `THEME_STAGE_CACHE_VERSION=2.3.0`;
- clustering model `sentence-transformers/all-MiniLM-L6-v2`;
- unnormalized production embedding geometry;
- `sklearn.cluster.HDBSCAN`;
- `min_cluster_size=2`;
- production `min_samples=3` (the documented sklearn inclusive-count translation);
- `metric="euclidean"`;
- `cluster_selection_method="eom"`;
- `allow_single_cluster=false`;
- Stage-B monthly-semantic-representative + L2 normalization + cosine complete linkage
  at similarity `0.65`.

No IF/WIF, graph, Louvain, LDA, translation, GPT/provider, community matching/evolution,
output-category, API, or frontend behavior changes are in scope.

## 3. Read-only benchmark boundary

Add `src/themes/monthly_cluster_benchmark.py` plus CLI/Make integration. The benchmark
reads only persisted:

```text
theme_clusters/evidence/*.parquet
theme_clusters/embeddings/clustering_general_themes.parquet
```

Both run-local `theme_clusters/` and published `data/themes/` layouts are supported.
The benchmark never calls TEI, OpenAI, translation providers, LDA, network analysis,
or the production pipeline.

Exact recorded vectors are expanded back to every persisted evidence occurrence so
Stage-A density semantics preserve duplicate theme observations.

## 4. Mandatory production-baseline fidelity

Before candidate comparison, reconstruct current production Stage A from the persisted
raw float32 vectors with the production `_fit_hdbscan` helper. For every period:

- the noise membership must match exactly;
- the non-noise partition must match exactly, ignoring arbitrary integer cluster-label
  renumbering;
- persisted and reconstructed HDBSCAN membership probabilities must agree within a
  small rounding tolerance;
- stable monthly cluster IDs and monthly semantic representatives reconstructed through
  the production `_monthly_clusters` helper must match the persisted evidence exactly.

If fidelity fails for any period, abort the benchmark. Evidence with a recorded monthly
clustering contract other than the current `2.2` is rejected so pre-Plan-085 corrupted
artifacts cannot become a promotion baseline.

## 5. Controlled candidate grid

Keep `min_cluster_size=2` fixed and vary only:

### Geometry

- `raw_euclidean` — current production geometry/control;
- `unit_euclidean` — L2-normalized vectors with Euclidean HDBSCAN;
- `cosine` — cosine HDBSCAN using sklearn's brute-force distance path.

### Cluster selection

- `eom` — current production selection;
- `leaf` — benchmark-only finer leaf selection.

### Density

- `min_samples=3` — current production effective density threshold;
- `min_samples=2` — benchmark-only less-conservative candidate.

The main grid therefore contains 12 variants. No production default changes merely
because a candidate is present in the benchmark.

## 6. Diagnostic-only single-cluster variant

Also run:

```text
raw_euclidean + eom + min_samples=3 + allow_single_cluster=true
```

Mark it `diagnostic_only=true`. It is not promotion-eligible. Its only purpose is to
help determine whether an all-noise month represents no stable density structure or a
single broad structure suppressed by the production `allow_single_cluster=false`
contract.

## 7. Explicitly excluded experiments

Do not benchmark in this plan:

- UMAP;
- different embedding models;
- DBSCAN/KMeans/agglomerative Stage A;
- `max_cluster_size` caps;
- `cluster_selection_epsilon` tuning;
- manual cluster-count targets;
- month-specific parameters or special cases.

## 8. Diagnostics

For every variant and period report:

- observation, cluster, clustered-observation, and noise counts/rates;
- largest cluster size and share of all/clustered observations;
- median/mean cluster size;
- membership-probability diagnostics;
- size-2/size-3 cluster counts and cluster-count/observation ratio;
- embedding norm distribution;
- mean top-1/top-2 nearest-neighbour cosine similarities;
- mean top-1/top-2 Euclidean distances;
- top-1 cosine separately for production-clustered and production-noise observations.

For every candidate/period, fingerprint the exact persisted float32 recorded vectors and
report duplicate-vector assignment consistency. Identical recorded embeddings may occur
multiple times because observation multiplicity is preserved. A promotion candidate must
never assign one identical-vector group to multiple non-noise clusters. Report a separate
noise/non-noise boundary-tie count because that case is not equivalent to semantic
fragmentation. Membership output records the embedding SHA-256 and duplicate-group size
for direct audit.

For every non-noise candidate cluster, use cosine as an independent semantic audit
metric regardless of clustering geometry and report:

- mean/minimum pairwise cosine;
- mean/minimum representative-to-member cosine;
- existing deterministic semantic-medoid representative;
- observation, unique-label, and community-pair counts;
- mean membership probability and complete unique member-label evidence.

Period output also reports maximum cosine between distinct cluster representatives as a
fragmentation diagnostic.

## 9. Fixed Stage-B impact audit

For each Stage-A candidate, feed only its resulting monthly semantic medoids and their
already-recorded vectors through the existing production Stage-B helper:

```text
monthly semantic medoid
  -> L2 normalize
  -> cosine complete linkage
  -> similarity 0.65
```

Report monthly-cluster count, canonical-family count, largest family cluster/observation
share, and minimum within-family representative cosine. This is an impact audit only;
Stage B is not retuned by Plan 086.

## 10. Outputs

Write four additive CSVs:

```text
monthly_clustering_benchmark_summary.csv
monthly_clustering_benchmark_periods.csv
monthly_clustering_benchmark_clusters.csv
monthly_clustering_benchmark_membership.csv
```

No production run artifact is modified.

## 11. Decision rule

There is no automatic winner/score. Review candidates manually against:

- coherent recovery of all-noise periods rather than forced clusters;
- removal of semantically incoherent mega-clusters;
- worst-cluster and weighted semantic cohesion;
- acceptable noise without artificial zero-noise behavior;
- fragmentation/tiny-cluster diagnostics;
- zero identical-recorded-embedding groups split across multiple non-noise clusters;
- preservation of healthy months and corrected June behavior;
- healthy fixed Stage-B concentration/cohesion;
- cross-platform agreement on clean post-Plan-085 corpora.

No production Stage-A change may be proposed from Telegram alone. A promising candidate
must also be benchmarked on a clean post-Plan-085 Twitter corpus.

## 12. Regression coverage

Tests must cover:

- run-local and published input layouts;
- exact production-baseline partition/noise/probability/cluster-ID/representative
  reconstruction and fail-fast mismatch behavior;
- all-noise reporting without forced clusters;
- an EOM parent-cluster fixture where leaf selection exposes finer structure;
- a vector-norm fixture where raw Euclidean differs from unit/cosine geometry;
- duplicate observation expansion from deduplicated recorded vectors;
- exact recorded-vector fingerprint/group-size membership output;
- explicit failure diagnostic for identical embeddings split across multiple non-noise
  clusters, while a noise-versus-single-cluster boundary tie is reported separately;
- cosine cohesion and fixed Stage-B impact fields;
- 12 main variants plus one diagnostic-only `allow_single_cluster=true` variant;
- rejection of pre-Plan-085 monthly contract artifacts;
- creation of all four CSV outputs without provider/inference calls.

## 13. Validation

Run where dependencies are available:

```bash
python -m compileall -q src tests
PYTHONPATH=. pytest -q \
  tests/unit/test_monthly_cluster_benchmark.py \
  tests/unit/test_theme_clustering.py \
  tests/unit/test_canonical_theme_benchmark.py \
  tests/unit/test_orchestration_hashing.py
python -m src.cli validate-config --config tests/configs/test_single_month.yml
make format
make lint
make test
git diff --check
```

Automated tests must not call TEI, OpenAI, translation providers, or other external
services.

## 14. Real benchmark command

After patch application, run against the existing clean Telegram Plan-085 result:

```bash
make monthly-theme-cluster-benchmark \
  THEMES_DIR=local_output/telegram/forwarded_message_evolution/runs/f1d62bc2-88ba-4407-98c1-9c48e2f28f41/telegram/theme_analysis/forward/theme_clusters \
  MONTHLY_CLUSTER_BENCHMARK_OUT=local_output/benchmarks/monthly-theme-clustering/plan086-telegram
```

No evolution-pipeline rerun is required for this benchmark.

## 15. Progress log

- 2026-08-23: Treated `community-analysis-full-review-20260823-1848.zip` as source of
  truth (branch `feature/frontend-ui-upgrade`, HEAD
  `c5ee46215b43618ac58c39fd8416f155c3e07bcf`) with Plan 085 applied in the archived
  working tree.
- 2026-08-23: Re-read the required repository contracts in prescribed order plus Plans
  039, 043, 083, 084, and 085 before editing.
- 2026-08-23: Added the read-only Stage-A benchmark module, CLI command, Make target,
  four-output evidence surface, mandatory baseline-fidelity gate, controlled 12-variant
  grid, and one diagnostic-only single-cluster variant. No production clustering code or
  analytical configuration was modified.
- 2026-08-23: Added synthetic regression coverage for all-noise, EOM-vs-leaf hierarchy,
  vector-norm geometry, occurrence multiplicity, fixed Stage-B impact, baseline mismatch,
  current-contract guard, and four-output writing.
- 2026-08-23: Focused regression validation passed with 86 tests across the new
  Stage-A benchmark, production monthly/Stage-B clustering, the existing Stage-B
  canonical benchmark, and orchestration hashing. The new benchmark suite also verifies
  CLI dispatch.
- 2026-08-23: `python -m compileall -q src tests`, direct CLI config validation, CLI
  help/dispatch, and a dry-run of the new Make target passed. New Python/test files have
  no >88-character lines.
- 2026-08-23: The review environment cannot execute the real Parquet benchmark because
  `pyarrow`/`fastparquet` is unavailable. A frozen `uv` environment attempt was blocked
  by network/DNS while resolving existing locked dependencies; no dependency or
  production behavior was changed to bypass the environment boundary.

- 2026-08-24: Clean Telegram benchmark on run
  `f1d62bc2-88ba-4407-98c1-9c48e2f28f41` confirmed that EOM can select an
  incoherent July parent cluster and raw Euclidean can leave October entirely as noise.
  Leaf selection removed the July mega-cluster; angular geometry recovered conservative
  October structure. `min_samples=2` and `allow_single_cluster=true` were rejected for
  excessive fragmentation/broad clustering.
- 2026-08-24: Clean Twitter Retweet-Quote benchmark on run
  `b31547eb-c789-4e23-a1be-4b1741c8bcb2` independently reproduced the EOM broad-parent
  failure. Direct cosine + leaf improved aggregate cohesion but split identical recorded
  embeddings across multiple non-noise clusters. Unit-normalized Euclidean + leaf with
  `min_samples=3` retained comparable semantic gains without that multi-cluster duplicate
  fragmentation in the reviewed Twitter evidence and is the current promotion candidate.
- 2026-08-24: Hardened the read-only benchmark with exact recorded-vector SHA-256/group
  diagnostics and a formal non-noise duplicate-vector consistency promotion gate. The
  benchmark continues to report all candidates and does not mutate production defaults.
- 2026-08-24: Hardened Telegram rerun confirmed `unit_euclidean_leaf_ms3` has zero
  identical-embedding groups split across multiple non-noise clusters. Hardened Twitter
  rerun independently confirmed zero non-noise splits for the same candidate; the one
  two-observation noise-boundary tie matched the baseline class of density-boundary
  behavior and did not create multiple semantic clusters.
- 2026-08-24: The hardened Twitter result formally rejected direct `cosine_leaf_ms3`:
  eight identical-vector groups covering 77 observations were split across multiple
  non-noise clusters, with one group spanning four non-noise cluster labels.
- 2026-08-24: Cross-platform decision accepted `unit_euclidean_leaf_ms3` for production
  promotion: L2-normalized Euclidean geometry + leaf selection + `min_samples=3`, with
  `min_cluster_size=2` and `allow_single_cluster=false` retained. Plan 087 owns the
  production contract change; this benchmark remains pinned to clean contract-2.2
  evidence and its historical raw-Euclidean/EOM baseline.
