# Architecture

## Current Architecture

The current project is a script-based thesis prototype:

```text
Neo4j database
  -> neo4j_data_fetcher.py
  -> exported relationship CSV
  -> social-network-analysis.py
  -> network/community/LDA CSV outputs
  -> theme-analysis.py
  -> GPT themes, transitions, diagrams, similarity heatmaps
```

Supporting logic lives in `utils/`.

## Target Architecture

The production version should keep the same behavior but move it into a layered Python package:

```text
src/
  config/
  artifacts/
  data_io/
  graph_store/
  ingestion/
  network/
  communities/
  topics/
  themes/
  visualization/
  reporting/
  cli.py

tests/
  unit/
  integration/
  fixtures/
```

## Current-To-Target Mapping

| Current file | Target module |
|---|---|
| `neo4j_data_fetcher.py` | `src/graph_store/neo4j_exporter.py`, `src/graph_store/memgraph_client.py` |
| `social-network-analysis.py` | `src/pipelines/social_network_pipeline.py` |
| `theme-analysis.py` | `src/pipelines/theme_pipeline.py` |
| `utils/network_data_extractor.py` | `src/ingestion/network_data_extractor.py`, `src/network/follower_followee.py` |
| `utils/network_graph.py` | `src/network/graphs.py`, `src/network/centrality.py` |
| `utils/community_generator.py` | `src/communities/louvain.py`, `src/communities/messages.py`, `src/communities/stats.py` |
| `utils/similarity_detector.py` | `src/communities/similarity.py` |
| `utils/text_preprocessor.py` | `src/topics/text_preprocessor.py` |
| `utils/lda_analysis.py` | `src/topics/lda.py`, `src/topics/topic_matching.py` |
| `utils/lang_detector.py` | `src/text/language_detection.py` |
| `utils/lang_translator.py` | `src/text/translation.py` |

## Dependency Direction

Allowed dependency direction:

```text
config -> data_io -> graph_store -> ingestion -> network -> communities -> topics -> themes -> visualization -> reporting -> cli
```

Rules:

- Metric logic must not depend on graph database clients.
- LDA logic must not call OpenAI.
- Theme generation may call OpenAI only through a provider abstraction.
- Visualization functions should consume saved dataframes or typed records, not rerun pipeline logic.
- CLI commands should orchestrate modules, not contain analysis logic.

## Run Artifact Boundary

Prefect-orchestrated executions persist one immutable, self-contained bundle at:

```text
<output_base_path>/runs/<pipeline_run_id>/
```

The bundle contains a versioned lifecycle manifest, secret-free resolved
configuration, portable dataset identity metadata, intermediate stage handoffs,
published analytical data, and report artifacts. Domain pipelines write generated analytical and intermediate tables as Parquet
inside the run directory; the artifact layer publishes additive canonical copies
for future API, dashboard, report, notebook, and object-storage consumers. Raw
`data/raw/**` relationship exports remain CSV at the ingestion boundary.

Consumers must discover files through `manifest.json` and validate relative
path containment, checksum, byte size, row count, media type, schema version,
and known tabular schemas before reading. The artifact layer does not calculate
metrics or rerun analysis.

Equivalent orchestrated runs may reuse validated internal stage artifacts from:

```text
<output_base_path>/.stage_cache/v1/<stage>/<stage_cache_key>/
```

The stage cache is content-addressed from relevant inputs, configuration, code/runtime
fingerprints, and explicit stage contract versions; run IDs and output paths are not
part of computational identity. Cache hits are restored into the new run directory
before downstream validation, so every completed run remains self-contained. The
internal cache is not a dashboard/API/report discovery surface and corrupt or
incomplete entries are treated as misses.

## Graph Store Boundary

Database-specific code is isolated behind `GraphRepository` in
`src/graph_store/base.py`. Runtime connection settings come from the
`GRAPH_DB_*` environment contract; analytical YAML must not contain a `database:`
connection section. `src/graph_store/factory.py` resolves the configured backend
and fails explicitly for engines without an implementation. Memgraph Community
Edition is the current default implementation in
`src/graph_store/memgraph_repository.py`; the thesis-era Neo4j backend remains
historical/migration context and can be reintroduced later through another
repository implementation. The Memgraph repository must preserve both import
paths:

- raw legacy graph CSVs with `source,target,relation`;
- derived monthly user-user interaction Parquet artifacts with IF/WIF metrics.

Analysis modules should consume dataframes or repository outputs rather than
calling Memgraph or Neo4j clients directly.

## Core Pipelines

### Database Export Pipeline

Input:

- Neo4j or Memgraph graph data.

Output:

- Relationship CSV with `source`, `target`, `relation`.

Current implementation:

- `neo4j_data_fetcher.py`

Target command:

```bash
python -m src.cli export-graph --dataset telegram --month 2019-11
```

### Ingestion Pipeline

Input:

- Legacy graph relationship CSVs with `source`, `target`, and `relation`.

Output:

- Derived monthly user-user interaction Parquet artifacts with `source`, `target`,
  `total_post`, `shared_post`, and `weighted_post`.

Current implementation:

- `src/pipelines/ingestion_pipeline.py`

Target command:

```bash
python -m src.cli ingest-interactions --config configs/twitter_reply_march_2017.yml --file data/raw/twitter_reply.csv
```

### Social Network Pipeline

Input:

- Exported relationship CSV. For Telegram forwarded-message analysis, the shared
  network boundary accepts either the legacy `source,target,relation` export or an
  already-normalized `from_id,forwarder_id` dataframe and reuses the ingestion
  normalizer before IF/WIF computation.

Output categories:

- `network_data`
- `user_centrality`
- `count_user_messages`
- `daily_messages_stat`
- `communities/matched`
- `communities/partially_matched`
- `LDA/scores`
- `LDA/matched`
- `LDA/partial_matched`

Current implementation:

- `social-network-analysis.py`

Target command:

```bash
python -m src.cli run-social-network --config configs/twitter_reply_march_2017.yml
```

### Theme Intelligence Pipeline

Input:

- Monthly `LDA/matched/<content_type>/<month>_<year>.parquet` files.

Output categories:

- `LDA/matched_theme`
- canonical general-theme cluster summaries/evidence (additive production artifacts)
- `LDA/community_transition/community_transition.parquet`
- `LDA/community_transition/community_transition.png`
- `LDA/community_transition/community_transition.html`
- persisted Community Evolution path-step and member-mobility artifacts
- persisted path-scoped theme-similarity records
- `LDA/membership_change_graphs`
- `LDA/theme_similarity`

Current implementation:

- `theme-analysis.py`

Target command:

```bash
python -m src.cli run-theme-analysis --config configs/twitter_mixed_2017.yml
```

### Community Evolution Read Model

The accepted monthly `community_transition` table is transformed upstream into
deterministic start-to-end DFS path rows, per-path membership mobility rows, and
(optional) path-scoped raw-theme cosine-similarity rows. These are immutable
manifest artifacts published under `data/evolution/`. The FastAPI layer reads
those artifacts only; it does not reconstruct paths, classify members, or execute
embedding/similarity code during requests.

The dashboard canonical route is `/evolution`. It presents Community Similarity
over Time, Member Mobility, and Thematic Similarity on one page controlled by one
persistent-path selection and a sticky right-side section rail. `/transitions` is a
compatibility redirect; the prior completed-run history remains available at
`/run-history`.

## Local Services

Default production local services:

- Memgraph Community Edition for local graph storage.
- Optional Neo4j exporter compatibility for existing database exports.
- Optional OpenAI API key for GPT theme generation.
- Two revision-pinned TEI embedding profiles for production semantic work:
  similarity on `8080` (`paraphrase-MiniLM-L6-v2`) and general-theme clustering
  on `8081` (`all-MiniLM-L6-v2`).
- TEI is an inference boundary, not an embedding database. Theme-clustering
  vectors and Community Evolution thematic-similarity vectors are content-addressed,
  persisted as immutable float32 Parquet run artifacts, and registered in the
  canonical manifest.
- Monthly semantic clustering uses first-party `sklearn.cluster.HDBSCAN`.
  Cross-month canonicalization contract `4.0` reuses the already-produced vector
  of each monthly cluster's deterministic semantic medoid, L2-normalizes it, and
  uses `sklearn.cluster.AgglomerativeClustering` with cosine complete linkage at
  similarity `0.65`. Memgraph remains graph storage and is not used as a vector
  store.

## Configuration

All values currently hard-coded in scripts must become configuration:

- dataset type: `telegram` or `twitter`
- content type: `forward`, `reply`, `retweet_quote`, `mixed`
- month and year
- input/output paths
- creator relation
- spreader relation
- creator node column
- spreader node column
- message/text node column
- date column
- graph thresholds
- LDA parameters
- GPT model and rate limit settings
- theme similarity model

## Multilingual Topic-Preparation Boundary

Plan 075 adds an optional text-preparation boundary immediately before topic preprocessing. Original network/community message artifacts remain the empirical source of truth. When `translation.enabled=true`, unique source messages are language-detected and translated to English through a provider abstraction (`azure` by default, `aws` optional), with results persisted in a per-message content-addressed cache. Only translated in-memory copies feed the existing thesis text preprocessor and unchanged unigram/bigram LDA implementation.

Translation identity is provider/version aware and participates in the Plan 074 topic-stage cache. A valid topic-stage hit bypasses translation entirely; on a topic-stage miss, per-message cache hits avoid cloud calls.
