# 002 – Database And Ingestion

This execution plan builds on the baseline foundation (Plan 001) and
focuses on replacing the Neo4j export workflow with a locally managed
Memgraph database and a clean ingestion layer.  Do **not** start this
plan until you have completed **001-baseline-and-foundation.md** and
documented its progress.

## Objective

1. **Introduce a repository abstraction** to decouple the rest of the
   code from any particular database engine.
2. **Implement Memgraph ingestion** for raw platform data and derived
   interaction edges.
3. **Refactor the existing Neo4j export script** into a reusable
   importer/exporter tool that reads from and writes to CSV files.
4. **Parameterize connection and ingestion settings** via config and
   environment variables.
5. **Verify Memgraph connectivity** and ingestion via tests and
   integration scripts.

## Tasks

### Task 2.1 – Graph repository abstraction

1. Create `src/graph_store/base.py` and define an abstract base class
   or `Protocol` named `GraphRepository`.  Methods should include:
   - `clear()` – drop or truncate all data (for test runs).
   - `import_raw_data(data_path: str, platform: str) -> None` – import
     platform‑specific raw nodes and edges according to `data-contract.md`.
   - `import_interactions(csv_path: str, snapshot_meta: dict) -> None` –
     import monthly interaction edges with metrics.
   - `export_interactions(snapshot_meta: dict, out_path: str) -> None` –
     dump interaction edges back to CSV matching the original thesis
     format (`source,target,relation`).
   - `get_distinct_users() -> Iterable[str]` – return all user IDs.
   - `close()` – close any open connections.
2. Create `src/graph_store/memgraph_repository.py` implementing
   `GraphRepository` using `mgclient` or `gqlalchemy`.  Read
   connection parameters from environment variables or config.  Make
   sure that `import_interactions` aggregates edges as described in
   `database-contract.md`.
3. (Optional) Create `src/graph_store/neo4j_exporter.py` that uses
   the existing Cypher queries from `neo4j_data_fetcher.py` to export
   data into CSV for import into Memgraph.  Remove hard‑coded URI and
   credentials; read them from config.

### Task 2.2 – CLI and config updates

1. Extend the config schema (see Plan 001) to include a `database`
   section with keys `engine`, `host`, `port`, `user`, and
   `password`.  Support environment variable interpolation using
   `${VAR}` syntax.
2. Add CLI commands in `src/cli.py`:
   - `db-up` – start Memgraph via Docker Compose if needed.
   - `db-check` – attempt to connect and run a simple query.  Exit
     non‑zero on failure.
   - `export-graph` – run the exporter to dump raw relationships from
     an upstream Neo4j instance (optional) into CSV.
   - `import-graph` – run the importer to load raw graph CSV files into
     Memgraph.
   - `ingest-interactions` – convert raw graph into monthly
     interaction CSVs and import them into Memgraph.  Use parameters
     from config (`min_total_post`, `min_shared_post`, etc.).
3. Update `Makefile` with new targets: `make db-up`, `make db-check`,
   `make ingest-sample`.  These should call the CLI commands.

### Task 2.3 – Data ingestion pipeline

1. Refactor existing code that splits creator/spreader and builds
   follower–followee edges (`utils/network_data_extractor.py`) into
   modular functions under `src/ingestion/`.  Ensure they are pure
   (database‑agnostic) and accept DataFrames and config parameters.
2. Write a new script `src/pipelines/ingestion_pipeline.py` that:
   - Reads raw platform CSVs (or outputs from the Neo4j exporter).
   - Calls ingestion functions to compute interaction edges.
   - Writes the monthly interaction edges to a temporary CSV.
   - Calls `GraphRepository.import_interactions` to load the edges.
   - Cleans up temporary files.
3. For Telegram and Twitter separately, write configuration presets in
   `configs/` illustrating how to specify creator/spreader relations.
4. Write unit tests for ingestion functions (using small fixtures) to
   ensure self‑forwarding rows are removed, metrics are calculated
   correctly, and config parameters are respected.
5. Write integration tests that spin up a Memgraph instance in a
   temporary Docker container (optional) and verify that the data is
   imported successfully.  Use `pytest` markers to skip these tests
   when Docker is unavailable.

### Task 2.4 – Migration and documentation

1. Document the migration path from the old Neo4j export workflow to
   the new Memgraph‑based ingestion.  Include sample commands for
   running the exporter, converting the CSV, and importing into
   Memgraph.
2. Update `ARCHITECTURE.md` to reflect the presence of the
   `GraphRepository` and the ingestion pipeline.
3. Update `HARNESS.md` with a brief summary of this plan and its
   non‑negotiable constraints (e.g. do not drop raw data, do not
   hard‑code credentials).
4. Record your progress in this file (as checkboxes or bullet points)
   when tasks are completed or blocked.

## Acceptance Criteria

- A `GraphRepository` interface exists with a working Memgraph
  implementation.
- A CLI command can start and check a Memgraph instance locally.
- An ingestion pipeline can import monthly interaction edges into the
  database using configuration and environment variables.
- At least one unit test verifies metric calculation during ingestion.
- The database contract file exists and matches the implemented
  repository behavior.
- `ARCHITECTURE.md` and `HARNESS.md` mention Memgraph and the
  repository abstraction.

Do **not** proceed to Plan 003 (Network/Community/Topic) until this
plan’s acceptance criteria are met and documented.

## Progress Log

| Date | Update |
|---|---|
| 2026-06-27 | Completed Phase 1 ingestion foundation only: added repository protocol, central thesis/export schema constants, missing pure network data extractor port, raw-to-derived mapping docs, and focused unit tests. Memgraph persistence remains out of scope for this phase. |
| 2026-06-28 | Added first Memgraph repository implementation for raw legacy CSV import, derived interaction import/export, index creation, distinct user lookup, CLI wiring for `db-check`/`import-graph`/`ingest-interactions`, sample database config blocks, Makefile cleanup, and mocked repository tests. |
| 2026-06-28 | Finished the Phase A ingestion slice: added `src/pipelines/ingestion_pipeline.py`, wired `ingest-interactions` to convert legacy raw CSVs or import derived metric CSVs, implemented config-driven `export-graph`, kept `import-csv` as an alias for repository-backed raw import, hardened raw CSV validation and index creation, aligned schema docs with thesis/export labels, and added mocked unit coverage for the ingestion pipeline and repository contract. |
| 2026-07-01 | Added a CLI `db-up` wrapper for the existing Docker Compose Memgraph workflow, documented local dev/test setup in the README, and preserved optional integration checks without making Docker required for unit tests. |
