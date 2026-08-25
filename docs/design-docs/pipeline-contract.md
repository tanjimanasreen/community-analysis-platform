# Pipeline Contract

## Full Current Pipeline

The production rebuild must cover this full sequence:

1. Configure dataset run.
2. Export graph relationships from Neo4j/Memgraph or load an existing relationship CSV.
3. Split creator and spreader relationships.
4. Build user dataframe.
5. Build normalized network dataframe.
6. Detect or translate language where configured.
7. Build follower-followee edges.
8. Build absolute and weighted NetworkX graphs.
9. Run Louvain community detection.
10. Filter prominent communities.
11. Extract community edge and message details.
12. Compute centrality summaries.
13. Compute user/message count summaries.
14. Compute daily message statistics.
15. Compare absolute and weighted communities.
16. Preprocess community text.
17. Run unigram LDA.
18. Run bigram/trigram LDA.
19. Save LDA scores.
20. Export matched and partially matched LDA topic comparisons.
21. Load monthly matched LDA outputs.
22. Generate GPT themes from keywords.
23. Compare communities across consecutive months.
24. Persist the accepted community-transition table.
25. Extract and persist thesis start-to-end DFS community paths.
26. Persist per-path member mobility (existing/new/lost/reappearing).
27. When enabled, compute and persist path-scoped theme cosine similarity plus the revision-pinned similarity embedding artifact.
28. Optionally render Sankey transition diagrams.
29. Optionally render membership-change diagrams.
30. Optionally render theme-similarity heatmaps from the same evolution similarity contract.

For Telegram forwarded-message analysis, step 5 is owned by the shared network
pipeline boundary rather than by a specific orchestrator. The boundary accepts
either legacy `source,target,relation` rows or already-normalized
`from_id,forwarder_id` rows. Legacy rows are normalized through the canonical
`PRODUCED` + `FORWARDED_BY` ingestion mapping before the existing IF/WIF metric
implementation runs. Therefore `run-social-network`, `run-all --debug`, normal
Prefect `run-all`, evolution runs, and programmatic network-pipeline callers use
the same Telegram input semantics.

## Pipeline Commands

Target commands:

```bash
python -m src.cli export-graph --config configs/<run>.yml
python -m src.cli run-social-network --config configs/<run>.yml
python -m src.cli run-topics --config configs/<run>.yml
python -m src.cli run-theme-analysis --config configs/<run>.yml
python -m src.cli verify-output-contract --config configs/<run>.yml
python -m src.cli run-all --config configs/<run>.yml
```

Make targets:

```bash
make db-up
make db-check
make ingest-sample
make run-network-sample
make run-topic-sample
make run-theme-sample
make run-pipeline-sample
make verify-output-contract
make run-evolution-pipeline-test
make verify-evolution-output-contract
make api-smoke-test
make frontend-install
make frontend-lint
make frontend-build
make build-report
make test
```

## Run Configuration

Every run should be configurable with:

- `data_type`
- `content_type`
- `month`
- `year`
- `input_path`
- `output_base_path`
- `creator_relation`
- `spreader_relation`
- `creator_node_column`
- `spreader_node_column`
- `text_node_column`
- `date_column`
- `min_total_post`
- `min_shared_post`
- `min_members`
- `lda.num_topics`
- `lda.top_n_keywords`
- `theme.enable_gpt`
- `theme.model`
- `theme.sleep_seconds`
- `theme.transition_threshold`
- `theme.evolution_similarity_enabled`
- `theme.similarity_model` and pinned `theme.similarity_model_revision`

## Output Preservation

The production pipeline must preserve the output categories listed in `docs/design-docs/current-code-feature-inventory.md`.

Generated tabular outputs are standardized on Parquet. The FR-004 migration explicitly retires generated CSV compatibility while preserving raw `data/raw/**` CSV ingestion.

The frozen public and internal artifact schemas are documented in
`docs/design-docs/output-artifact-contract.md`. The `verify-output-contract`
CLI command validates generated artifacts without rerunning any pipeline stage.

## Read-Only Artifact API

Plan 025 provides the canonical FastAPI read model under `src/api/`. It
discovers `<artifact_root>/runs/<run_id>/manifest.json`, resolves files only by
manifest artifact key, and verifies the selected artifact before reading or
streaming it. The API must not run ingestion, graph analysis, community
detection, LDA, theme generation, embeddings, visualization rendering, or
database clients.

The API exposes stable `/api/v1` routes for run discovery and filtering,
overview summaries, bounded graph subsets, communities, centrality, topics,
themes, transitions, persisted Community Evolution paths, path-scoped member
mobility and thematic similarity, legacy persistent/membership/similarity
compatibility views, reports, and downloads. Large table responses are paginated
and graph requests are limited by configured node and edge caps.

Local commands:

```bash
make api-smoke-test
make run-api API_ARTIFACT_ROOT=/path/to/artifacts
```

## Read-Only Dashboard

The Vite dashboard consumes only `/api/v1` artifact API endpoints. It must not
call old demo endpoints, mutate output files, run pipeline stages, or call
external services. It may show operational tables, status cards, and optional
file availability for generated artifacts.

## Offline And Online Modes

Offline mode:

- Runs export from existing CSV.
- Runs network, community, and LDA stages.
- Uses cached or mocked theme responses.
- Does not call OpenAI.

Online mode:

- May connect to database.
- May call OpenAI for GPT theme generation if `OPENAI_API_KEY` is configured.

## Failure Behavior

- Fail fast on missing config.
- Fail fast on missing required columns.
- Never delete raw input files.
- Do not overwrite previous run outputs unless explicitly configured.
- GPT failures should not destroy LDA outputs. Persistent typed provider safety outcomes are
  recoverable per unique theme payload: exact LDA/community evidence is retained, the theme
  interpretation is left unavailable, and other payloads/months continue. Unexpected errors
  remain fail-fast.
- Theme-generation coverage and per-source provenance are persisted; no placeholder theme is
  fabricated for unavailable interpretations.
- Visualization failures should be reported separately from analysis failures.

## Run Finalization Contract

Orchestrated pipeline execution owns the run lifecycle:

1. Create `<output_base_path>/runs/<run_id>/` and write a `running` manifest.
2. Execute stages using `ArtifactReference` objects; large DataFrames do not
   cross orchestration boundaries.
3. Persist generated analytical and intermediate tabular outputs as Parquet; raw input relationship exports remain CSV.
4. Publish validated canonical copies into `intermediate/`, `data/`, and
   `reports/`.
5. Atomically replace the manifest with `completed` only after all canonical
   records pass path, hash, size, row-count, and schema validation.
6. On any terminal error, atomically write `failed` with safe failure metadata.

Dashboard, API, and report consumers must use the run manifest rather than
inferring arbitrary filesystem paths.

### Cross-Run Stage Artifact Reuse Contract

Network/community, topic, and theme/evolution orchestration stages may reuse validated
internal artifacts from:

```text
<output_base_path>/.stage_cache/v1/<stage>/<stage_cache_key>/
```

The stage key is derived only from computation dependencies: relevant input/dataset
hashes, relevant resolved configuration, explicit stage cache/contract versions, and a
stage-scoped code/runtime fingerprint. `pipeline_run_id`, Prefect flow-run identity,
output paths, tracking metadata, and unrelated configuration are excluded.

On a valid hit, cached bytes are integrity-checked and restored under the current
`runs/<run_id>/` root before downstream stages execute. On a miss, incomplete entry, or
hash/size mismatch, the unchanged domain stage executes and its successful artifacts
are snapshotted atomically. Cached entries never replace the current run manifest or
become a public consumer boundary. `orchestration.artifact_reuse: false` bypasses both
cache restore and cache publication for an explicit recomputation run.

Prefect result persistence remains enabled for orchestration observability, but Prefect
task-result caching is not the cross-run artifact-reuse mechanism because cached task
results may contain references to an older run directory.

## Theme Trend Publication

The read-only API exposes additive deterministic views over existing theme
artifacts:

```text
GET /api/v1/runs/{run_id}/theme-trends/monthly?period=YYYY-MM&scope=matched
GET /api/v1/runs/{run_id}/theme-trends/timeline?period_start=YYYY-MM&period_end=YYYY-MM&scope=matched
```

These endpoints read every manifest-listed monthly theme Parquet needed for the
request and are not constrained by ordinary table pagination. They publish
available periods, source/exclusion counts, exact-label matched-pair coverage,
keyword evidence, and the deterministic timeline leader.

The existing topic and theme table endpoints accept `period=YYYY-MM`; the theme
endpoint additionally accepts `exact_theme=<case-sensitive exact label>` before
pagination. Existing month, community, pagination, artifact, and output
contracts remain compatible. No analytical stage or public output category is
changed.


## Canonical Theme Cluster Publication

After raw general GPT themes are written, runs with `theme.clustering_enabled`
publish an additive two-stage semantic clustering result before community
transition/similarity rendering:

1. field-specific `general_theme_names` parsing preserves commas inside semantic
   labels; exact legacy dot-joined multi-theme strings are reconstructed only
   through an exact `general_theme_gpt` key round-trip -> clustering TEI embeddings ->
   immutable content-addressed `float32` Parquet embedding artifact;
2. persisted raw vectors expanded back to all theme observations -> an in-memory
   L2-normalized copy -> scikit-learn Euclidean HDBSCAN monthly clusters using
   `leaf` selection;
3. each non-noise monthly cluster -> reuse its already-produced deterministic
   semantic-medoid embedding -> L2 normalization -> run-local cosine complete-linkage
   agglomerative canonical families at similarity `0.65`;
4. canonical families -> distinct matched-pair counts and aggregated general LDA
   keyword evidence.

Stage B does not issue a second representative-label embedding request and does not
average heterogeneous constituent vectors. Canonical labels remain existing monthly
representatives selected by deterministic semantic medoid over the normalized monthly
representative vectors. Canonicalization contract `4.0` persists the fixed
representation/grouping/threshold provenance, a generic Stage-B cluster label, and a
null legacy Stage-B HDBSCAN label. Monthly clustering contract `3.0` promotes the
Plan-086 unit-Euclidean/leaf candidate while preserving the raw recorded embedding
artifact, default `min_cluster_size=2`, sklearn-inclusive `min_samples=3`, and
`allow_single_cluster=false`. Stage-B canonicalization remains contract `4.0`.
Published clustering provenance explicitly records raw embedding normalization
separately from the normalized Stage-A input plus effective `min_samples`, selection
method, and single-cluster policy.

The raw `themes_*` artifacts are unchanged. New logical artifact keys are:

- `theme_clusters_<YYYY-MM>`;
- `theme_cluster_observations_<YYYY-MM>`;
- `theme_canonical_families`;
- `theme_embeddings_clustering`;
- `theme_embeddings_similarity` when Community Evolution similarity analysis
  is enabled.

The embedding artifacts are canonically published under
`data/themes/embeddings/` and are manifest-hashed like every other analytical
artifact. TEI model IDs and exact Hugging Face revisions are configuration
contracts; changing either changes embedding identity. Dashboard/API request
handlers never compute or persist embeddings.

The optional `canonical-theme-benchmark` command is outside the production
pipeline. It reads only completed persisted Stage-A evidence and recorded
clustering embeddings. The accepted roots are either the canonical published
`data/themes/` layout (`clusters/evidence/*.parquet` plus
`embeddings/clustering_general_themes.parquet`) or the run-local
`theme_clusters/` layout (`evidence/*.parquet` plus
`embeddings/clustering_general_themes.parquet`). The command writes diagnostic
CSV files to a caller-selected benchmark directory and never changes run manifests
or published analytical artifacts.

Canonical production evolution runs use exactly these dataset configurations:

- `configs/twitter/reply_evolution.yml` for Twitter replies;
- `configs/twitter/retweet_quote_evolution.yml` for Twitter retweets/quotes;
- `configs/telegram/forwarded_message_evolution.yml` for Telegram forwarded messages.

The Telegram evolution config consumes the legacy `source,target,relation` export
shape. The shared network pipeline reuses the existing ingestion mapping
(`PRODUCED` + `FORWARDED_BY`) to normalize creator/spreader message rows before
the unchanged IF/WIF network metrics execute; orchestration does not maintain a
separate Telegram normalization path. The retired `configs/longitudinal/`
configuration family is not
a production entry point. The internal `longitudinal_datasets` key remains a
compatibility name for multi-period run configuration and persisted metadata.

Before a real evolution run, `make pipeline-preflight CONFIG=...` validates
the locked dependency contract, required input CSVs, provider credentials,
output writability, the scikit-learn HDBSCAN runtime, and only the TEI profiles
actually required by that configuration. `make run-evolution-pipeline` depends
on this preflight. Memgraph is intentionally not required for this CSV-backed
workflow.

The API exposes saved results only:

```text
GET /api/v1/runs/{run_id}/theme-clusters/monthly?period=YYYY-MM&scope=matched
GET /api/v1/runs/{run_id}/theme-clusters/timeline?period_start=YYYY-MM&period_end=YYYY-MM&scope=matched
GET /api/v1/runs/{run_id}/theme-clusters/evidence?period=YYYY-MM&canonical_theme_id=<id>
```

These request handlers must not import or execute HDBSCAN, TEI, LDA, provider,
or community-detection code. Overview and Thematic Analysis share this read
model. Community Evolution continues to use the existing persisted-community
transition and `paraphrase-MiniLM-L6-v2` thematic-similarity path.


## Community Evolution Publication

Community Evolution is an artifact-first longitudinal read model over the accepted
`community_transition.parquet` graph. It preserves the thesis transition threshold
and the existing Sankey DFS path semantics rather than deriving persistence from
connected components in the API. New logical artifacts are:

- `community_paths` — one row per persistent path/month step, including member
  count, prior-step Jaccard/retained count, and raw absolute/weighted/general
  generated theme strings;
- `community_path_membership` — per-path/month existing, new, lost, and
  reappearing member sets/counts from the existing thesis mobility function;
- `community_path_theme_similarity` — path-scoped upper-triangle cosine records
  for general, absolute (IF), and weighted (WIF) raw generated themes, including
  embedding model/revision provenance.

`community_paths` and `community_path_membership` are always materialized after
the transition table. `theme.evolution_similarity_enabled` controls the semantic
similarity computation independently of `theme.render_visuals`; when the new flag
is absent, the historical `render_visuals` value is used as the compatibility
default. `render_visuals` now gates only PNG/HTML-style visual reports. Dedicated
evolution configs enable similarity explicitly.

The path-native API is read-only:

```text
GET /api/v1/runs/{run_id}/evolution/paths
GET /api/v1/runs/{run_id}/evolution/paths/{path_id}/mobility
GET /api/v1/runs/{run_id}/evolution/paths/{path_id}/theme-similarity?theme_type=general|absolute|weighted
```

Request handlers only read manifest-listed Parquet plus the secret-safe resolved
configuration. They do not run DFS, member classification, embeddings, cosine
similarity, HDBSCAN, NetworkX, GPT, or database clients. Community Evolution
continues to use the independently pinned `paraphrase-MiniLM-L6-v2` similarity
profile and does not consume Plan 039 canonical theme clusters.

## Multilingual Translation Before Topic Modeling

The optional `translation` stage is logically inside the topic boundary, after community-message artifacts are loaded and before `message_preprocess`. It must not mutate or overwrite the saved original-language community-message artifacts. When enabled, exact source texts are deduplicated, resolved through the persistent translation cache, and only missing texts are sent to the configured provider. The resulting English message copies feed the existing preprocessing/unigram/phrase-LDA code unchanged.

The topic computation identity includes only analytical translation settings (`enabled`, provider, target language, contract version), not operational cache path or timeout. Provider or contract changes therefore invalidate topic outputs and their downstream theme/evolution outputs while leaving network/community artifacts reusable. Language detections are cached separately from completed translations under the same provider/contract boundary so a detection-only planning pass can be reused by the later full topic run without repeating cloud language detection.

## Translation Workload Preflight
`make translation-preflight CONFIG=<config>` is a cloud-free planning path for the Plan 075 translation boundary. It runs or restores only the network/community preparation required to materialize the exact community-message inputs that can reach LDA, aggregates those messages across selected longitudinal datasets, deduplicates them, and inspects the persistent translation cache. It does not execute topic/LDA, themes, language detection, or translation provider calls. On a cold network cache, the preparation work is stored through the normal Plan 074 stage cache and is therefore reusable by the subsequent full evolution run. The report's language-detection request count follows the configured provider batching contract; exact translation-request count is intentionally reported as a range until language detection determines which cache misses are already in the target language.

`make translation-detect CONFIG=<config>` is the optional second planning step. It uses the same exact LDA-bound message set, calls only the configured provider's language-detection API (Azure `/detect` or AWS Comprehend), persists those detections, and does not call a translation endpoint. It then reports the exact number of non-target texts/characters and the exact translation-request count implied by the provider's translation batching logic. A later full topic run reuses cached detections; target-language detections are already complete no-translation cache records.
For Azure v3, `/detect` may identify a language/script while reporting `isTranslationSupported=false`. Those messages remain visible in the detection audit and are counted in the exact full-run workload; the later translation stage retries only those messages through `/translate` with the `from` parameter omitted so Azure performs translation-time source-language auto-detection. Successful fallback translations are cached normally. Unsupported foreign text must never be silently substituted as English analysis text, and messages above the Azure translate request-size limit remain blocking errors.
