# Plan 084 — Production Stage-B Representative Clustering Fix

## 1. Objective
Promote the cross-corpus Plan-083 winner into production while changing only the Stage-B monthly-cluster representation.

The approved production Stage-B contract is:

```text
monthly HDBSCAN cluster
  -> existing deterministic semantic-medoid / monthly representative embedding
  -> L2 normalize
  -> cosine-distance agglomerative clustering
  -> complete linkage
  -> similarity threshold 0.65 (distance threshold 0.35)
```

Monthly HDBSCAN and every upstream thesis analytical contract remain unchanged.

## 2. Evidence and approval boundary
Plan 083 was run read-only against two completed longitudinal corpora after Plan 082 production validation exposed centroid collapse on Telegram.

Telegram forwarded-message validation:
- 33 non-noise monthly clusters.
- Plan-082 constituent-mean representation at similarity 0.65 produced 18 canonical families; the largest family contained 9 monthly clusters and approximately 86.7% of non-noise theme observations, while its minimum representative-space cosine was approximately 0.205.
- Plan-083 monthly-representative representation at similarity 0.65 produced 26 canonical families; the largest family contained 3 monthly clusters, the largest observation share was approximately 22.3%, and minimum within-family cosine was approximately 0.774.

Twitter retweet/quote validation:
- 117 monthly clusters.
- Constituent-mean complete-linkage 0.65 produced 46 families with minimum representative-space cosine approximately 0.515.
- Monthly-representative complete-linkage 0.65 produced 57 families, largest family size 7, largest observation share approximately 8.5%, and minimum within-family/representative-space cosine approximately 0.653.

The user explicitly approved implementation after reviewing these cross-corpus results. The production threshold remains 0.65; only the Stage-B representation changes.

## 3. Production contract
- Keep `MONTHLY_CLUSTER_CONTRACT_VERSION=2.1`.
- Bump `CANONICALIZATION_CONTRACT_VERSION` from `3.0` to `4.0`.
- Set production representation provenance to `monthly_semantic_representative_l2_normalized`.
- Reuse the exact embedding already produced for the monthly semantic medoid/representative; do not issue a second embedding request.
- Do not average constituent embeddings in production Stage B.
- L2-normalize each monthly representative vector.
- Group normalized representative vectors with `sklearn.cluster.AgglomerativeClustering` using:
  - `metric="cosine"`;
  - `linkage="complete"`;
  - `n_clusters=None`;
  - `distance_threshold=0.35`;
  - `compute_full_tree=True`.
- A size-one Stage-B group remains a valid `singleton_canonical_theme`.
- Canonical labels remain existing monthly representatives selected by the deterministic semantic-medoid rule over Stage-B family representative vectors.
- Canonical IDs continue to hash sorted monthly-cluster membership plus the canonicalization contract version.
- No GPT relabeling or manual theme standardization is added.

## 4. Representative-vector integrity
The production Stage-B boundary must fail explicitly if:
- a monthly cluster's representative label cannot be found among its own constituent observations;
- repeated occurrences of the representative label map to inconsistent recorded vectors;
- the representative vector is zero or non-finite.

There is no silent centroid fallback and no representative-label re-embedding.

## 5. Artifact and provenance contract
Existing artifact schemas remain additive and unchanged. Summary, evidence, and canonical-family artifacts continue to persist:
- canonicalization representation;
- grouping method and implementation;
- metric and linkage;
- similarity and distance thresholds;
- canonicalization contract version;
- generic `stage_b_cluster_label`;
- nullable legacy `stage_b_hdbscan_label`.

Only the representation value and contract version change for Plan 084.

## 6. Cache invalidation
- Bump the theme-stage cache semantic version.
- The theme-stage cache key already includes the canonicalization contract and representation constants; contract `3.0` artifacts therefore cannot be restored as contract `4.0` outputs.
- Translation, network/community, and topic-stage analytical contracts are unchanged.

## 7. Protected contracts
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
- existing analytical output categories;
- cosine complete-linkage grouping or the 0.65 Stage-B similarity threshold.

## 8. Regression coverage
Required tests cover:
- exact monthly representative-vector reuse and L2 normalization;
- no constituent-centroid fallback;
- explicit failure for missing representative vectors;
- explicit failure for inconsistent repeated representative vectors;
- complete-linkage bridge prevention at cosine similarity 0.65;
- singleton canonical-theme behavior;
- deterministic canonical IDs under input reordering;
- no additional representative-label embedding calls;
- production Stage-B partition parity with the Plan-083 representative + complete-linkage cosine-0.65 benchmark candidate;
- artifact provenance remains schema-compatible;
- theme-stage cache invalidation across canonicalization contract revisions.

## 9. Validation
Run, where dependencies are available:

```bash
python -m compileall -q src tests
PYTHONPATH=. pytest -q tests/unit/test_theme_clustering.py tests/unit/test_canonical_theme_benchmark.py tests/unit/test_orchestration_hashing.py
PYTHONPATH=. pytest -q tests/unit/test_output_artifact_contract.py
python -m src.cli validate-config --config tests/configs/test_single_month.yml
make format
make lint
make test
git diff --check
```

The real Telegram/Twitter evolution pipelines are validation after patch application in the user's fully provisioned local environment; they are not required to make live provider calls inside automated tests.

## 10. Progress Log
- 2026-08-23: Read `HARNESS.md`, `ARCHITECTURE.md`, the required design/product/data/database/metric/pipeline/theme-intelligence contracts, verification gates/matrix, and Plans 082–083 before editing.
- 2026-08-23: Treated `community-analysis-full-review-20260823-0254.zip` as the source of truth; confirmed Plan 083 and its run-local benchmark input-layout correction are present.
- 2026-08-23: Promoted only the Plan-083 monthly semantic representative representation into production Stage B; cosine complete linkage and threshold 0.65 remain unchanged, and monthly HDBSCAN remains contract 2.1.
- 2026-08-23: Bumped canonicalization contract `3.0 -> 4.0`, updated representation provenance, and bumped the theme-stage cache semantic version so prior Stage-B artifacts cannot be reused.
- 2026-08-23: Added explicit representative-vector integrity failures and updated production/benchmark parity to the Plan-083 representative candidate.
- 2026-08-23: Focused regression validation passed with 89 tests covering production clustering, Plan-083 benchmark parity, orchestration hashing, cluster-service reads, config contracts, and static output-artifact schema checks.
- 2026-08-23: `python -m compileall -q src tests` and direct `PYTHONPATH=. python -m src.cli validate-config --config tests/configs/test_single_month.yml` passed.
- 2026-08-23: Full output-artifact tests that write Parquet were environment-blocked because the review interpreter has neither `pyarrow` nor `fastparquet`; the schema-only output-contract checks passed.
- 2026-08-23: Full `tests/unit` collection was environment-blocked before execution by missing review-environment dependencies (`kneed`, `mlflow`, `prefect`, and `demoji`). No dependency was installed or production behavior altered to bypass those boundaries.
- 2026-08-23: `make validate-config` and `make format` were blocked by the archive-local `.venv` missing required packages (`pydantic` and `black`). `make lint` and `make test` attempted frozen dependency resolution through `uv` and were blocked by unavailable network/DNS. Equivalent focused tests, direct config validation, compileall, and patch/static checks were used instead.
