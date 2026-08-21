# Plan 065 — Final Review Batch B1: Stale-Test Reconciliation

Status: complete

## Objective

Reconcile three residual stale unit-test assertions and add the missing configured
Memgraph batch-boundary coverage verified against the 2026-08-14 17:18 source
snapshot, without changing production code or protected analytical behavior.

## Classification

| Finding | Classification | Production behavior change | Analytical output change |
|---|---|---|---|
| Interaction-import test assumes top-level per-row Memgraph parameters | `STALE_TEST` | No | No |
| Raw legacy import test assumes pre-batching Cypher parameters | `STALE_TEST` | No | No |
| Duplicate NVIDIA fallback-model assertion uses retired model spelling | `STALE_TEST` | No | No |
| Configured interaction batch boundary lacks explicit unit coverage | `STALE_TEST` / coverage gap | No | No |

## Protected Contracts

This plan must not change:

- `shared_post`, `total_post`, or `weighted_post` behavior;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- approved LDA defaults or alpha/eta handling;
- evolution transition semantics or thresholds;
- Telegram raw `source,target,relation` compatibility;
- Memgraph Community Edition as the current default graph database;
- theme-provider routing or runtime defaults.

## Baseline Evidence

On the pristine 2026-08-14 17:18 snapshot:

```text
python -m pytest -q \
  tests/unit/test_memgraph_repository.py \
  tests/unit/test_ingestion_network_data_extractor.py

3 failed, 10 passed
```

The failures are:

1. `test_import_interactions_skips_self_edges_and_preserves_metrics` expects
   `params["source"]` etc. at the top level, while production intentionally
   submits `{"rows": [...]}` to `UNWIND $rows AS row`.
2. `test_import_raw_data_uses_legacy_csv_contract` expects `$source_pk` and
   `$target_pk`, while the batched query uses `row.source_pk` and
   `row.target_pk` plus top-level `platform`.
3. `test_defaults_are_preserved_for_ingestion_phase` expects the retired
   `nvidia:meta/llama3-70b-instruct` spelling instead of the current canonical
   `nvidia:meta/llama-3.3-70b-instruct` already protected elsewhere.

The current verification matrix additionally requires configured Memgraph batch
boundaries to be covered explicitly.

## Surgical Implementation

### B1-01 — Interaction-import batching assertions

File:

- `tests/unit/test_memgraph_repository.py`

Update the existing interaction-import test to assert:

- one `UNWIND $rows AS row` call for the single valid edge;
- exactly one submitted row;
- preserved source/target, IF/WIF metrics, and snapshot metadata;
- self-edges are absent from the submitted batch.

### B1-02 — Raw legacy import batching assertions

File:

- `tests/unit/test_memgraph_repository.py`

Update the raw-import test to assert:

- the current `UNWIND` query shape;
- `row.source_pk` / `row.target_pk` bindings;
- correct `User`, `Message`, and `CREATED` schema shape;
- `platform="telegram"`;
- source/target primary keys and properties preserved inside `params["rows"]`.

### B1-03 — Configured batch-boundary coverage

File:

- `tests/unit/test_memgraph_repository.py`

Add one focused test with three interaction rows and
`interaction_batch_size=2`. Verify two calls with row counts `[2, 1]`, stable row
ordering, the canonical `UNWIND` query, and unchanged weighted metrics.

### B1-04 — Duplicate provider-default assertion

File:

- `tests/unit/test_ingestion_network_data_extractor.py`

Replace only the stale NVIDIA model string with the current canonical
`nvidia:meta/llama-3.3-70b-instruct` value. Do not change provider production
configuration.

## Validation

Focused:

```bash
python -m pytest -q \
  tests/unit/test_memgraph_repository.py \
  tests/unit/test_ingestion_network_data_extractor.py
```

Surrounding graph-store/default coverage:

```bash
python -m pytest -q \
  tests/unit/test_memgraph_repository.py \
  tests/unit/test_graph_store_factory.py \
  tests/unit/test_current_defaults.py
```

Protected analytical smoke coverage:

```bash
python -m pytest -q \
  tests/unit/test_follower_followee_metrics.py \
  tests/unit/test_current_defaults.py \
  tests/unit/test_graph_thresholds.py \
  tests/unit/test_louvain_defaults.py
```

Structural/repository gates where available:

```bash
python -m compileall -q src tests
make validate-config
make lint
make format
make test-unit
make test-integration
make test
git diff --check
```

Dependency, DNS, Docker, or service limitations are recorded as
`ENVIRONMENT_BLOCKER`; production code must not be changed to bypass them.

## Acceptance Criteria

- Current Memgraph `UNWIND $rows` behavior is asserted rather than reverted.
- Self-edge exclusion and IF/WIF metric values remain protected.
- Configured interaction batch boundaries have explicit test coverage.
- Raw `source,target,relation` compatibility remains protected.
- The duplicate fallback-model assertion matches the existing canonical default.
- No production Python file is changed.
- No analytical output changes.
- Focused tests pass.
- The task-only patch applies cleanly to a second pristine extraction and all
  affected files byte-match the working implementation.

## Progress Log

| Date | Progress |
|---|---|
| 2026-08-14 | Verified the 17:18 archive SHA-256 against the supplied manifest, extracted pristine and working copies, read the mandatory contracts and relevant active plans, and reproduced the B1 baseline as 3 failed / 10 passed. |
| 2026-08-14 | Reconciled only the stale test assertions: Memgraph tests now assert the current `UNWIND $rows` batch contract, raw legacy CSV properties remain protected, a three-row fixture verifies configured `[2, 1]` interaction batch boundaries, and the duplicate NVIDIA expectation now matches the canonical `llama-3.3-70b-instruct` default. No production source was changed. |
| 2026-08-14 | Focused B1 validation passed 14/14. Surrounding graph-store/default validation passed 15/15, and protected IF/WIF/default/Louvain smoke validation passed 12/12. `python -m compileall -q src tests` and `make validate-config PYTHON=python` passed. |
| 2026-08-14 | Additional ingestion/file-format coverage had 5 passing tests and 2 environment-blocked Parquet tests because this interpreter lacks `pyarrow`/`fastparquet`. `make format PYTHON=python` is blocked because Black is absent; `make lint`, `make test-unit`, `make test-integration`, and `make test` are blocked by unavailable locked dependencies/network access. No blocked gate is claimed as passed. |
| 2026-08-14 | Final task-only patch verification completed against a second pristine extraction of the 17:18 ZIP: `git apply --check` and patch application succeeded, all three affected files byte-matched the working implementation, focused B1 tests passed 14/14, surrounding graph-store/default tests passed 15/15, protected smoke tests passed 12/12, `python -m compileall -q src tests` passed, and configuration validation passed. |
