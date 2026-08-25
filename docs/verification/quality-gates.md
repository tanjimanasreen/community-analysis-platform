# Quality Gates

Work is complete only when the relevant gates pass.

## Gate 1: Baseline Preservation

Required:

- Current scripts are inventoried.
- Existing output categories are documented.
- A small fixture or sample run is available.
- Current hard-coded parameters are captured in config defaults.

Validation:

```bash
pytest tests/unit/test_current_defaults.py
```

## Gate 2: Configuration And Secrets

Required:

- No database credentials are hard-coded.
- Current graph-repository connection settings are supplied through `GRAPH_DB_*`;
  analytical YAML `database:` sections are rejected instead of ignored.
- No OpenAI API key is hard-coded.
- `.env.example` exists.
- Dataset run config supports Twitter and Telegram parameters.
- Canonical evolution configs are limited to Twitter reply, Twitter retweet/quote,
  and Telegram forwarded-message workflows, with relation/column mappings
  validated before execution.
- External drive paths are replaced by configurable paths.

Validation:

```bash
python -m src.cli validate-config --config configs/sample.yml
```

## Gate 3: Database Export Compatibility

Required:

- Existing `source,target,relation` CSV format is supported.
- Neo4j export can be configured without editing source.
- Memgraph local runtime exists as the current default backend.
- Graph store access is isolated behind `GraphRepository` and backend resolution;
  unsupported configured engines fail explicitly rather than falling through to
  Memgraph.

Validation:

```bash
make db-up
make db-check
pytest tests/integration/test_graph_export_contract.py
```

## Gate 4: Network Metrics

Required:

- `shared_post` calculation is tested.
- `weighted_post = shared_post / total_post` is tested.
- Self-spread exclusion is tested.
- Graph filtering thresholds are tested.
- The shared Telegram network boundary accepts both legacy
  `source,target,relation` rows and already-normalized
  `from_id,forwarder_id` rows before the same IF/WIF implementation runs.

Validation:

```bash
pytest tests/unit/test_follower_followee_metrics.py
pytest tests/unit/test_graph_thresholds.py
pytest tests/unit/test_pipelines.py -k telegram
```

## Gate 5: Community Analysis

Required:

- Louvain defaults are preserved.
- Prominent community filtering is tested.
- Community message extraction is tested.
- Exact and partial community matching are tested.

Validation:

```bash
pytest tests/unit/test_louvain_defaults.py
pytest tests/unit/test_community_similarity.py
```

## Gate 6: LDA Topic Modeling

Required:

- Text preprocessing behavior is tested.
- The approved production `LdaMulticore` defaults are enforced without hidden prior rewriting.
- Unigram and bigram outputs are generated.
- Matched and partially matched topic comparison outputs are generated.
- Perplexity and coherence scores are saved.

Validation:

```bash
pytest tests/unit/test_text_preprocessor.py
pytest tests/unit/test_lda_contract.py
make run-topic-sample
```

## Gate 7: Theme Intelligence

Required:

- GPT theme generation is behind a provider interface.
- Theme generation supports mock/cached mode.
- Prompt V3 is centrally authoritative and requests faithful, descriptive, non-endorsing,
  severity-preserving labels plus explicit request-bounded zero-based keyword IDs; exact keyword
  evidence is reconstructed locally and is never sanitized to satisfy a provider.
- Multiple typed provider safety failures are payload-scoped and recoverable, while unexpected
  errors remain fail-fast; provenance/coverage is persisted and missing labels are never embedded
  as empty strings.
- Provider routing is configured only under `theme_provider`; stale `theme.fallback` and `theme.fallback_chain` settings fail validation instead of being silently ignored.
- Month-to-month transitions require positive member overlap and use the correct thresholds.
- Sankey path detection is tested.
- Membership-change calculation is tested.
- Theme similarity matrix generation is tested.

Validation:

```bash
pytest tests/unit/test_theme_generation_contract.py
pytest tests/unit/test_theme_content_filter_recovery.py
pytest tests/unit/test_config.py tests/unit/test_provider_factory.py
pytest tests/unit/test_community_transition.py
pytest tests/unit/test_membership_changes.py
pytest tests/unit/test_theme_similarity.py
make run-theme-sample
```

## Gate 8: End-To-End Sample

Required:

- Sample network pipeline runs.
- Sample topic pipeline runs.
- Sample theme pipeline runs in offline/mock mode.
- Final report or output index lists all generated artifacts.
- Current operational documentation references only Make targets that exist.

Validation:

```bash
make run-pipeline-sample
pytest tests/unit/test_release_hygiene.py
make test
```

## Gate 9: Run Artifact Contract

Required:

- Orchestrated outputs are isolated below `<output_base_path>/runs/<run_id>`.
- Running, completed, and failed statuses are persisted atomically.
- Canonical artifact records use relative paths and validate containment.
- Checksums, byte sizes, Parquet row counts, and known schemas are verified.
- Generated analytical and intermediate tabular outputs are Parquet; no generated CSV compatibility copy is required.
- Failed runs cannot retain completed status.
- Equivalent runs with different run IDs compute the same stage cache identity.
- Relevant input, configuration, stage-code/runtime, or contract changes invalidate the affected stage cache identity.
- Valid cached artifacts are restored under the current run root; missing, incomplete, or tampered cache entries are treated as misses.
- Prefect task-result caching is not used to reuse older run-scoped artifact references.

Validation:

```bash
pytest tests/unit/test_run_manifest.py
pytest tests/unit/test_stage_artifact_cache.py
pytest tests/unit/test_orchestration_hashing.py
pytest tests/unit/test_orchestration_monthly_flow.py
pytest tests/integration/test_orchestration_smoke.py
```

## Dashboard Data API Gate

- The API discovers only `runs/<run_id>/manifest.json` below the configured
  artifact root.
- Analytical and report files are resolved only through manifest artifact keys.
- Selected artifacts pass path-containment, checksum, size, media-type, and
  schema validation before their contents are returned.
- Table responses enforce pagination and graph responses enforce configured
  node/edge caps.
- API requests do not import or execute pipeline, NetworkX, Louvain, LDA,
  provider, TEI, or visualization-generation modules.
- `python -m pytest tests/unit/test_backend_api.py` passes offline.

## Dashboard Frontend Quality And Release Gate

Required:

- A deterministic canonical fixture is generated through artifact models and
  passes manifest validation.
- Vitest uses exact offline MSW handlers, rejects unhandled requests, and meets
  focused adapter/state/view-model coverage thresholds.
- Playwright starts the real FastAPI API and Vite app against the fixture and
  covers run/metric state, deep links, semantic controls, longitudinal views,
  comparison, reports, integrity failures, mobile navigation, and history.
- Representative routes have axe checks and keyboard/mobile coverage.
- All route pages are lazy and graph/chart vendors are split from the initial
  entry.
- Lint has zero warnings; typecheck, production build, and bundle budget pass.
- Production frontend source contains no obsolete endpoint, analytical mock,
  credential, absolute path, database client, or provider call.

Validation:

```bash
make dashboard-fixture
python -m pytest -q tests/unit/test_dashboard_fixture.py tests/unit/test_backend_api.py
make frontend-check
make frontend-e2e
```

`frontend-e2e` is offline after the Playwright Chromium binary has been
installed. Visual baselines are updated only through the documented reviewed
snapshot command; an absent baseline is an explicit skip and is not evidence of
a passing visual gate.

## Performance Regression Gate

Required:

- Indexed community-message extraction is output-equivalent to the legacy
  reference implementation.
- The synthetic benchmark records a speedup and does not regress to repeated
  full-frame scans.
- IF and WIF extraction reuse one monthly message index.
- Longitudinal defaults avoid nested month-level and `LdaMulticore`
  multiprocessing.
- Memgraph interaction import uses bounded batches.
- Theme generation emits progress and respects configured request concurrency.

Validation:

```bash
make benchmark-performance
python -m pytest -q \
  tests/unit/test_community_messages.py \
  tests/unit/test_memgraph_repository.py \
  tests/unit/test_network_dashboard_sample.py
```

For private full datasets, capture stage duration and peak memory before and
after. Synthetic success is not a substitute for a full-size load run.

## Observability And Optional-Service Gate

Required:

- Text and JSON log formatting work without leaking secrets.
- MLflow code is not imported or invoked when tracking is disabled.
- OpenAI usage values are captured when present in the provider response.
- TEI requests are batched and validated.
- TEI failure is terminal for real similarity runs; mock fallback is explicit.
- Disabled visualization stages log `skipped` rather than misleading work
  messages.

Validation:

```bash
python -m pytest -q \
  tests/unit/test_logging_config.py \
  tests/unit/test_openai_usage.py \
  tests/unit/test_tei_client.py \
  tests/unit/test_tracking_summaries.py
```

## Container And AWS-Readiness Gate

Required before starting the CDK plan:

- Frozen dependency install succeeds.
- The wheel imports in a clean environment.
- The container builds without editable installs and runs as a non-root user.
- Configuration, secrets, log format, artifact root, cache root, and service
  endpoints are environment driven.
- `/api/v1/health` and readiness behavior work in the container.
- Pipeline and API processes share only the configured artifact boundary.
- Documentation accurately states that EFS/filesystem is supported now and
  direct S3 requires a future adapter.

- The container imports and loads the pinned `en_core_web_sm` model.
- The API caches only artifacts below the configured byte threshold and rejects
  duplicate run IDs.
- Optional DeepEval imports do not affect normal pipeline/CLI imports.

Validation:

```bash
uv sync --frozen --extra orchestration --extra tracking
python -m build
docker build -t community-analysis:local .
docker run --rm community-analysis:local --help
make test
make frontend-check
```

## Dashboard Production Hardening Gate

Before dashboard/AWS handoff:

```bash
python -m pytest -q tests/unit/test_backend_api.py
make frontend-check
make frontend-e2e

docker build -f Dockerfile.api -t community-analysis-api:local .
docker build -f frontend/Dockerfile -t community-analysis-frontend:local frontend
```

The graph gate must use a real completed run bundle and confirm a non-empty
canvas, bounded node/edge counts, IF/WIF switching, resize, and fullscreen. API
responses must include `X-Request-ID`, security headers, and a successful
`/api/v1/ready` response when the artifact root is mounted. Artifact values must
remain data: the browser may parse JSON but must never evaluate serialized text.

## Multilingual Translation Gate
- No automated test may call Azure Translator, Amazon Comprehend, or Amazon Translate live.
- A complete per-message translation-cache hit must not construct a cloud provider.
- Original community-message dataframes/artifacts must remain unchanged.
- Azure↔AWS or translation-contract changes must invalidate topic cache identity; cache path/timeout changes must not.
- Translation provenance must be included in topic-stage artifact reuse and final run-manifest validation.

### Translation preflight gate
- The translation workload planner must not construct a cloud provider or create an empty SQLite cache merely to report zero cache hits.
- `translation-preflight` must stop before LDA/theme/provider execution and report exact cache misses at the post-community, pre-LDA boundary.
- Azure/AWS language-detection request estimates must match the batching logic used by the corresponding provider adapter.
- `translation-detect` must call language detection only, persist reusable detection results, never call a translation endpoint, and report the exact remaining provider translation-request count.
- A subsequent full translation run must reuse cached detections and must not repeat detection for those texts.
- Azure `/detect` results with `isTranslationSupported=false` must never be passed to LDA unchanged; the full translation path may retry them through `/translate` source auto-detection, must cache successful fallback output, and must fail explicitly for unresolved/oversized inputs.
- Detection-only planning must include Azure auto-detect fallback requests in its exact request count and persist a message-level issue audit without calling `/translate`.

## Monthly Theme Stage-A Benchmark Gate
- Benchmark input must be persisted clean Stage-A evidence plus the run's recorded clustering embedding artifact; no TEI/provider inference or production artifact mutation is allowed.
- Before any candidate runs, the frozen contract-`2.2` raw-Euclidean/EOM/`min_samples=3` baseline must reproduce persisted period-by-period noise membership and non-noise partition exactly, with membership probabilities matching within rounding tolerance and production-reconstructed monthly cluster IDs/representatives matching persisted evidence; baseline mismatch aborts the benchmark.
- Pre-Plan-085 monthly clustering contracts must be rejected so serialization-corrupted evidence cannot be used as a promotion baseline.
- The main grid must keep `min_cluster_size=2` fixed and vary only raw/unit-Euclidean/cosine geometry, EOM/leaf selection, and sklearn-inclusive `min_samples` 3/2. The `allow_single_cluster=true` control is diagnostic-only and must be marked as such.
- Output must preserve duplicate observation multiplicity and include period-level noise/concentration, embedding-neighbour geometry, cluster-level cosine cohesion, semantic-medoid cohesion, fragmentation, full observation membership, and exact recorded-embedding fingerprints/group sizes.
- Within one period, an exact recorded embedding assigned to more than one non-noise cluster is a promotion-gate failure and must be counted at period and corpus level. A duplicate embedding split only across noise versus one non-noise cluster is a separate boundary diagnostic and does not by itself fail the non-noise consistency gate.
- Candidate Stage-A clusters must be audited through the unchanged production Stage-B representative + cosine complete-linkage `0.65` contract; this is an impact diagnostic, not a Stage-B benchmark/default change.
- No automatic winner is permitted. Production Stage-A changes require manual semantic review and clean cross-platform evidence rather than a Telegram-only score.

## Production Monthly Theme Stage-A Gate
- Production monthly clustering contract `3.0` must keep the recorded clustering embedding artifact raw/unnormalized while creating a separate in-memory L2-normalized matrix for HDBSCAN.
- Production HDBSCAN must use Euclidean distance, `cluster_selection_method="leaf"`, default `min_cluster_size=2`, sklearn-inclusive default `min_samples=3`, and `allow_single_cluster=false`.
- Stage-A summary/evidence/family artifacts must persist `clustering_input_normalized`, effective `hdbscan_min_samples`, `hdbscan_cluster_selection_method`, and `hdbscan_allow_single_cluster` without changing `embedding_normalized=false` for the recorded artifact.
- Production Stage-A labels/probabilities must match the Plan-086 `unit_euclidean_leaf_ms3` candidate for the same raw matrix.
- Zero/non-finite vectors must fail before normalization/HDBSCAN rather than producing undefined geometry.
- Theme-stage cache contract `3.0.0` must prevent reuse of contract-`2.2` Stage-A artifacts and include the promoted normalization/selection policy in cache identity.
- Stage-B canonicalization remains contract `4.0`; no Stage-A promotion may change the representative + cosine complete-linkage `0.65` method.

Validation:

```bash
python -m pytest -q tests/unit/test_monthly_cluster_benchmark.py tests/unit/test_theme_clustering.py
```

## Canonical Theme Stage-B Benchmark Gate
- Benchmark input must come from persisted non-noise monthly-cluster evidence plus the run's recorded clustering embedding artifact; no TEI/provider inference is allowed.
- The baseline benchmark variant must reproduce the current Stage-B HDBSCAN partition for the same embedding matrix.
- Candidate benchmarking must not mutate production canonicalization configuration or run artifacts.
- Constituent-mean candidates must reconstruct monthly-cluster vectors from every persisted non-noise evidence occurrence using exact recorded source-label embeddings; duplicate observations must not be collapsed before averaging.
- Raw and L2-normalized constituent means must be compared under the existing Euclidean Stage-B density settings so representation changes are isolated from parameter changes.
- Plan-081 grouping candidates must keep the normalized constituent centroid fixed, vary HDBSCAN `min_samples` independently without changing production defaults, and evaluate average/complete-linkage cosine thresholds at the documented fixed grid.
- Agglomerative singleton groups must be represented as benchmark singleton noise; complete-linkage threshold runs must expose the configured similarity/distance threshold in the summary so family cohesion can be audited directly.
- Plan-083 representation candidates must keep cosine complete linkage fixed and compare the recorded monthly representative, occurrence-weighted constituent mean, individually normalized constituent mean, HDBSCAN-membership-probability-weighted constituent mean, and exact-unique-label constituent mean at similarity thresholds 0.60 through 0.80.
- Probability-weighted reconstruction must use persisted monthly HDBSCAN `membership_probability` values and fail explicitly on missing, negative, non-finite, or zero-total weights; no fallback weighting is allowed.
- Benchmark output must include monthly-cluster internal cohesion, representative-to-centroid agreement, representative-space within-family cohesion, observation-weighted largest-family concentration, representation/grouping provenance, constituent evidence counts, and full monthly-cluster membership for semantic review before any production default change is approved.
- Regression coverage must include a centroid-collapse fixture where two heterogeneous monthly clusters merge in centroid space while their recorded representatives remain below the configured similarity threshold; representative-space diagnostics must expose that false merge.

Validation:

```bash
python -m pytest -q tests/unit/test_canonical_theme_benchmark.py tests/unit/test_theme_clustering.py
```

## Production Canonical Theme Stage-B Gate
- Production canonicalization contract `4.0` must reuse the already-produced embedding of each monthly cluster's deterministic semantic medoid/representative and L2-normalize that vector; production Stage B must not average constituent embeddings.
- Stage B must use cosine-distance agglomerative clustering with complete linkage and similarity threshold `0.65` (`distance_threshold=0.35`); Stage B must not alter the independently versioned monthly Stage-A contract.
- Complete-linkage regression coverage must demonstrate that bridge/chaining points cannot force a canonical family whose furthest pair falls below the threshold.
- Stage-B size-one groups must remain valid singleton canonical themes. `stage_b_hdbscan_label` must be null for contract `4.0`, while a generic Stage-B cluster label and full grouping provenance are persisted.
- Stage B must not issue a second embedding request for monthly representative labels. A representative missing from its own constituent observations, or mapping to inconsistent recorded vectors, must fail explicitly rather than re-embed or fall back to a centroid.
- Canonical labels must remain existing monthly representatives selected by deterministic semantic medoid over the normalized monthly representative vectors.
- The production partition must match the approved Plan-083 representative + complete-linkage cosine-0.65 benchmark candidate when both receive the same normalized representative matrix.
- Theme-stage cache identity must change across canonicalization contract revisions so contract-3.0 artifacts cannot be restored as contract-4.0 outputs.

## General Theme Serialization Gate
- `general_theme_names` must never be split on commas merely because it is a scalar string; comma-bearing production labels must remain atomic observations.
- Native list/tuple and JSON/Python serialized list forms must preserve commas inside individual items.
- Exact legacy dot-joined reconstruction must compare the raw saved scalar with `".".join(general_theme_gpt.keys())` before any generic list fallback can alter the value, and recovered labels must retain their own mapped LDA keyword evidence.
- Missing `general_theme_names` must not be rescued from `general_theme_gpt`; ambiguous dot-joined values with absent/mismatched mappings must remain excluded and diagnosed, while abbreviation punctuation such as `U.S. Immigration Policy` remains valid.
- Plan-085 serialization contract `2.2` and theme-stage cache version `2.3.0` invalidated pre-repair Stage-A artifacts. Plan 087 supersedes production monthly clustering with contract `3.0` and theme-stage cache version `3.0.0`; the cache key must continue to include the monthly clustering contract.
- Plan 085 itself does not change HDBSCAN parameters, Stage-B canonicalization contract `4.0`, IF/WIF metrics, Louvain, LDA, translation, provider behavior, or output categories. The later Plan-087 Stage-A promotion is independently versioned and tested.
