# Plan 072 — Telegram `network_data` Date-Column Contract Reconciliation

Status: code-complete; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-16

## Goal

Fix the real Telegram evolution finalization failure:

```text
ValueError: artifact schema mismatch for network_data_01; missing columns: ['created_at']
```

The Telegram forwarding pipeline correctly preserves `forwarded_date` as the
canonical event timestamp, while the generic published-artifact schema currently
requires Twitter-style `created_at`. Reconcile those validators with the existing
canonical platform/content mapping without changing the produced analytical data.

## Protected analytical behavior

This plan must not change:

- Telegram raw normalization or `forwarded_date` values;
- `shared_post`, `total_post`, or `weighted_post`;
- graph thresholds, Louvain defaults, or LDA behavior/defaults;
- community matching, transitions, persistent paths, or member mobility;
- Plan 071 theme generation, provider safety recovery, fallback, embeddings, or
  HDBSCAN;
- artifact key naming, database behavior, or frontend behavior.

No `created_at = forwarded_date` compatibility column is synthesized.

## Implementation

- [x] Add one shared config-aware `network_data` required-column resolver in
      `src/reporting/output_contract.py` using the existing canonical raw-to-derived
      mapping. Canonical Telegram forward requires `forwarded_date`; canonical
      Twitter workflows require `created_at`; the existing no-config schema API
      remains backward compatible with `created_at`.
- [x] Make public output-contract checks use that resolver.
- [x] Make run-manifest Parquet/CSV schema validation resolve `network_data`
      against the run's persisted `resolved_config.yaml`, using the same resolver.
- [x] Add Telegram-positive, Telegram-wrong-date, and Twitter-preservation
      regression tests for both validation layers.
- [x] Document the platform/content-aware timestamp contract and verification
      invariant.
- [x] Run focused tests and available repository gates; record environment blockers
      without weakening production behavior.
- [x] Generate a task-only patch and verify it against a pristine extraction of the
      approved 2026-08-16 03:36 source snapshot.

## Explicitly out of scope

- the currently known unrelated `make test` reconciliation;
- duplicate artifact-key renaming/counters;
- MLflow tracing/concurrency changes;
- provider/theme changes;
- ingestion or network-data producer changes;
- new configuration switches.

## Acceptance criteria

1. A Telegram `network_data_01` artifact with `forwarded_date` and no `created_at`
   completes run-bundle publication and later passes `validate_run_manifest()`.
2. A Telegram forward artifact with `created_at` but no `forwarded_date` fails with
   a missing-`forwarded_date` schema error.
3. Twitter reply/retweet-quote continue to require `created_at`.
4. `verify_output_contract()` enforces the same platform/content-aware timestamp
   rule as run-manifest publication.
5. No protected metric, algorithm, provider, or Telegram producer behavior changes.

## Validation

Focused checks:

```bash
python -m pytest -q \
  tests/unit/test_run_manifest.py \
  tests/unit/test_output_artifact_contract.py \
  tests/unit/test_evolution_configs.py
python -m compileall -q src tests
```

Repository gates where the environment permits:

```bash
make validate-config
make run-evolution-pipeline-test
make verify-evolution-output-contract
make lint
make format
```

The pre-existing unrelated full-suite failures are intentionally deferred.

## Progress log

- 2026-08-16: User approved the date-column reconciliation and supplied the 03:36
  archive as the new source of truth.
- 2026-08-16: Verified archive SHA-256
  `6cad50e3709dfaca6ba4b9af3630a0458183cd9337fa69e93fad68e718b7bdd5`,
  extracted separate working/pristine copies, read mandatory repository contracts
  plus Plans 055, 057, and 071, and confirmed the failure is a validator mismatch:
  canonical Telegram forwarding maps to `forwarded_date` while the generic
  `network_data` schema requires `created_at`.

- 2026-08-16: Implemented one shared config-aware network schema resolver in
  `src/reporting/output_contract.py`. Canonical Telegram forwarding now requires
  `forwarded_date`; canonical Twitter workflows remain on `created_at`; callers
  without config retain the existing `created_at` default. Public output checks and
  run-manifest validation use the same resolver, with the latter reading the
  immutable run `resolved_config.yaml`. No network-data producer or ingestion code
  changed.
- 2026-08-16: Added focused regression coverage for Telegram acceptance, Telegram
  rejection when only `created_at` is present, and Twitter preservation in both
  output-contract and run-manifest layers. Updated the output-artifact contract and
  test matrix.
- 2026-08-16: Dependency-available focused checks passed: 12 tests covering the new
  pure schema resolver plus canonical evolution configs, `make validate-config
  PYTHON=python`, and `python -m compileall -q src tests`. A direct run-manifest
  contract probe (with only Parquet metadata reading stubbed because the sandbox
  lacks PyArrow) confirmed Telegram `forwarded_date` passes, Telegram
  `created_at`-only fails with missing `forwarded_date`, Twitter `created_at` passes,
  and Twitter `forwarded_date`-only fails with missing `created_at`.
- 2026-08-16: Full focused Parquet tests and `make run-evolution-pipeline-test
  PYTHON=python` are environment-blocked because neither `pyarrow` nor `fastparquet`
  is installed. A frozen `uv run` attempted dependency resolution but sandbox DNS
  prevented downloading `tiktoken`; no production behavior was weakened to bypass
  these environment limits.
- 2026-08-16: Patch discipline completed against the supplied 03:36 snapshot:
  `git diff --check` passed, the task-only patch passed `git apply --check` on a
  pristine extraction, applied successfully, and every changed file byte-compared
  equal to the working implementation.
