# Plan 057 — FR-006 Telegram Network Input Boundary

Status: code-complete; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-12

## Goal

Finish FR-006 by moving the Telegram raw relationship normalization responsibility
from the Prefect network task to the shared social-network pipeline boundary. All
network entry points must accept the documented legacy `source,target,relation`
Telegram forwarding export without duplicating parsing or changing IF/WIF logic.

## Current finding

FR-002 already added `normalize_network_input()` and wired it into the canonical
Prefect/evolution task. The residual gap is that direct `run-social-network`,
`run-all --debug`, and programmatic network-pipeline callers bypass that task and
reach `run_network_phase()` with raw Telegram rows, where the code historically
assumed `from_id`/`forwarder_id` were already present.

## Protected analytical behavior

This plan does not change:

- `shared_post`, `total_post`, or `weighted_post`;
- self-interaction exclusion;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- the approved production LDA contract;
- community matching/evolution semantics;
- Telegram/Twitter supported content types;
- generated Parquet artifact contracts;
- API/frontend behavior.

## Implementation

- [x] Reuse `normalize_network_input()` at the shared Telegram branch in
      `run_network_phase()`.
- [x] Pass the existing relation/column mapping parameters into that normalization
      boundary so canonical cross-field validation remains available without
      changing the network-phase public signature.
- [x] Preserve the prior copy semantics for already-normalized Telegram inputs.
- [x] Remove the duplicate Telegram normalization step from the Prefect network
      task; the task now loads the dataset and delegates to the shared pipeline.
- [x] Add regression coverage for raw Telegram normalization through the actual
      network phase, unchanged IF/WIF values, normalized-input compatibility, and
      clear invalid-shape failure.
- [x] Add orchestration coverage showing raw Telegram rows are delegated unchanged
      to the shared pipeline boundary.
- [x] Align architecture/pipeline/verification documentation with the single
      normalization owner.
- [x] Run focused and available broader validation.
- [x] Generate and verify a task-only patch against a second pristine extraction.

## Validation

Focused checks:

```bash
python -m pytest tests/unit/test_pipelines.py -k telegram -q
python -m pytest tests/unit/test_evolution_configs.py -q
python -m pytest tests/unit/test_follower_followee_metrics.py -q
python -m pytest tests/unit/test_orchestration_tasks.py -q
```

Repository gates where the review environment permits:

```bash
make run-pipeline-test
make run-evolution-pipeline-test
make format
make lint
make test
git diff --check
```

The review archive intentionally excludes installed dependencies, raw production
data, local services, and credentials. Environment blockers must be reported rather
than hidden by changing production behavior.

## Acceptance criteria

- Raw Telegram `source,target,relation` forwarding exports work through the shared
  network-analysis boundary.
- Already-normalized `from_id,forwarder_id` Telegram inputs continue to work with
  the same dataframe semantics as before.
- Raw and normalized equivalents produce the same `shared_post`, `total_post`, and
  `weighted_post` values.
- Invalid Telegram input shapes fail before a downstream `KeyError`.
- Prefect orchestration does not contain a second Telegram parser/normalizer.
- Direct CLI/debug/programmatic callers inherit the same boundary behavior without
  caller-specific normalization.
- No protected analytical default, metric, output schema/category, API, or frontend
  behavior changes.

## Progress log

| Date | Update |
|---|---|
| 2026-08-12 | Verified the 02:37 source archive checksum against the supplied manifest, extracted pristine and working copies, read the mandatory documentation and active plans, and confirmed FR-006 is partially resolved by FR-002: Prefect/evolution normalizes raw Telegram input, while direct/debug/programmatic social-network paths still rely on pre-normalized columns. |
| 2026-08-12 | Implemented the boundary change surgically: `run_network_phase()` now reuses `normalize_network_input()` only for Telegram, preserving the previous dataframe copy behavior after normalization; the Prefect network task no longer performs caller-specific Telegram normalization. No IF/WIF implementation or graph/community algorithm code changed. |
| 2026-08-12 | Focused validation passed: 3 Telegram network-boundary tests, 9 canonical evolution-config/normalization tests, 2 follower-followee metric tests, and 5 protected-default tests. The full orchestration task test file passed 17 tests under an external no-op Prefect task decorator because Prefect is not installed in the review interpreter. A pristine-vs-working normalized Telegram probe was byte-identical for network rows, synthetic users, and IF/WIF interactions; the raw Telegram probe changed from the baseline `KeyError: 'from_id'` to the expected normalized edge (`shared_post=2`, `total_post=3`, `weighted_post=2/3`). Python compileall passed. |
| 2026-08-12 | Broader environment gates: full `tests/unit/test_pipelines.py` has the same three environment blockers observed in the pristine baseline (two missing Parquet-engine failures and one missing `demoji` import); the four dependency-available tests in that file pass. `make run-pipeline-test`, `make run-evolution-pipeline-test`, and `make format` cannot start because the review archive has no `.venv`. `make lint` and `make test` attempted locked dependency resolution but failed downloading `blis==1.3.3` because sandbox network/DNS access is unavailable. No blocked gate is claimed as passed. Protected graph/Louvain/LDA/evolution defaults were re-parsed and confirmed unchanged. |
| 2026-08-12 | Final patch discipline completed: task-only diff passed `git diff --check`; a second pristine extraction accepted `git apply --check`, applied cleanly, and byte-compared all affected files to the working implementation. The focused Telegram/evolution/metric/default/orchestration checks and Python compileall were rerun successfully on the patch-applied copy. |
