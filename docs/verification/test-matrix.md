# Test Matrix

## Required Tests By Feature

| Feature | Current code | Required tests |
|---|---|---|
| Neo4j export CSV | `neo4j_data_fetcher.py` | Query config, output columns, no hard-coded credentials. |
| Creator/spreader split | `get_creator_spreader` | Correct relation filtering. |
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
| Text preprocessing | `message_preprocess` | Emoji removal, HTML cleaning, Unicode normalization, stopword removal. |
| LDA defaults | `get_lda` | Parameters match contract. |
| Unigram LDA | `get_unigram_lda` | Output schema on small corpus. |
| Bigram LDA | `get_bigram_lda` | Bigram token handling and output schema. |
| Keyword cutoff | `get_cutoff_probability` | Knee and fallback behavior. |
| Matched topic export | `get_matched_topic_df` | Absolute/weighted unigram/bigram columns. |
| Theme data loading | `load_prepare_data` | Month sorting and keyword column parsing. |
| GPT theme generation | `generate_gpt_theme` | Mocked provider, JSON parsing, output columns. |
| Month transition | `get_community_transition` | Reply threshold and non-reply threshold. |
| Sankey path info | `get_path_info` | Correct source/target indices. |
| Sankey path detection | `find_all_sankey_paths` | Finds all start-to-end paths. |
| Membership changes | `calculate_membership_changes` | New/lost/existing/reappearing behavior. |
| Theme similarity | `calculate_sentence_similarity` | Matrix shape and similarity bounds. |
| Output artifact contract | `verify_output_contract` | Public CSV schemas, internal manifests, SHA256 hashes, copied LDA schema, optional outputs. |

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
- Download SentenceTransformer models unless marked slow/integration.
- Depend on external drive paths.

Use mocks or cached fixtures for those cases.

## Output Contract Verification

Generated sample outputs should be checked with:

```bash
make run-pipeline-sample
make verify-output-contract
make run-longitudinal-sample
make verify-longitudinal-output-contract
```

The verifier is read-only and must not call database, LLM, model-download, or
visualization services.

## Run Artifact Contract Tests

| Feature | Implementation | Required tests |
|---|---|---|
| Run layout | `src/artifacts/run_manifest.py` | Creates `runs/<run_id>` metadata, intermediate, data, report, and log directories. |
| Manifest models | `src/artifacts/models.py` | Status/category values, relative paths, SHA-256 validation, unique keys. |
| Canonical publication | `complete_run_bundle` | Classifies artifacts and preserves legacy source bytes. |
| Manifest verification | `validate_run_manifest` | Path containment, checksum, byte size, row count, JSON schema version, CSV columns. |
| Atomic lifecycle | `initialize_run_bundle`, `complete_run_bundle`, `fail_run_bundle` | No temporary files remain; failed runs are never completed. |

## Dashboard Data API Tests

| Feature | Implementation | Required tests |
|---|---|---|
| Run discovery and filters | `src/api/services/run_catalog.py` | Platform, content type, year, month, and status filters; no absolute paths in responses. |
| Manifest/artifact validation | `src/api/services/artifact_reader.py` | Invalid manifest, checksum mismatch, schema mismatch, and symlink/path escape. |
| Pagination | Topic, theme, transition, and centrality routers | Stable totals, limits, offsets, and JSON normalization. |
| Bounded graph read model | `src/api/services/network_service.py` | IF/WIF selection, community filtering, sampling, and hard request caps. |
| Evolution read model | `src/api/services/evolution_service.py` | Transitions, persistent components, membership counts, and optional theme-similarity outputs. |
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
| Structural views | network/community/explorer adapters | Graph transform, sampling labels, metric weights, ID preservation, pagination, page-local filtering, downloads. |
| Semantic views | topic/theme adapters | Safe normalization, matched/partial, unigram/bigram, IF/WIF links, provider metadata, similarity fallback. |
| Longitudinal/comparison | evolution/transition/comparison models | Compatible grouping, missing values, config warnings, Sankey model, explicit cross-platform runs. |
| Reports/methodology | artifact library and methodology model | Intermediate suppression, report URL, protected defaults, selected-run overrides, non-OpenAI metadata. |
| Accessibility | Playwright axe and keyboard workflows | Serious/critical axe scan, names/labels, mobile navigation, 200% zoom, 320 CSS pixels. |
| Performance | Vite route chunks and bundle script | Entry under 300 KiB, non-route application chunks under 500 KiB, separate graph/chart vendors. |
| Mock/secret guard | `frontend/src/test/mockDataGuard.test.ts` plus source scans | No old mock IDs/dates/platforms, obsolete routes, secrets, direct provider/database calls, or machine paths in production source. |

Playwright visual baselines are stored beside the visual spec and are updated
only after review. The functional/axe suite must not depend on snapshot
availability.
