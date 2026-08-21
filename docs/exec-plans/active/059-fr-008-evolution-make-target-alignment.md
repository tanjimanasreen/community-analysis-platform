# Plan 059 — FR-008 Evolution Make Target Alignment

Status: code-complete; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-12

## Goal

Resolve FR-008 by aligning current operational documentation with the canonical
`evolution` Make target names while retaining a narrow compatibility alias for the
pre-evolution longitudinal verifier name. Prevent future current-doc/Makefile target
drift with a lightweight release-hygiene test.

## Current finding

The Makefile defines `run-evolution-pipeline-test` and
`verify-evolution-output-contract`, and already retains `run-longitudinal-sample`
as a compatibility alias. Current operational docs still advertise
`verify-longitudinal-output-contract`, which did not exist in the supplied source
snapshot and failed immediately with `No rule to make target`. The internal CLI
verifier flag `--longitudinal` remains a valid implementation detail and is not
being renamed by this plan.

## Protected behavior

This plan does not change:

- `shared_post`, `total_post`, or `weighted_post`;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- the approved production LDA contract;
- evolution transition semantics or artifacts;
- Telegram/Twitter analytical support;
- database/provider/environment configuration;
- generated Parquet artifact schemas or output categories.

## Implementation

- [x] Keep `run-evolution-pipeline-test` and `verify-evolution-output-contract` as
      the canonical current Make targets.
- [x] Add `verify-longitudinal-output-contract` as a backward-compatible alias to
      the canonical verifier, matching the existing run alias strategy.
- [x] Update current operational documentation to advertise the canonical
      evolution commands.
- [x] Preserve historical execution-plan records and annotate Plan 010 with a
      supersession note rather than rewriting old evidence.
- [x] Add release-hygiene regression checks that current operational docs use
      canonical evolution names and that documented `make <target>` commands resolve
      to real Makefile targets.
- [x] Run focused and available broader validation.
- [x] Generate and verify a task-only patch against a second pristine extraction.

## Validation

Focused checks:

```bash
python -m pytest tests/unit/test_release_hygiene.py -q
make -n verify-evolution-output-contract
make -n verify-longitudinal-output-contract
make help
git diff --check
```

Repository gates where the review environment permits:

```bash
make test-unit
make test-integration
make test
make lint
make format
```

Environment/dependency blockers must be reported separately rather than hidden by
changing production behavior.

## Acceptance criteria

- Current operational docs advertise `run-evolution-pipeline-test` and
  `verify-evolution-output-contract`.
- `make -n verify-evolution-output-contract` resolves successfully.
- `make -n verify-longitudinal-output-contract` resolves to the same canonical
  verifier command for backward compatibility.
- Current operational docs do not advertise nonexistent Make targets.
- Historical longitudinal terminology in old execution evidence remains intact.
- No analytical metric, default, output schema/category, API, frontend, database,
  or provider behavior changes.

## Progress log

| Date | Update |
|---|---|
| 2026-08-12 | Verified the 13:07 source archive checksum against the supplied manifest, extracted pristine/working copies, read the mandatory documentation and relevant active plans, and reproduced FR-008: current docs advertise `verify-longitudinal-output-contract` while the Makefile has no such target. |
| 2026-08-12 | Implemented the surgical alignment: current operational docs now use `run-evolution-pipeline-test` and `verify-evolution-output-contract`; the historical verifier name is a compatibility Make alias; Plan 010 retains its original records with a supersession note; and release hygiene now checks documented Make commands against actual targets. No `src/`, config, `.env*`, metric, algorithm, artifact-schema, API, or frontend behavior changed. |
| 2026-08-12 | Focused validation passed: the focused Make-target/canonical-name release-hygiene checks passed; canonical and compatibility `make -n` commands resolve to the exact same verifier recipe; `make help` advertises the canonical names; and the current-doc target scan reports no missing Make targets. The full `test_release_hygiene.py` still has one unrelated baseline failure (`_load_benchmark_dotenv` is absent from `src.cli`), reproduced identically in the pristine source. |
| 2026-08-12 | Broader gates are environment-limited: `make test-unit` failed while uv could not download `black==26.5.1` because sandbox DNS is unavailable; `make test-integration` timed out during dependency resolution; `make test` failed downloading `beartype==0.22.9`; `make lint` failed downloading `plotly==6.9.0`; and `make format` cannot run because the partially created `.venv` has no Black. No blocked gate is claimed as passed. |
| 2026-08-12 | Final patch discipline passed: `git diff --check`; task-only patch generation; fresh source-archive extraction; `git apply --check`; clean patch application; byte comparison of all 9 affected files; and focused Make-target/release-hygiene checks rerun successfully on the patch-applied copy. |
