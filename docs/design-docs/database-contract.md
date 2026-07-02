# Database Contract

This document specifies how the community‑analysis project interacts with
databases.  It describes the default local graph database (Memgraph),
connection configuration, and guidelines for data import/export.  The
intent is to make database usage explicit and configurable, ensuring
that the codebase can support multiple backends while remaining easy
for developers to run locally.

## 1. Default Database

### 1.1 Memgraph Community Edition

The production version of this project uses **Memgraph Community
Edition** as the default local graph database.  Memgraph was chosen
because it is free, open source, and compatible with the Cypher query
language familiar from Neo4j.  According to the Memgraph pricing page,
the Community Edition is free, forever and open source, and it
provides a full in‑memory graph database with ACID transactions,
on‑disk persistence and high‑availability replication【848454457501326†L80-L94】.

Memgraph can be run:

- **Locally** via a Docker image or native packages.  For example,
  `docker run -p 7687:7687 -p 3000:3000 memgraph/memgraph-platform` starts
  Memgraph and the Memgraph Lab web UI.
- **In the cloud** via Memgraph Cloud, which offers a free tier for
  experimentation and eliminates the need to manage infrastructure.

### 1.2 Neo4j Compatibility

The thesis implementation originally queried Neo4j.  The new codebase
must support importing data exported from Neo4j (CSV files), but it
should avoid hard‑coding Neo4j connection details.  A future adapter
could reconnect directly to Neo4j, provided it implements the same
repository interface described below.

## 2. Connection Configuration

All database connection parameters must be loaded from environment
variables or configuration files.  Do **not** hard‑code credentials or
URIs in code.

### 2.1 Environment Variables

The recommended environment variables for Memgraph are:

```env
MG_HOST=localhost
MG_PORT=7687
MG_USER=  # optional, default anonymous
MG_PASSWORD=  # optional, default anonymous
```

Use a `.env` file (not committed to version control) to provide these
values during development.  The Python code can use `python‑dotenv` to
load these values into the process environment.

### 2.2 Configuration File

Database settings may also be specified in a YAML or JSON configuration
file (see `configs/`).  A typical config block looks like:

```yaml
database:
  engine: memgraph
  host: ${MG_HOST}
  port: ${MG_PORT}
  user: ${MG_USER}
  password: ${MG_PASSWORD}
```

When the `engine` value is `memgraph`, the application should create a
`MemgraphRepository` using the provided host, port, user and password.
If another engine name appears, the application should attempt to
initialize the corresponding repository implementation (e.g. a
`Neo4jRepository`), or fail gracefully if unsupported.

## 3. Repository Pattern

To decouple business logic from database specifics, implement a
repository pattern.  Define an abstract base class with methods such
as:

```python
class GraphRepository(Protocol):
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
- derived monthly interaction import from CSVs containing `source`,
  `target`, `total_post`, `shared_post`, and `weighted_post` plus snapshot
  metadata.

Do not flatten these two import paths into a single table or CSV shape.

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
  LOAD CSV WITH HEADERS FROM 'file:///interactions.csv' AS row
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
