# Database Contract

This document specifies how the community‑analysis project interacts with
databases.  It describes the default local graph database (Memgraph),
connection configuration, and guidelines for data import/export.  The
intent is to make database usage explicit and configurable, ensuring
that the codebase can support multiple backends while remaining easy
for developers to run locally.

## 1. Backend History and Current Default

### 1.1 Thesis-era Neo4j

The MSc thesis implementation queried Neo4j directly. That historical backend
choice is preserved as provenance, and the project retains the legacy
`source,target,relation` CSV export/import boundary needed to reuse thesis data.
Direct Neo4j repository support is not part of the current runtime graph-store
implementation. A future Neo4j adapter may be added behind `GraphRepository`.

### 1.2 Current Memgraph Default

The productionized project currently uses **Memgraph Community Edition** as the
default local graph database. Database-specific analytical access remains isolated
behind the repository boundary so a future production deployment can select a
different graph database by adding an implementation and resolver entry rather
than changing analytical pipelines.

Memgraph can be started locally through the repository Docker Compose service.
The current repository implementation is `MemgraphRepository`.

## 2. Runtime Connection Configuration

Current `GraphRepository` backend connection settings are **environment-only**.
Analytical run YAML controls datasets, algorithms, paths, and pipeline behavior; it
must not contain a
`database:` connection section. This prevents credentials from being copied into
resolved analytical configs or run artifacts and avoids silently ignored operator
settings.

The current runtime variables are:

```env
GRAPH_DB_ENGINE=memgraph
GRAPH_DB_URI=bolt://localhost:7687
GRAPH_DB_USER=
GRAPH_DB_PASSWORD=
```

For local development these values may be provided through an uncommitted `.env`
file. In deployed environments the same variables may be injected by the runtime
or secret/configuration service. Do not commit credentials.

`GRAPH_DB_ENGINE` is a backend identifier, not a promise that every identifier is
already implemented. The repository resolver currently supports `memgraph`. If an
unimplemented engine is selected, repository construction must fail clearly rather
than silently creating a Memgraph repository. Future backends (including a direct
Neo4j repository if required) should be added behind the same resolver and
`GraphRepository` interface.

A YAML block such as the following is invalid for analytical run configuration:

```yaml
database:
  engine: memgraph
  uri: bolt://localhost:7687
```

Configuration validation must reject this shape and direct the operator to the
`GRAPH_DB_*` environment variables. The separate legacy Neo4j export path is a
migration concern and is not the current `GraphRepository` backend selection
mechanism.

## 3. Repository Pattern

To decouple business logic from database specifics, implement a
repository pattern.  Define an abstract base class with methods such
as:

```python
class GraphRepository(Protocol):
    def check_connectivity(self) -> None: ...
    def clear(self) -> None: ...
    def create_indexes(self) -> None: ...
    def import_raw_data(self, data_path: str, platform: str) -> None: ...
    def import_interactions(self, csv_path: str, snapshot_meta: dict) -> None: ...
    def export_interactions(self, snapshot_meta: dict, out_path: str) -> None: ...
    def get_user_interactions(self, snapshot_meta: dict) -> Iterable[dict]: ...
    def get_distinct_users(self) -> Iterable[str]: ...
    def close(self) -> None: ...
```

Implementations must satisfy the interface, including closing
connections.  The `snapshot_meta` dictionary contains fields such as
`month`, `year`, `data_type`, and `content_type` to identify the
interaction snapshot.

The current implementation keeps this boundary in `src/graph_store/base.py`
and provides a Memgraph-backed implementation in
`src/graph_store/memgraph_repository.py`.  The repository supports two
separate import paths:

- raw graph import from legacy `source,target,relation` CSV exports;
- derived monthly interaction import from generated Parquet artifacts containing
  `source`, `target`, `total_post`, `shared_post`, and `weighted_post` plus
  snapshot metadata. The repository may continue reading older derived CSVs for
  backward compatibility, but new generated interaction exports are Parquet-only.

Do not flatten the raw relationship and derived interaction paths into a single
table or file shape.

## 4. Import and Export Guidelines

### 4.1 Importing Raw Graph Data

- Do not import raw platform data directly into the analytical graph.
  Instead, store raw nodes and edges using labels and properties
  defined in `data-contract.md`.
- Use bulk import operations where possible.  Memgraph supports the
  `LOAD CSV` statement (via mgconsole) or streaming connectors for
  high‑volume ingestion.

### 4.2 Importing Interaction Edges

- When importing monthly interaction edges (source–target pairs with
  `shared_post`, `total_post`, `weighted_post`), use a single Cypher
  query per snapshot.  Use the `MERGE` pattern to avoid creating
  duplicate nodes and to aggregate counts.  Example:

  ```cypher
  UNWIND $rows AS row
  MERGE (src:User {user_id: row.source})
  MERGE (dst:User {user_id: row.target})
  WITH src, dst, row
  MERGE (src)-[e:USER_INTERACTED_WITH {
    data_type: row.data_type,
    content_type: row.content_type,
    month: toInteger(row.month),
    year: toInteger(row.year)
  }]->(dst)
  ON CREATE SET e.shared_post = toInteger(row.shared_post),
                 e.total_post = toInteger(row.total_post),
                 e.weighted_post = toFloat(row.weighted_post)
  ON MATCH SET e.shared_post = e.shared_post + toInteger(row.shared_post),
                 e.total_post = e.total_post + toInteger(row.total_post),
                 e.weighted_post = (e.shared_post + toInteger(row.shared_post)) / (e.total_post + toInteger(row.total_post));
  ```

- Do not import self‑edges (rows where `source == target`).

### 4.3 Exporting Data

- Raw graph exports use the legacy thesis column order:
  `source,target,relation`.
- Derived monthly interaction exports use the analytical edge schema:
  `source,target,total_post,shared_post,weighted_post,data_type,content_type,month,year`.
- Use these exports for downstream processing or for migrating to
  another database.

## 5. Indexes and Constraints

Define indexes to improve query performance.  In Memgraph, create the
following indexes:

```cypher
CREATE INDEX ON :User(user_id);
CREATE INDEX ON :Channel(channel_id);
CREATE INDEX ON :Message(unique_id);
CREATE INDEX ON :Forward_Message(unique_id);
CREATE INDEX ON :Twitter_User(user_id);
CREATE INDEX ON :Retweet_Quote(unique_id);
CREATE INDEX ON :Reply(unique_id);
```

Memgraph currently does not support enforcing property existence
constraints.  However, by following the repository pattern and using
`MERGE` statements consistently, you can avoid duplicate nodes and
relationships.

## 6. Backup and Persistence

Although Memgraph is an in‑memory database, the Community Edition
supports periodic snapshots to disk.  In production, enable snapshot
creation and configure backup jobs to copy snapshots to persistent
storage.  When running locally, instruct developers to persist data
between sessions by not deleting the container volume or by using
Memgraph Cloud’s managed persistence.
