# Plan 039 — Production Theme Clustering and Canonicalization

## Goal

Add a production, reproducible semantic clustering stage for **general themes from matched IF/WIF communities** so that both **Thematic Analysis** and **Overview → Top Themes** report semantically consolidated themes instead of exact GPT-label strings, while preserving the raw theme artifacts and keeping **Community Evolution thematic similarity** analytically separate.

## Scope decisions

### Thematic Analysis / Overview
- Source population: all matched IF/WIF communities in the run.
- Theme source: `general_theme_names` only.
- Theme evidence: `general_theme_gpt` / corresponding general LDA keyword evidence.
- Community identity: distinct `(absolute_community, weighted_community)` pair.
- Monthly top themes: clustered/canonical themes, ranked by distinct matched-pair coverage.
- Thematic Analysis progression: aggregate theme progression across months; no persisted-community continuity data.

### Community Evolution
- Persisted community paths remain a separate analysis.
- Existing thematic-similarity logic remains separate from theme clustering.
- Community Evolution continues to use its own configured embedding profile and cosine-similarity outputs.

## Embedding architecture

Use two TEI instances with separate analytical profiles:

1. **Similarity TEI**
   - Purpose: Community Evolution thematic similarity.
   - Model: `sentence-transformers/paraphrase-MiniLM-L6-v2`.
   - Default local port: `8080`.
   - Preserve existing behavior and compatibility.

2. **Clustering TEI**
   - Purpose: Thematic Analysis/Overview theme clustering and canonicalization.
   - Model: `sentence-transformers/all-MiniLM-L6-v2`.
   - Default local port: `8081`.
   - Additive; must not change the similarity profile.

Both profiles pin exact Hugging Face model revisions independently. A model alias without a pinned revision is not sufficient production provenance.

`make tei-up` should start both services. `make tei-check` should verify both services with real lightweight embedding requests, and `make tei-down` should stop both cleanly. Optional individual targets may exist for debugging.

Analytical modules receive a configured embedding client/profile; they must never hard-code ports or load SentenceTransformer models directly.

Automated tests must use injected/fake embeddings and must not call TEI or download models.

## Stage A — Monthly clustering

For each run and month:

1. Load matched-community raw theme records.
2. Use only `general_theme_names`; do not silently fall back to IF/WIF labels. When multiple saved names were serialized by the generator as a dot-joined value, use the corresponding `general_theme_gpt` mapping only to reconstruct those same general labels and their per-label LDA keyword evidence; the mapping must not supply labels when `general_theme_names` is missing.
3. Preserve theme occurrences rather than deduplicating labels before HDBSCAN, because occurrence density is part of the clustering behavior.
4. Obtain embeddings from the clustering TEI profile (`all-MiniLM-L6-v2`).
5. Preserve the notebook-style clustering geometry while using the maintained project dependency stack:
   - `sklearn.cluster.HDBSCAN`
   - `min_cluster_size=2`
   - `min_samples=3` for the default contract (`min_cluster_size + 1`) to account for scikit-learn's inclusive `min_samples` definition versus the legacy scikit-contrib implementation
   - `metric="euclidean"`
   - `cluster_selection_method="eom"`
   - `allow_single_cluster=False`
   - no UMAP
   - no `prediction_data` because the pipeline does not perform approximate prediction
   - persist membership probabilities and the exact scikit-learn version as provenance.
6. Request unnormalized vectors from the clustering TEI profile and do not post-normalize them before Euclidean HDBSCAN. This keeps clustering geometry distinct from the normalized-vector default retained by Community Evolution similarity.
7. Treat HDBSCAN `-1` as monthly clustering noise.
8. Keep noise records in audit artifacts, but exclude them from clustered monthly Top Theme ranking.
9. For every non-noise cluster, choose the representative label using semantic centrality:
   - pairwise cosine similarity among cluster observations;
   - mean similarity per observation;
   - highest mean similarity wins;
   - deterministic tie-break using normalized lexical order plus a stable source key.

## Stage B — Cross-month canonicalization

Replace the thesis manual standardization step with an automated, reproducible canonicalization stage.

Within a single run only:

1. Take one representative observation for every non-noise monthly cluster.
2. Embed those representatives with the same clustering TEI profile (`all-MiniLM-L6-v2`).
3. Cluster the monthly representatives across the run with a separately versioned HDBSCAN canonicalization contract.
4. Monthly representatives grouped together become one **canonical theme family**.
5. Stage-B HDBSCAN noise becomes a valid **singleton canonical theme** rather than being discarded, because a theme may be unique to one month and still be analytically meaningful.
6. Choose the canonical label using semantic centrality among the family’s monthly representative labels, with deterministic tie-breaking.
7. Never canonicalize across different runs, platforms, or content types.

This stage is the production replacement for the thesis’s manual label standardization. It should be described as thesis-aligned and fully reproducible, not as bit-for-bit reproduction of the historical manually curated tables.

## Community aggregation

After monthly clustering and canonicalization:

- Count **distinct matched IF/WIF pairs** per canonical theme per month.
- A matched pair carrying multiple source labels that resolve to the same canonical theme counts once for that theme in that month.
- Percentage denominator: all themed matched pairs for the month.
- Multiple themes may occur in one pair, so percentages across themes may sum to more than 100%.
- Track missing `general_theme_names` records as diagnostics; do not substitute absolute/weighted labels.

## LDA keyword aggregation

For every canonical theme/month:

1. Collect general LDA keyword evidence from all matched pairs mapped to the canonical theme.
2. Deduplicate support within each matched pair.
3. Rank keywords by number of distinct matched pairs supporting the keyword.
4. Use deterministic source-order/lexical tie-breaking.
5. Publish enough ranked keywords for downstream consumers; Thematic Analysis may display five and Overview may display three.

LDA remains the analytical evidence beneath GPT themes and semantic clustering.

## Artifact strategy

Preserve all current raw theme artifacts unchanged.

Add versioned additive artifacts following the repository’s existing artifact/manifest conventions after inspecting the full source tree.

Logical monthly-cluster fields should include:
- run ID / period
- monthly cluster key
- HDBSCAN diagnostic label
- representative general theme
- source general-theme observations/labels
- matched community pairs
- prominent LDA keywords
- membership probabilities / cluster diagnostics where available
- noise flag

Logical canonical-theme fields should include:
- canonical theme ID
- canonical label
- monthly cluster IDs
- monthly representatives
- source general-theme labels
- matched community count per month
- matched community pairs per month
- prominent LDA keywords per month
- months present
- provenance/version metadata

Use stable hash-based IDs derived from canonical source identities and contract versions. Do not expose HDBSCAN integer labels as permanent analytical IDs.

Add immutable run-local embedding artifacts for semantic inference. The clustering
profile always publishes one when clustering is enabled; the similarity profile
publishes one when Community Evolution similarity rendering is enabled:
- exact unique source text plus a content-addressed embedding key;
- `float32` fixed-size vector;
- profile/provider/model ID and pinned model revision;
- normalization/preprocessing/embedding-contract versions;
- text and vector SHA-256 hashes.

Duplicate exact source texts may be embedded once for efficiency, but their vectors must be expanded back to every original theme observation before HDBSCAN so observation density is unchanged. TEI remains the inference service; no vector database or Memgraph vector storage is introduced.

Provenance should include at minimum:
- clustering contract version
- canonicalization contract version
- embedding provider (`tei`)
- model ID and pinned/reported model revision when available
- HDBSCAN version and explicit parameters
- source artifact hashes
- code version/commit when available
- output artifact SHA-256

## API design

Do not change the semantic meaning of existing raw/exact-theme endpoints unless required for compatibility.

Add/read clustered-theme reporting endpoints following current API conventions, logically equivalent to:

- monthly clustered themes for a run/period
- timeline clustered themes for a run/range
- optional canonical-theme evidence/drill-down

The API must only read saved clustered artifacts. It must never invoke TEI or HDBSCAN during a dashboard request.

## Thematic Analysis migration

The Thematic Analysis page should consume canonical clustered themes for:

- monthly top-five themes;
- prominent LDA keywords;
- matched-pair counts and percentages;
- timeline leader;
- aggregate theme progression across months.

Progression connects canonical theme identity across months. It must not use persisted community paths, Jaccard transitions, retained members, or Community Continuity data.

Evidence should remain auditable by exposing:
- canonical theme;
- monthly representative theme;
- source raw `general_theme_names` labels;
- general LDA keywords;
- matched IF/WIF pair IDs;
- links to existing community/network evidence where supported.

## Overview migration

Overview → Top Themes must use the **same server-side clustered monthly result** as Thematic Analysis.

Remove the duplicate frontend exact-label aggregation from the visible Top Themes panel once parity is protected.

For the same run/month:
- rankings and canonical theme IDs must match Thematic Analysis;
- Overview may render fewer keywords for compactness.

Do not conflate this panel with any legacy run-wide `overview.top_themes` field that may still serve other consumers.

## Multi-profile TEI implementation

Preserve the existing similarity service on port 8080 and add clustering on 8081.

Recommended local defaults:

- similarity: `http://127.0.0.1:8080`
- clustering: `http://127.0.0.1:8081`

Recommended configuration separation:

```yaml
embeddings:
  similarity:
    provider: tei
    model: sentence-transformers/paraphrase-MiniLM-L6-v2
    base_url: http://127.0.0.1:8080
  clustering:
    provider: tei
    model: sentence-transformers/all-MiniLM-L6-v2
    base_url: http://127.0.0.1:8081
```

Exact config keys must follow the repository’s existing configuration conventions after full-tree inspection.

On Linux/Docker, prefer two named TEI services/containers. On macOS/native TEI, manage two router processes with separate PID/log files, safe port checks, idempotent startup, and clean shutdown. Runtime PID/log files must be gitignored.

## Quality and reproducibility gates

### Unit tests
Use fixed/injected embeddings to test:
- duplicate theme observations;
- monthly HDBSCAN clusters;
- HDBSCAN noise;
- representative selection;
- deterministic ties;
- multiple source labels from one matched pair;
- pair deduplication;
- missing general themes;
- keyword aggregation;
- Stage-B canonical families;
- Stage-B singleton noise;
- stable IDs;
- artifact serialization/provenance.

### Integration tests
Verify:
- clustering uses `general_theme_names` only;
- no absolute/weighted fallback occurs in clustered reporting;
- API reads artifacts without TEI calls;
- Overview and Thematic Analysis return the same top-theme IDs/ranks for the same run/month;
- raw theme evidence remains available;
- Thematic Analysis makes no Community Continuity/persisted-path requests;
- Community Evolution outputs remain unchanged.

### TEI tests/checks
- `make tei-up` starts both profiles.
- `make tei-check` validates both model endpoints independently.
- `make tei-down` stops both.
- failure of either required service is surfaced clearly.
- tests do not require either TEI service.

### Regression/quality diagnostics
For representative fixtures, record:
- number of raw theme observations;
- monthly cluster count;
- Stage-A noise count/rate;
- canonical family count;
- matched-pair coverage;
- top-five canonical themes;
- output hashes.

Do not require exact equality to historical thesis tables because the thesis included manual standardization and used a different historical notebook workflow. Treat the thesis tables as reference results, not universal golden outputs.

## Documentation

Update:
- active execution plan/progress log;
- pipeline contract;
- theme intelligence contract;
- data/artifact contract if schemas change;
- verification test matrix;
- HARNESS/README/Makefile documentation for dual TEI services if appropriate;
- methodology-facing documentation describing the automated replacement for manual standardization.

Document explicitly:
- general themes are the clustering source;
- monthly HDBSCAN noise policy;
- cross-month canonicalization policy;
- distinct matched-pair counting;
- the two separate TEI model purposes;
- no claim of bit-for-bit historical thesis-table reproduction.

## Implementation sequence

1. Read required repository docs and current active plan(s).
2. Inspect full source tree, current artifact writers, embedding clients, orchestration, TEI launcher, and dashboard consumers.
3. Protect current raw/exact-theme behavior with regression tests.
4. Add multi-profile TEI configuration/start/check/stop support with pinned revisions.
5. Add reusable embedding-profile client abstraction if not already present.
6. Use first-party `sklearn.cluster.HDBSCAN`; remove the standalone `hdbscan` dependency and protect the migration with a stable-partition fixture.
7. Add content-addressed embedding recording/persistence: infer unique exact texts once, expand duplicates before clustering, persist float32 Parquet vectors.
8. Implement monthly clustering with injected embeddings and tests.
9. Implement cross-month canonicalization and tests.
10. Implement matched-pair/keyword aggregation and stable IDs.
11. Publish additive clustered/canonical/embedding artifacts with provenance.
12. Add `make bootstrap` and mandatory real-run `pipeline-preflight` checks.
10. Add read-only clustered-theme API endpoints.
11. Migrate Thematic Analysis to clustered/canonical reporting.
12. Migrate Overview → Top Themes to the same endpoint.
13. Run targeted tests and full available validation gates.
14. Update docs and active-plan progress log.
15. Produce a surgical git patch and validation report.

## Non-negotiable boundaries

Do not:
- change `shared_post` or `weighted_post` behavior;
- change graph filtering, Louvain, or LDA defaults;
- replace LDA with LLM output;
- require OpenAI/GPT calls during automated tests;
- cluster themes in React/the browser;
- call TEI from dashboard request handlers;
- modify Community Evolution continuity/member-mobility semantics;
- remove Telegram support;
- hard-code local absolute paths;
- silently fall back from general themes to IF/WIF themes;
- introduce paid cloud dependencies;
- delete or overwrite raw theme artifacts.

## Acceptance criteria

Plan 039 is complete when:

1. Theme clustering is an upstream reproducible pipeline stage using `general_theme_names`.
2. Clustering embeddings come from TEI `all-MiniLM-L6-v2` on the clustering profile.
3. Existing Community Evolution similarity continues through TEI `paraphrase-MiniLM-L6-v2` on the similarity profile.
4. One `make tei-up` starts both services; check/down handle both.
5. Monthly `sklearn.cluster.HDBSCAN` + deterministic representative selection works without manual review or the standalone `hdbscan` package.
6. Cross-month automated canonicalization replaces manual standardization.
7. Distinct matched IF/WIF pairs are the reporting unit.
8. General LDA keywords remain visible as evidence.
9. Raw theme artifacts remain unchanged and auditable.
10. Overview and Thematic Analysis use the same canonical clustered results.
11. Thematic Analysis remains independent of persisted-community continuity.
12. Community Evolution analytical outputs remain unchanged.
13. Unique embeddings from both semantic profiles are persisted as immutable content-addressed float32 Parquet artifacts when produced; duplicate theme observations still affect HDBSCAN density.
14. Both TEI models pin exact revisions and embedding provenance is manifest-backed.
15. `make bootstrap` and `make pipeline-preflight CONFIG=...` provide the canonical local setup/fail-fast path; the real evolution Make target depends on preflight.
16. Automated tests make no TEI/OpenAI/model-download calls.
17. Relevant repository validation gates pass, or pre-existing/environment blockers are documented precisely.
18. Documentation and active-plan progress are updated.


## Progress log

### 2026-08-07 — Full source inspection

- Treated `community-analysis-full-review-20260807-1710.zip` as the source of truth.
- Read the required harness, architecture, analytical/data/database/metric/pipeline/theme contracts, quality gates, test matrix, and active plans before editing.
- Confirmed the full analytical `src/` tree, TEI client/launcher, artifact system, orchestration, API, frontend, and current Plan 037/038 work were present.

### 2026-08-07 — Implementation

- Added additive two-stage clustering over `general_theme_names` only: monthly HDBSCAN clusters followed by run-local canonical families.
- Added deterministic semantic-medoid representative selection, Stage-A noise evidence, Stage-B singleton canonical themes, distinct matched-pair aggregation, LDA keyword support ranking, stable IDs, and provenance.
- Preserved the generator's multi-theme semantics by reconstructing dot-joined `general_theme_names` only when they round-trip to the corresponding `general_theme_gpt` mapping; per-label mapped LDA keywords are retained, and missing general names never fall back to mapping/IF/WIF labels.
- Reused the existing TEI client abstraction with a new clustering profile on port 8081 while preserving the Community Evolution similarity profile on port 8080.
- Added dual-profile TEI start/check/stop commands.
- Published monthly cluster summaries, observation evidence, and canonical-family artifacts without changing raw theme artifacts or Community Evolution semantics.
- Added read-only clustered-theme API endpoints; request handlers do not import or execute clustering/embedding code.
- Migrated Thematic Analysis and Overview Top Themes to the same canonical clustered read model while retaining raw theme/LDA evidence.
- Kept exact-label trend APIs as compatibility/audit surfaces.
- Initial implementation used `hdbscan.HDBSCAN(prediction_data=True)`; the later ML-infrastructure hardening section supersedes this with the maintained first-party scikit-learn implementation while preserving the analytical density contract explicitly.

### 2026-08-07 — Validation status

- The initial Plan 039 validation passed 42 targeted tests; the later ML-infrastructure hardening validation supersedes the external-`hdbscan` limitation and records the final sklearn/embedding/preflight results.
- Clustering tests explicitly cover dot-joined multi-theme `general_theme_names` reconstruction against `general_theme_gpt`, per-label keyword evidence, missing-general-label exclusion, duplicate occurrence density, pair deduplication, HDBSCAN noise, deterministic medoids, and Stage-B singleton canonical themes.
- Dual-profile TEI launcher shell tests and shell syntax checks pass without starting real model services.
- Cluster artifact schemas exactly match the reporting output contract; API construction exposes all three clustered-theme routes without importing the clustering runtime.
- Protected graph thresholds, Louvain defaults, LDA defaults, and the existing `paraphrase-MiniLM-L6-v2` Community Evolution similarity model remain unchanged.
- Modified Python files compile successfully; 19 changed frontend TypeScript/JavaScript files pass TypeScript syntax transpilation. `git diff --check` and a changed-diff secret/absolute-user-path scan pass.
- Direct full-unit collection is blocked by dependencies absent from the packaged runtime (`kneed`, `mlflow`, `prefect`, `demoji`) plus three pre-existing theme-benchmark import failures; the clean source baseline produces the same 13 collection errors.
- The initial sandbox could not provision the complete frozen environment from its configured registry. The later infrastructure-hardening validation records the final lock/dependency state after removing the standalone `hdbscan` package.
- Full frontend dependency installation is environment-blocked by the configured npm mirror returning HTTP 404 for `yargs-parser-21.1.1.tgz`; canonical frontend typecheck/test/build/lint gates therefore cannot run in this sandbox.
- Real TEI model health/semantic execution was not run because model services are intentionally not present in the review environment; automated tests use injected/fake embeddings as required by the contract.

### 2026-08-07 — macOS TEI launcher compatibility fix

- Fixed `scripts/start_tei.sh` for the system Bash 3.2 shipped with macOS when `set -u` is enabled and no optional TEI batching arguments are configured.
- Removed expansion of potentially empty arrays (`common_args`, `gpu_args`, `env_args`) under nounset mode; native optional arguments are appended directly and Docker command arguments are built in one guaranteed-nonempty command array.
- This is a launcher-only compatibility fix: model IDs, ports, analytical contracts, clustering behavior, and Community Evolution similarity behavior are unchanged.

### 2026-08-07 — ML infrastructure hardening

- Rebased on `community-analysis-full-review-20260807-2031.zip`, the updated full working-tree source of truth after Plan 039 and the macOS TEI launcher fix.
- Migrated the clustering runtime from the standalone `hdbscan` package to first-party `sklearn.cluster.HDBSCAN` and raised the project scikit-learn contract to `>=1.7,<2`; the standalone dependency was removed from `pyproject.toml` and `uv.lock`.
- Bumped monthly-cluster and canonicalization analytical contract versions to `2.0`; pinned explicit sklearn HDBSCAN parameters and translated legacy `min_samples` semantics with `min_samples=min_cluster_size+1`. `prediction_data` is no longer requested because it was unused.
- Added a content-addressed embedding recorder around both TEI semantic profiles. Exact duplicate texts are embedded once per model contract; clustering vectors are expanded back to all source observations before HDBSCAN, and rendered Community Evolution similarity reuses exact-text vectors across heatmap passes. Unique vectors are persisted as fixed-size float32 Parquet with text/vector hashes, model ID/revision, normalization, dtype/dimension, preprocessing, and embedding-contract provenance.
- Registered `theme_embeddings_clustering` and, when similarity rendering is enabled, `theme_embeddings_similarity` as additive canonical run artifacts under `data/themes/embeddings/`; manifests therefore carry immutable SHA-256/row counts like other analytical outputs. No vector database or Memgraph vector storage was introduced.
- Pinned the similarity and clustering Hugging Face revisions independently and kept legacy `TEI_*` similarity settings compatible while preferring explicit `TEI_SIMILARITY_*` variables.
- Added `make bootstrap` for the locked core+orchestration environment and `pipeline-preflight` for fail-fast dependency-lock, sklearn HDBSCAN, input CSV, output writability, live-provider credential, TEI model/revision, and required-service checks. The real `run-evolution-pipeline` Make target now depends on preflight. Memgraph is intentionally not required by the CSV-backed longitudinal path.
- Added regression tests for exact-text embedding inference deduplication versus duplicate observation density, content-addressed revision keys, float32/fixed-size Parquet schema, sklearn HDBSCAN partition behavior, dependency-lock consistency, preflight failures, TEI revision pins, and embedding artifact routing.

- Preserved the documented Python 3.10 floor by adding a conditional direct `tomli` dependency and a `tomllib` fallback for the new preflight lock parser; dependency-marker handling is regression tested.
