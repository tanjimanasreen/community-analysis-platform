# Execution Plan: Output Contract Freeze And Report Readiness

Status: complete

Owner: agent

Last updated: 2026-07-01

## Goal

Freeze and validate public and internal output artifact contracts so future
report, dashboard, and API work can rely on stable schemas.

## Non-Goals

- Do not change thesis metrics, defaults, or public output schemas.
- Do not start backend, frontend, or dashboard implementation.
- Do not require Neo4j, Memgraph, Docker, OpenAI, SentenceTransformer
  downloads, or Kaleido for tests.

## Files Changed

- `src/reporting/output_contract.py`
- `src/reporting/artifact_index.py`
- `src/cli.py`
- `Makefile`
- `tests/unit/test_output_artifact_contract.py`
- `docs/design-docs/output-artifact-contract.md`
- `docs/design-docs/pipeline-contract.md`
- `docs/verification/test-matrix.md`
- `README.md`
- `code_setup.md`
- `docs/exec-plans/active/010-output-contract-freeze-report-readiness.md`

## Milestones

### Milestone 1: Contract Verifier

Tasks:

- [x] Add public artifact path and column definitions.
- [x] Validate topic-input and theme-input manifests through existing loaders.
- [x] Enforce theme input SHA256 behavior.
- [x] Ensure copied theme inputs preserve public matched LDA schema.

Validation:

```bash
.venv/bin/python -m pytest tests/unit/test_output_artifact_contract.py
```

### Milestone 2: CLI And Make Targets

Tasks:

- [x] Add `verify-output-contract`.
- [x] Add `verify-longitudinal-output-contract`.
- [x] Keep verification read-only and offline.

Validation:

```bash
make verify-output-contract
make verify-longitudinal-output-contract
```

### Milestone 3: Documentation And Report Readiness

Tasks:

- [x] Add `docs/design-docs/output-artifact-contract.md`.
- [x] Document verification commands.
- [x] Keep `build-report` a lightweight artifact index.

Validation:

```bash
make build-report
```

## Acceptance Criteria

- [x] Unit tests pass.
- [x] One-month output contract verification passes after sample generation.
- [x] Longitudinal output contract verification passes after longitudinal sample generation.
- [x] Public thesis output file names and schemas remain unchanged.
- [x] Internal contracts are documented, versioned, and validated.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-01 | Added output artifact contract module, CLI/Make verification targets, contract docs, and unit tests. Validation pending. |
| 2026-07-01 | Full validation passed: unit suite, config validation, one-month pipeline sample, one-month contract verifier, longitudinal sample, longitudinal contract verifier, and artifact report generation. |

## Risks

| Risk | Mitigation |
|---|---|
| Optional partial-match and visualization outputs are not always produced by tiny fixtures. | Verifier skips optional files when absent and validates their schema when present. |
| Backend/frontend currently read some legacy or demo paths. | Plan 010 documents the stable contract only; implementation is out of scope. |

## Supersession note — 2026-08-11

Plan 055 supersedes only this plan's generated-CSV filename/compatibility
assumptions. The schema-freeze and read-only verification goals remain valid,
but current generated analytical/intermediate tabular artifacts are Parquet. Raw
`data/raw/**` relationship inputs remain CSV. Historical validation records above
are retained as evidence of the state at the time.

## Supersession note — 2026-08-12

Plan 059 supersedes this plan's current Make-target naming only. The historical
`verify-longitudinal-output-contract` milestone and validation records above are
retained as evidence of the state at the time. Current operational documentation
uses `run-evolution-pipeline-test` and `verify-evolution-output-contract`; the old
verification target remains only as a backward-compatible Make alias.
