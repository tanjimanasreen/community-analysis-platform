# Plan 082 — Production Canonical Theme Clustering Fix

## 1. Objective
Promote the benchmark-supported Plan-081 Stage-B candidate into production while preserving every upstream thesis analytical contract.

The approved production Stage-B contract is:

```text
monthly HDBSCAN cluster
  -> all constituent general-theme embeddings, preserving occurrence multiplicity
  -> arithmetic mean
  -> L2 normalize
  -> cosine-distance agglomerative clustering
  -> complete linkage
  -> similarity threshold 0.65 (distance threshold 0.35)
```

Monthly HDBSCAN remains unchanged.

## 2. Evidence and approval boundary
The user supplied the new Plan-081 `canonicalization_benchmark_summary.csv` and `canonicalization_benchmark_membership.csv` and approved applying this plan to the 2026-08-21 22:14 source snapshot.

The approved candidate is `constituent_mean_normalized_agglomerative_complete_cosine_s65`. Relative to the former production Stage-B HDBSCAN behavior, the benchmark materially reduces largest-family concentration while preserving substantially stronger within-family cosine cohesion. Complete linkage is preferred over average linkage because it prevents bridge/chaining merges whose minimum pairwise family similarity falls below the nominal threshold.

Plan 080 documented an earlier 33-monthly-cluster benchmark population, while the newly supplied Plan-081 files contain 117 monthly clusters. The source archive intentionally excludes generated `local_output/` run artifacts, so that population lineage cannot be mechanically re-derived from the snapshot itself. The user's explicit approval of the supplied Plan-081 result files resolves the promotion gate for this implementation; the benchmark CSVs remain the evidentiary basis and are not copied into production artifacts.

## 3. Production contract
- Keep `MONTHLY_CLUSTER_CONTRACT_VERSION=2.1`.
- Bump `CANONICALIZATION_CONTRACT_VERSION` from `2.1` to `3.0`.
- Reuse the exact observation embeddings already produced for monthly clustering; do not re-embed monthly representative labels for Stage B.
- Build one occurrence-weighted constituent centroid per non-noise monthly cluster and L2-normalize it.
- Group normalized monthly centroids with `sklearn.cluster.AgglomerativeClustering` using:
  - `metric="cosine"`;
  - `linkage="complete"`;
  - `n_clusters=None`;
  - `distance_threshold=0.35`;
  - `compute_full_tree=True`.
- A size-one agglomerative group is a valid `singleton_canonical_theme`; it is not HDBSCAN noise.
- Select the canonical label from existing monthly representative labels using the existing deterministic semantic-medoid rule, but compute that Stage-B medoid over normalized monthly constituent centroids.
- Stable canonical IDs continue to hash the sorted monthly-cluster membership plus the canonicalization contract version.
- No GPT relabeling/manual theme standardization is added.

## 4. Artifact/provenance contract
Persist explicit Stage-B provenance in cluster summary, observation, and canonical-family artifacts:
- representation;
- grouping method;
- implementation;
- metric;
- linkage;
- similarity threshold;
- distance threshold;
- canonicalization contract version.

Canonical-family artifacts additionally persist a generic `stage_b_cluster_label`. The legacy `stage_b_hdbscan_label` column is retained for schema compatibility but is null under contract `3.0`.

The historical `canonicalization_min_cluster_size` field remains present for backward-compatible config/artifact shape, but it no longer controls Stage-B grouping under contract `3.0`.

## 5. Cache/provenance invalidation
- Bump the theme stage cache semantic version.
- Include the canonicalization contract and fixed Stage-B grouping contract in the theme cache key.
- Include the same Stage-B provenance in the provider/run summary digest.
- Old contract-2.1 theme-stage artifacts must not be reused as contract-3.0 outputs.

## 6. Protected contracts
Do not change:
- `shared_post` / `weighted_post` definitions;
- graph thresholds;
- Louvain defaults;
- LDA behavior/defaults;
- translation behavior;
- monthly HDBSCAN or its density semantics;
- community detection/matching;
- GPT theme-generation evidence;
- evolution/member-mobility logic;
- existing analytical output categories.

## 7. Regression coverage
Required tests cover:
- occurrence-weighted constituent centroid construction;
- L2 normalization;
- complete-linkage bridge prevention at cosine similarity 0.65;
- singleton canonical-theme behavior without Stage-B HDBSCAN noise;
- deterministic canonical IDs under input reordering;
- no Stage-B representative-label re-embedding;
- production Stage-B partition parity with the approved Plan-081 benchmark candidate on the same normalized centroid matrix;
- nullable legacy `stage_b_hdbscan_label` plus generic Stage-B label;
- output-contract provenance columns;
- cache-key invalidation across canonicalization contract revisions.

## 8. Validation
Run, where dependencies are available:

```bash
python -m compileall -q src tests
python -m pytest -q tests/unit/test_theme_clustering.py tests/unit/test_canonical_theme_benchmark.py tests/unit/test_orchestration_hashing.py
python -m pytest -q tests/unit/test_output_artifact_contract.py::test_theme_cluster_summary_contract_includes_ambiguous_serialization_diagnostic
make validate-config
make lint
make test
```

Also run `git diff --check` or an equivalent patch whitespace check on the resulting changes.

## 9. Progress Log
- 2026-08-22: Read `HARNESS.md`, `ARCHITECTURE.md`, required design/product/verification contracts, and Plans 079–081 before editing.
- 2026-08-22: Treated the user-supplied Plan-081 CSVs as the approved production evidence after explicit implementation approval; noted that generated run artifacts are excluded from the 22:14 source archive, preventing an independent 33-vs-117 lineage reconstruction from the snapshot alone.
- 2026-08-22: Replaced only production Stage-B canonicalization with normalized occurrence-weighted constituent centroids plus cosine complete-linkage agglomerative clustering at similarity 0.65; monthly HDBSCAN remains unchanged.
- 2026-08-22: Removed the Stage-B representative-label embedding call by reusing monthly observation vectors, preserved deterministic semantic-medoid naming, and bumped canonicalization contract `2.1 -> 3.0`.
- 2026-08-22: Added Stage-B provenance/schema fields, a generic Stage-B label with nullable legacy HDBSCAN label, and cache/run-summary invalidation metadata.
- 2026-08-22: Added regression tests for centroid weighting/normalization, complete-linkage bridge prevention, singleton semantics, deterministic IDs, benchmark parity, schema provenance, and cache invalidation.
- 2026-08-22: Focused Plan-082 regression suite passed: 57 tests covering production clustering, benchmark parity, cache hashing, API cluster-service reads, and the theme-cluster output contract.
- 2026-08-22: `python -m compileall -q src tests` passed and direct `python -m src.cli validate-config --config tests/configs/test_single_month.yml` passed. `make validate-config` could not run because this archive intentionally excludes `.venv`; the equivalent CLI validation passed.
- 2026-08-22: Repository formatting/lint tooling could not be provisioned offline: system `black`, `ruff`, and `pre-commit` are unavailable, while `uv run --frozen` attempted dependency resolution and was blocked by network/DNS access. Equivalent local checks passed for changed-Python AST parsing, YAML parsing, trailing whitespace, merge markers, and final newlines.
- 2026-08-22: Broader artifact/pipeline test attempts were dependency-blocked where the archived environment lacks `pyarrow`/`fastparquet` or `prefect`; failures occurred before Plan-082 functional assertions. No dependencies were installed or repository state altered to bypass those environment constraints.
