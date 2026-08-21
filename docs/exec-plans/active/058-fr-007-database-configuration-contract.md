# Plan 058 — FR-007 Database Configuration Contract

Status: code-complete; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-12

## Goal

Make the runtime graph-database configuration contract explicit and enforceable
without locking the architecture permanently to Memgraph. The thesis-era Neo4j
backend remains historical/migration context; Memgraph Community Edition remains
the current default implementation; future graph databases must plug in behind the
existing repository boundary.

## Current finding

`DatabaseSettings` already reads graph-database connection values from
`GRAPH_DB_*`, and `.env.example` documents that runtime path. However,
`get_database_config()` ignored its YAML config argument while the database
contract and sample config still advertised a `database:` YAML section. CLI graph
operations also constructed `MemgraphRepository` directly, so changing
`GRAPH_DB_ENGINE` could not select another implementation and could misleadingly
fall through to Memgraph.

## Protected behavior

This plan does not change:

- `shared_post`, `total_post`, or `weighted_post`;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- the approved production LDA contract;
- community matching/evolution semantics;
- Telegram/Twitter analytical support;
- raw CSV and generated Parquet artifact contracts;
- Memgraph queries, schemas, batching, or index behavior;
- the legacy Neo4j export/migration feature.

## Implementation

- [x] Keep `GRAPH_DB_ENGINE`, `GRAPH_DB_URI`, `GRAPH_DB_USER`, and
      `GRAPH_DB_PASSWORD` as the runtime graph-database connection contract.
- [x] Reject analytical YAML `database:` sections explicitly instead of silently
      ignoring them, including dataset-local sections.
- [x] Reuse the same policy check from run-config validation and direct database
      config resolution so commands such as `db-check` cannot bypass it.
- [x] Remove the obsolete `database:` block from the canonical single-month test
      config.
- [x] Add the smallest repository resolver needed to make backend selection
      explicit; Memgraph is currently supported/default and unimplemented engines
      fail clearly.
- [x] Route current graph-repository CLI construction through that resolver without
      changing repository behavior.
- [x] Align architecture/database/verification documentation with the
      environment-only, backend-extensible contract.
- [x] Add focused tests for environment settings, default Memgraph settings, YAML
      rejection, Memgraph resolution, and unsupported-backend failure.
- [x] Run focused and available broader validation.
- [x] Generate and verify a task-only patch against a second pristine extraction.

## Validation

Focused checks:

```bash
python -m pytest tests/unit/test_config.py tests/unit/test_graph_store_factory.py -q
python -m pytest tests/unit/test_current_defaults.py tests/unit/test_memgraph_repository.py -q
python -m compileall -q src tests
```

Repository gates where the review environment permits:

```bash
make validate-config
make test-unit
make test-integration
make test
make lint
make format
git diff --check
```

If a local Memgraph service is available:

```bash
make db-up
make db-check
```

Environment/service/dependency blockers must be reported separately rather than
hidden by changing production behavior.

## Acceptance criteria

- Graph connection values are resolved from the `GRAPH_DB_*` environment contract.
- The default engine remains `memgraph` with the existing local URI default.
- Analytical YAML `database:` sections fail with an actionable environment-only
  message rather than being ignored.
- `GRAPH_DB_ENGINE=memgraph` resolves to `MemgraphRepository`.
- An engine without a repository implementation fails explicitly and never falls
  through to `MemgraphRepository`.
- The repository abstraction remains suitable for a future Neo4j or other graph
  database implementation.
- No protected analytical metric, default, output schema/category, API, or frontend
  behavior changes.

## Progress log

| Date | Update |
|---|---|
| 2026-08-12 | Verified the 12:44 source archive SHA-256 against the supplied manifest, extracted pristine/working copies, read the mandatory documentation in order, and confirmed the FR-007 mismatch: runtime uses `GRAPH_DB_*`, the sample/docs still advertise YAML `database:`, and CLI repository construction is Memgraph-specific. |
| 2026-08-12 | Implemented the surgical contract change: YAML `database:` is rejected by one shared policy check, the sample block was removed, graph-repository construction now uses a small backend resolver, and unsupported engines fail explicitly while Memgraph remains the current default. No analytical or Memgraph query logic changed. |
| 2026-08-12 | Focused validation passed: 18 config/factory/default tests, the Memgraph connectivity boundary test, GraphRepository protocol conformance, 7 protected IF/WIF/default tests, `make validate-config PYTHON=python`, an explicit invalid-YAML CLI probe, and Python compileall. `.env.example` is byte-identical to the source archive and protected graph/Louvain/LDA defaults remain unchanged. |
| 2026-08-12 | Broader gates are environment-limited: `make test-unit` could not download Prefect because sandbox DNS is unavailable; offline `make test-integration`, `make test`, and `make lint` reported uncached locked dependencies; `make format` could not run because the partially created `.venv` lacks Black; Docker is unavailable so `db-up`/live `db-check` were not run. Two failures in `tests/unit/test_memgraph_repository.py` were reproduced identically in the pristine source and are unrelated baseline assertions, not FR-007 regressions. The full ingestion-pipeline test file is additionally blocked on its Parquet write because the review interpreter lacks `pyarrow`/`fastparquet`; its protocol-focused test passes. |
| 2026-08-12 | Final patch discipline passed: `git diff --check`; task-only patch generation; fresh source-archive extraction; `git apply --check`; clean patch application; byte comparison of all affected files; and focused tests/compile/config validation rerun successfully on the patch-applied copy. |
