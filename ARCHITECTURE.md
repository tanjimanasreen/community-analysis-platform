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
published analytical data, and report artifacts. Domain pipelines continue to
write the frozen thesis CSV layout inside the run directory; the artifact layer
publishes additive canonical copies for future API, dashboard, report, and
notebook consumers.

Consumers must discover files through `manifest.json` and validate relative
path containment, checksum, byte size, row count, media type, schema version,
and known CSV columns before reading. The artifact layer does not calculate
metrics or rerun analysis.

## Graph Store Boundary

Database-specific code is isolated behind `GraphRepository` in
`src/graph_store/base.py`.  Memgraph support lives in
`src/graph_store/memgraph_repository.py` and must preserve both import
paths:

- raw legacy graph CSVs with `source,target,relation`;
- derived monthly user-user interaction CSVs with IF/WIF metrics.

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

- Derived monthly user-user interaction CSVs with `source`, `target`,
  `total_post`, `shared_post`, and `weighted_post`.

Current implementation:

- `src/pipelines/ingestion_pipeline.py`

Target command:

```bash
python -m src.cli ingest-interactions --config configs/twitter_reply_march_2017.yml --file data/raw/twitter_reply.csv
```

### Social Network Pipeline

Input:

- Exported relationship CSV.

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

- Monthly `LDA/matched/<content_type>/<month>_<year>.csv` files.

Output categories:

- `LDA/matched_theme`
- `LDA/community_transition/community_transition.csv`
- `LDA/community_transition/community_transition.png`
- `LDA/community_transition/community_transition.html`
- `LDA/membership_change_graphs`
- `LDA/theme_similarity`

Current implementation:

- `theme-analysis.py`

Target command:

```bash
python -m src.cli run-theme-analysis --config configs/twitter_mixed_2017.yml
```

## Local Services

Default production local services:

- Memgraph Community Edition for local graph storage.
- Optional Neo4j exporter compatibility for existing database exports.
- Optional OpenAI API key for GPT theme generation.

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
