# Test Matrix

## Required Tests By Feature

| Feature | Current code | Required tests |
|---|---|---|
| Neo4j export CSV | `neo4j_data_fetcher.py` | Query config, output columns, no hard-coded credentials. |
| Graph database configuration | `DatabaseSettings`, `get_database_config`, `create_graph_repository` | `GRAPH_DB_*` environment values/default Memgraph are honored; analytical YAML `database:` is rejected; unsupported engines fail explicitly instead of constructing Memgraph. |
| Creator/spreader split | `get_creator_spreader` | Correct relation filtering. |
| Canonical evolution config mapping | `configs/*/*_evolution.yml`, `validate_canonical_raw_mapping` | Twitter reply, Twitter retweet/quote, and Telegram forward mappings resolve exactly; contradictory relation/column mappings fail before execution. |
| Telegram network input boundary | `normalize_network_input`, `run_network_phase` | Raw `source,target,relation` and normalized `from_id,forwarder_id` inputs converge at the shared network boundary; raw forwarding rows produce unchanged IF/WIF metrics; invalid shapes fail clearly; orchestration delegates normalization to the shared pipeline. |
| User dataframe | `create_user_df` | Unique users, anonymous username normalization. |
| Neo4j datetime conversion | `convert_neo4j_datetime_strings` | Converts string pattern safely. |
| Network dataframe parsing | `create_network_df` | Parses stringified node dictionaries. |
| Follower-followee edges | `get_follower_followee_network` | `shared_post`, `total_post`, `weighted_post`, self-exclusion. |
| Graph construction | `get_network_graph` | Threshold filtering and `MultiDiGraph` output. |
| Centrality summaries | `show_hightest_out_degree`, `show_hightest_in_degree` | Max/min/average values on small graph. |
| Louvain communities | `get_louvain_community` | Uses stable seed and weight column. |
| Prominent community filter | `detect_promiment_communities` | Filters by `min_members`. |
| Community messages | `get_community_messages` | Aggregates messages, IDs, and counts. |
| Daily message stats | `get_overall_community_messages_stat` | Min/max/avg/std by day. |
| Community matching | `find_matching_communities` | Exact, partial, unmatched cases. |
| Language detection | `lang_detection` | URL removal, English flag, empty text behavior. |
| Translation | `lang_translate` | Mock translator, non-English update behavior. |
| Cached multilingual translation | `src/text/translation.py`, `translation-detect` | Persistent cache reuse, Azure/AWS provider isolation, detection-only planning, Azure unsupported-detection auto-translate fallback without `from`, no untranslated foreign pass-through, exact fallback request counts, issue audit, and explicit oversized-input failure; no live cloud calls. |
| Text preprocessing | `message_preprocess` | Emoji removal, HTML cleaning, Unicode normalization, stopword removal. |
| LDA defaults | `get_lda` | `LdaMulticore` receives the approved defaults exactly; `eta="auto"` is preserved, `alpha="auto"` is rejected, and default worker selection remains implicit. |
| Unigram LDA | `get_unigram_lda` | Output schema on small corpus. |
| Bigram LDA | `get_bigram_lda` | Bigram token handling and output schema. |
| Keyword cutoff | `get_cutoff_probability` | Knee and fallback behavior. |
| Matched topic export | `get_matched_topic_df` | Absolute/weighted unigram/bigram columns. |
| Theme data loading | `load_prepare_data` | Month sorting and keyword column parsing. |
| GPT theme generation | `generate_gpt_theme` | Mocked provider, V2 theme-name + keyword-index wire schema, exact local keyword reconstruction, output columns, multi-filter payload recovery, provenance, unchanged known input hash, and fail-fast unexpected errors. |
| Theme provider config contract | `validate_run_config`, `build_theme_provider` | Canonical `theme_provider.fallback` / `fallback_chain` remain valid; stale provider-routing keys under `theme` fail clearly; analytical `theme` settings remain valid; mock-only factory routing tests make no network calls. |
| Month transition | `get_community_transition` | Zero overlap excluded at reply threshold `0.0`; positive overlap accepted for reply; exact `0.5` accepted and below `0.5` rejected for non-reply. |
| Sankey path info | `get_path_info` | Correct source/target indices. |
| Sankey path detection | `find_all_sankey_paths` | Finds all start-to-end paths. |
| Membership changes | `calculate_membership_changes` | New/lost/existing/reappearing behavior. |
| Theme similarity | `calculate_sentence_similarity` | Matrix shape and similarity bounds; missing generated labels produce null/gap comparisons and are never sent to the embedder as empty strings. |
| Output artifact contract | `verify_output_contract` | Generated Parquet paths/schemas, no CSV suffix fallback, internal manifests, SHA256 hashes, copied LDA schema, optional outputs, and canonical platform/content timestamp validation (`forwarded_date` for Telegram forwarding; `created_at` for Twitter workflows). |
| Operational Make targets | `Makefile`, current operational docs | `tests/unit/test_release_hygiene.py` verifies documented `make <target>` commands resolve and current docs use canonical evolution target names. |
| Provider environment settings | `src/config/settings.py` | `ProviderSettings` reads current-working-directory `.env` values, exported environment values take precedence, and settings loading does not require a CLI-specific dotenv helper or mutate the process environment. |

## Fixture Strategy

Create tiny fixtures:

- 4 users.
- 2 months.
- 2 content types: `reply` and non-`reply`.
- One exact absolute/weighted community match.
- One partial absolute/weighted community match.
- One unmatched community.
- One self-spread row to verify exclusion.
- Enough repeated rows to test graph thresholds.

## No-Network Test Rules

Unit tests must not:

- Call Neo4j.
- Call Memgraph unless marked integration.
- Call OpenAI.
- Download TEI models unless marked slow/integration.
- Depend on external drive paths.

Use mocks or cached fixtures for those cases.

## Output Contract Verification

Generated sample outputs should be checked with:

```bash
make run-pipeline-sample
make verify-output-contract
make run-evolution-pipeline-test
make verify-evolution-output-contract
```

The verifier is read-only and must not call database, LLM, model-download, or
visualization services.

## Run Artifact Contract Tests

| Feature | Implementation | Required tests |
|---|---|---|
| Run layout | `src/artifacts/run_manifest.py` | Creates `runs/<run_id>` metadata, intermediate, data, report, and log directories. |
| Manifest models | `src/artifacts/models.py` | Status/category values, relative paths, SHA-256 validation, unique keys. |
| Canonical publication | `complete_run_bundle` | Classifies generated Parquet artifacts and preserves source bytes during publication. |
| Manifest verification | `validate_run_manifest` | Path containment, checksum, byte size, row count, JSON schema version, and known tabular schemas. |
| Atomic lifecycle | `initialize_run_bundle`, `complete_run_bundle`, `fail_run_bundle` | No temporary files remain; failed runs are never completed. |

## Dashboard Data API Tests

| Feature | Implementation | Required tests |
|---|---|---|
| Run discovery and filters | `src/api/services/run_catalog.py` | Platform, content type, year, month, and status filters; no absolute paths in responses. |
| Manifest/artifact validation | `src/api/services/artifact_reader.py` | Invalid manifest, checksum mismatch, schema mismatch, and symlink/path escape. |
| Pagination | Topic, theme, transition, and centrality routers | Stable totals, limits, offsets, and JSON normalization. |
| Bounded graph read model | `src/api/services/network_service.py` | IF/WIF selection, community filtering, sampling, and hard request caps. |
| Evolution read model | `src/themes/community_paths.py`, `src/api/services/evolution_service.py` | Branching start-to-end DFS paths, deterministic IDs/order, artifact-only API reads, resolved reply/non-reply thresholds, NumPy-backed member IDs serialized as parseable native scalars, path mobility including reappearing members, and path-scoped general/IF/WIF similarity matrices. |
| Report/download serving | `src/api/routers/reports.py` | Manifest-only file resolution and no intermediate downloads. |
| OpenAPI/error contract | `src/api/app.py`, `src/api/errors.py` | Stable route set and structured error envelopes. |
| Analytical isolation | API test suite | Pipeline/model/NetworkX modules remain unimported during requests. |

## Dashboard Frontend Quality Matrix

| Feature | Implementation | Required tests |
|---|---|---|
| Canonical dashboard fixture | `scripts/build_dashboard_fixture.py` | Valid completed runs, compatible history, sampled graph, no runs, missing optional artifact, empty table, tampered checksum. |
| API contract and errors | `frontend/src/api/`, MSW handlers | Exact routes/query names, structured errors, no unhandled request. |
| URL/global state | `DashboardProvider`, search-param adapters | Default completed run, invalid recovery, reload, back/forward, IF/WIF switching. |
| Request/integrity states | shared state components | Loading, API error, no runs, empty records, optional artifact unavailable, failed verification. |
| Structural views | unified Communities workspace plus Overview adapters | Period-aware `(run, period, metric, community_id)` identity, latest-month default, partition-change selection reset, directory pagination without fake global rank, selected-community graph coverage/min-weight isolation, LDA-before-theme preview, legacy route redirects, structural deep links, graph transform, metric weights, and ID preservation. |
| Semantic views | topic/theme adapters | Safe normalization, matched/partial, unigram/bigram, IF/WIF links, provider metadata, similarity fallback. |
| Longitudinal/comparison | Community Evolution page/models plus comparison models | All-path-first master view, run-level-only overview KPIs, one URL-backed path shared by structural/mobility/theme/evidence detail, synchronized path row/dropdown selection, invalid-path recovery, right sticky section rail/mobile jump control, reappearing-member display, General/IF/WIF similarity switch, missing optional artifacts, legacy `/transitions` redirect, compatible run history/comparison behavior. |
| Data & Reports workspace | `Evidence.jsx`, evidence model/hook/components, artifact library | URL-backed thesis-dimension views with a two-level horizontal dimension/data-view navigator; latest-period resolution; communities/centrality period+metric scope; matched/partial LDA/themes period+exact-community scope; transitions/outputs free of false single-month/metric scope; period-preserving community links; constructive centrality leaders; safe normalized record details; report URL; manifest-key downloads; intermediate suppression; canonical `/data-reports` routing plus `/evidence`, `/data`, and `/reports` compatibility redirects. |
| Methodology | methodology content/model and Methodology page | Five-section visual hierarchy, exact thesis RQs, shared foundation plus Structural/Semantic/Temporal workflow branches, embedded RQ traceability, LDA-before-theme interpretation, semantic→temporal theme-similarity dependency, Telegram/Retweet-Quote/Reply relationship diagrams, common creator→spreader projection, layered system implementation, search-param-preserving RQ links, protected defaults, selected-run overrides, non-OpenAI metadata, right section rail/mobile jump control, responsive no-overflow behavior, and keyboard-accessible tabs. |
| Accessibility | Playwright axe and keyboard workflows | Serious/critical axe scan, names/labels, mobile navigation, 200% zoom, 320 CSS pixels. |
| Performance | Vite route chunks and bundle script | Entry under 300 KiB, non-route application chunks under 500 KiB, separate graph/chart vendors. |
| Mock/secret guard | `frontend/src/test/mockDataGuard.test.ts` plus source scans | No old mock IDs/dates/platforms, obsolete routes, secrets, direct provider/database calls, or machine paths in production source. |

Playwright visual baselines are stored beside the visual spec and are updated
only after review. The functional/axe suite must not depend on snapshot
availability.

## Performance And Operations Test Matrix

| Feature | Implementation | Required tests |
|---|---|---|
| Indexed community messages | `CommunityMessageIndex` | Exact legacy equivalence; message order; duplicates; translated text; anonymous users; empty communities; dates. |
| Community message benchmark | `scripts/benchmark_community_messages.py` | Fails on output mismatch; reports legacy/indexed duration and scan counts. |
| Parser reuse | `src/pipelines/ingestion_pipeline.py`, `src/ingestion/network_data_extractor.py` | Repeated serialized nodes are parsed once without changing rows. |
| Memgraph batching | `MemgraphRepository.import_interactions` | Self-edge exclusion, metric preservation, and configured batch boundaries. |
| Text preprocessing batching | `message_preprocess` | Output equivalence to the frozen preprocessing sequence. |
| Topic runtime settings | `src/topics/lda.py` | `LdaMulticore` retained; implementation metadata is not forwarded to Gensim, configured parameters are forwarded unchanged, explicit workers are honored, default workers remain implicit, and empty corpus is rejected. |
| Stage artifact reuse + semantic keys | `src/orchestration/hashing.py`, `src/orchestration/stage_cache.py` | Equivalent run IDs produce the same key; relevant input/config/code/runtime/contract changes invalidate; unrelated reuse metadata is excluded; valid immutable cache entries restore into the current run; missing/tampered entries are misses; Prefect result caching is not used for cross-run run-scoped paths. |
| Theme progress/cache metrics | `src/themes/theme_generation.py` | Completed totals, cache hits/misses, outbound requests, and no external calls in tests. |
| OpenAI usage and structured output | `src/providers/openai.py` | Mapping/object token usage including reasoning tokens, Prompt V3 with explicit zero-based IDs, request-bounded strict V2 JSON Schema (`name` + `keyword_indices`), exact keyword reconstruction, 32K→64K bounded budget escalation, low reasoning effort, one bounded content-filter retry, typed terminal prompt/completion filter or refusal outcomes, Azure `model_extra.content_filters` annotation parsing, safe diagnostic logs, and no live calls. |
| Offline mock providers | `src/providers/mock.py` | Deterministic theme output and token metadata without tokenizer downloads or any network access. |
| TEI batching/failure | `src/themes/tei_client.py`, `theme_similarity.py` | Session reuse, batch cardinality, malformed response, fail policy, explicit mock. |
| Structured logs | `src/logging_config.py` | Text/JSON output and structured fields. |
| Dashboard read models | network pipeline/API service | Summary/sample/node index generation, exact multi-month node totals, bounded graph reads. |
| API bounded dataframe cache | `ArtifactReader` | Small Parquet artifacts are cached; large artifacts bypass the dataframe LRU. |
| Run catalog uniqueness | `RunCatalog` | Duplicate run IDs fail discovery with a diagnostic error. |
| DeepEval optional adapter | `deepeval_judge.py` | Lazy optional imports, score scaling, schema validation, dataset filtering, and offline helper tests. |
| spaCy container model | `Dockerfile`, topic smoke | Pinned model wheel imports and loads in the built image. |
| Artifact month routing and network schema | `src/artifacts/run_manifest.py` | Numeric, abbreviated, and full month suffixes map to correct base schema/path; manifest validation resolves `network_data` timestamp requirements from the persisted canonical run configuration, accepting Telegram `forwarded_date` while preserving Twitter `created_at`. |
| Container smoke | `Dockerfile` | Frozen install, non-root execution, CLI import/help, writable configured output. |

## Dashboard Production Hardening Matrix

| Feature | Implementation | Required tests |
|---|---|---|
| Stable graph canvas | `NetworkGraph.jsx`, `networkModel.ts` | Width-only resize observation, fixed height, deterministic positions, malformed endpoint omission, parallel-edge curvature, metric/remount behavior. |
| Heterogeneous artifact rendering | `ArtifactValue.tsx`, Evidence and metadata panels | JSON arrays/maps, scalars, long text, ordinary text, no evaluation, compact and expanded views. |
| API operational boundary | `src/api/app.py`, `ApiSettings` | Request ID propagation, security headers, gzip configuration, trusted-host configuration, liveness, readiness success/failure. |
| AWS container boundary | `Dockerfile.api`, frontend nginx | Non-root API process, environment-based artifact root, health endpoint, same-origin proxy, immutable assets, SPA fallback. |

## Matched-Community Theme Trend Matrix

| Feature | Implementation | Required tests |
|---|---|---|
| Complete monthly trend aggregation | `src/api/services/theme_trend_service.py` | Distinct pair denominator, duplicate rows, multi-label pairs, general precedence, IF/WIF fallback, missing IDs, >500 source rows, stable keyword order. |
| Exact-label timeline | `ThemeTrendService.timeline` | Year-boundary ordering, zero-filled series, exact-label separation, deterministic leader tie-breaks, invalid/empty ranges. |
| Period/exact-label evidence reads | `TopicService`, theme router | Canonical period selection, exact case-sensitive filtering before pagination, totals and unavailable artifacts. |
| Aggregate matched-theme progression | `themeTrendModel.ts`, `MonthlyThemeMatrix.tsx`, `AggregateThemeProgression.tsx` | Sparse 0–5 canonical-theme selection per month, deterministic rank movement by canonical ID, adjacent-month continuity, gap breaking, re-entry markers, fixed readable month columns, one/long timeline geometry, local horizontal scrolling, full-label accessibility, dynamic rank guides, and accessible companion table. |
| Thematic Analysis route | `ThematicAnalysis.jsx` and components | Methodology overview before results, shared sticky navigation rail/mobile section jump, timeline range URL state, sparse canonical top-theme rankings and LDA keywords, aggregate progression, selected canonical-cluster evidence separated from month/community-scoped source evidence, Token Representation scoped to LDA presentation, compact provider provenance with collapsed raw run metrics, loading/empty/error/unavailable states, and no transition/similarity requests or persisted-path UI. |
| Four-month dashboard fixture | `scripts/build_dashboard_fixture.py` | Four period-specific theme/topic/community artifacts plus deterministic cluster artifacts and Community Evolution path/mobility/similarity read models, including a leave-and-reappear member, pinned evolution similarity provenance, a long-but-valid canonical theme/keyword layout case, and valid manifest. |


## Canonical General-Theme Clustering

| Feature | Implementation | Required tests |
|---|---|---|
| Monthly semantic clustering | `src/themes/theme_clustering.py` | General-only source, injected raw embeddings, occurrence density, tuple keyword normalization, comma-bearing scalar-label atomicity, native/serialized list preservation, verified raw dot-joined mapping round-trip with per-label keyword evidence, ambiguous legacy serialization exclusion/diagnostic, missing-name non-recovery, abbreviation safety, raw-artifact preservation plus in-memory L2-normalized Stage-A input, Euclidean leaf HDBSCAN with default sklearn-inclusive `min_samples=3`, zero-vector rejection, explicit Stage-A provenance, deterministic medoid on recorded vectors, stable IDs, no IF/WIF fallback. |
| Cross-month canonicalization | `src/themes/theme_clustering.py` | Existing monthly semantic-medoid vector reuse, L2 normalization, explicit missing/inconsistent representative-vector failure, cosine complete-linkage threshold `0.65`, bridge prevention, singleton canonical themes, deterministic medoid labels/IDs, no representative re-embedding or centroid fallback, nullable legacy HDBSCAN label, period/run isolation. |
| Matched-pair and keyword aggregation | `src/themes/theme_clustering.py` | Pair deduplication, multi-label merge, denominator, keyword support ordering, missing-general diagnostics. |
| Embedding recorder/store | `src/themes/embedding_store.py` | Exact-text inference deduplication, duplicate-observation expansion, revision-aware content keys, float32/fixed-size Parquet schema, empty artifact; clustering and rendered similarity artifacts share the same storage contract while retaining separate profiles. |
| Cluster artifact routing/schema | `src/reporting/output_contract.py`, `src/artifacts/run_manifest.py` | Summary/evidence/family/embedding required columns, hashes, and canonical manifest paths. |
| Read-only clustered-theme API | `ThemeClusterService`, theme router | Monthly/timeline/evidence normalization, deterministic leader, API route contract, no analytical imports or TEI calls. |
| Shared dashboard reporting | `TopThemesPanel.tsx`, `ThematicAnalysis.jsx` | Overview/Thematic Analysis use canonical IDs and the same monthly server result; ambiguous serialization diagnostics are surfaced; long valid labels/keywords remain layout-bounded without altering underlying text; raw evidence remains available. |
| Dual TEI profiles | `scripts/start_tei.sh`, `scripts/check_tei.py`, `scripts/stop_tei.sh` | One command starts both models, independent ports/models/revisions, legacy similarity env compatibility, secret-safe launch, both health checks. |
| Pipeline preflight | `src/preflight.py`, `src/cli.py`, `Makefile` | Lock/direct-dependency agreement, sklearn HDBSCAN availability, missing inputs, provider credentials, output writability, required TEI contract/service checks, no Memgraph requirement for CSV-backed evolution. |

| Multilingual translation | `tests/unit/test_translation.py`, `tests/unit/test_config.py`, `tests/unit/test_orchestration_hashing.py` | exact-message dedup/cache reuse, Azure/AWS provider adapters with fakes, source preservation, provider/version cache invalidation, canonical Telegram-on/Twitter-off configuration |

| Translation workload preflight | `src/text/translation.py`, `src/cli.py`, `Makefile` | cloud-free cache inspection, no empty-cache side effect, Azure/AWS detection batch counts, translation request range, item-limit warning |
| Translation detection-only preflight | `src/text/translation.py`, `src/cli.py`, `Makefile` | Azure `/detect`/AWS Comprehend only, persistent detection cache reuse, target-language no-translation promotion, exact post-detection translation request count, no live cloud calls in tests |

| Monthly Stage-A robustness benchmark | `src/themes/monthly_cluster_benchmark.py`, `src/cli.py`, `Makefile` | Run-local/published input-layout compatibility, exact recorded-vector occurrence expansion, frozen contract-2.2 raw-Euclidean/EOM baseline partition/noise/probability/stable-ID/representative fidelity and fail-fast mismatch, 12-variant geometry/selection/density grid, diagnostic-only single-cluster control, all-noise reporting, EOM-vs-leaf hierarchy fixture, norm-sensitive geometry fixture, nearest-neighbour diagnostics, independent cosine cluster/medoid cohesion, fragmentation metrics, exact recorded-embedding fingerprint/group-size membership audit, duplicate-vector non-noise split promotion gate with separate noise-boundary diagnostic, full observation membership, fixed Stage-B impact audit, four CSV outputs, pre-Plan-085 evidence rejection, no TEI/LLM/provider calls. |
| Production/benchmark Stage-A parity | `src/themes/theme_clustering.py`, `src/themes/monthly_cluster_benchmark.py` | Production contract `3.0` unit-Euclidean/leaf/default-ms3 labels and membership probabilities match the Plan-086 `unit_euclidean_leaf_ms3` candidate for the same raw matrix; raw recorded embeddings remain unnormalized and zero vectors fail before normalization. |
| Canonical Stage-B benchmark | `src/themes/canonical_benchmark.py`, `src/cli.py` | Published `data/themes/` and run-local `theme_clusters/` input-layout compatibility, persisted monthly-cluster deduplication, exact recorded-vector alignment, current Stage-B baseline fidelity, normalized-Euclidean/cosine candidate execution, occurrence-weighted constituent-mean reconstruction, raw/normalized centroid comparison, independent HDBSCAN `min_samples`, historical average/complete-linkage cosine threshold grid, Plan-083 fixed-complete-linkage representation grid (representative, constituent mean, unit-constituent mean, membership-probability-weighted mean, unique-label mean), singleton-noise normalization, monthly-cluster cohesion, representative-space family cohesion, observation-weighted largest-family concentration, centroid-collapse regression, no TEI/LLM calls, no production-default mutation. |
| Production/benchmark Stage-B parity | `src/themes/theme_clustering.py`, `src/themes/canonical_benchmark.py` | Production canonicalization partition equals the approved Plan-083 monthly-representative complete-linkage cosine-0.65 benchmark candidate for the same normalized representative matrix; contract-version cache invalidation is enforced. |
| Theme-stage clustering/cache invalidation | `src/orchestration/hashing.py`, `tests/unit/test_orchestration_hashing.py` | Theme cache key explicitly includes monthly clustering contract plus Stage-A normalization/effective-min-samples/selection/single-cluster policy; `2.2 -> 3.0` changes identity independently of Stage-B contract `4.0`, and theme-stage semantic version `3.0.0` prevents reuse of pre-promotion artifacts. |
