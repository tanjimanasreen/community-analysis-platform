# Execution Plan: Offline Sample Hardening

Status: complete

Owner: agent

Last updated: 2026-07-01

## Goal

Make the advertised local sample commands truthful and reproducible without requiring remote services, database containers, OpenAI calls, model downloads, or Kaleido.

## Context

- `Makefile`
- `configs/sample_twitter_reply.yml`
- `tests/fixtures/sample_relationships.csv`
- `tests/fixtures/theme_lda/`
- `src/cli.py`
- `src/pipelines/ingestion_pipeline.py`
- `src/pipelines/theme_pipeline.py`
- `docs/verification/quality-gates.md`

## Non-Goals

- Do not change thesis metrics, thresholds, Louvain defaults, LDA defaults, or GPT defaults.
- Do not implement Memgraph persistence changes.
- Do not split the legacy social-network CLI into independent network-only and topic-only stages in this slice.
- Do not require optional visual export engines for tests or samples.

## Files Changed

- `Makefile`
- `README.md`
- `configs/sample_twitter_reply.yml`
- `src/cli.py`
- `src/pipelines/ingestion_pipeline.py`
- `src/reporting/artifact_index.py`
- `tests/fixtures/theme_lda/january_2017.csv`
- `tests/fixtures/theme_lda/february_2017.csv`
- `tests/unit/test_artifact_index.py`
- `docs/exec-plans/active/005-offline-sample-hardening.md`

## Milestones

### Milestone 1: Offline Fixtures And Config

Tasks:

- [x] Point the default Twitter reply sample config at checked-in relationship fixtures.
- [x] Add tiny matched-LDA theme fixtures for theme pipeline samples.
- [x] Lower only the sample config thresholds so tiny fixture graphs produce outputs.
- [x] Keep production/default thesis constants unchanged.

Validation:

```bash
make validate-config
```

### Milestone 2: Offline Ingestion And Reporting

Tasks:

- [x] Add `ingest-interactions --no-db` for local CSV derivation without Memgraph.
- [x] Ensure raw `source,target,relation` fixtures can produce derived interaction CSV output.
- [x] Add a minimal `build-report` implementation that writes a markdown artifact index.
- [x] Add unit coverage for artifact indexing.

Validation:

```bash
make ingest-sample
make build-report
```

### Milestone 3: Sample Command Truthfulness

Tasks:

- [x] Wire Make targets to `.venv/bin/python`.
- [x] Keep default sample targets offline.
- [x] Update README with exact offline sample commands and output paths.
- [x] Leave Docker/Memgraph behavior only on explicit database targets.

Validation:

```bash
make test
make run-network-sample
make run-topic-sample
make run-theme-sample
make run-pipeline-sample
```

## Acceptance Criteria

- [x] `make test` runs unit tests in `.venv`.
- [x] `make validate-config` validates the offline sample config.
- [x] `make ingest-sample` does not call Neo4j, Memgraph, Docker, or OpenAI.
- [x] `make run-network-sample` completes from fixture data offline.
- [x] `make run-topic-sample` completes from fixture data offline.
- [x] `make run-theme-sample` completes without OpenAI, model downloads, or Kaleido.
- [x] `make run-pipeline-sample` runs ingest, social/topic, theme, and report stages offline.
- [x] `make build-report` writes `/tmp/community-analysis-artifact-index.md`.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-01 | Completed offline sample hardening. Added fixture-backed sample config, no-db ingestion path, artifact index report command, theme LDA fixtures, README command documentation, and unit coverage for artifact indexing. Validation passed: `make test` with 65 tests, `make validate-config`, `make ingest-sample`, `make run-network-sample`, `make run-topic-sample`, `make run-theme-sample`, `make run-pipeline-sample`, and `make build-report`. |
| 2026-07-01 | Added setup and running instructions to `README.md` and refreshed `code_setup.md` around the current `.venv` workflow, offline sample pipeline, direct CLI commands, optional Memgraph commands, and optional legacy Neo4j export. Validation: `make validate-config` passed. |

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-01 | Keep `db-up`, `db-check`, and database import behavior as explicit database targets only. | The default samples must remain offline and must not require Docker or Memgraph. |
| 2026-07-01 | Use `/tmp/community-analysis-*` paths for sample outputs. | Sample commands should not pollute the repository while remaining easy to inspect. |
| 2026-07-01 | Document that sample social-network and topic targets both complete through the legacy combined social/LDA pipeline. | Splitting those stages is useful future work, but out of scope for this sample hardening slice. |

## Risks

| Risk | Mitigation |
|---|---|
| The legacy social-network CLI still runs LDA during `run-social-network`. | Kept behavior unchanged and documented the sample target as an offline social/topic-compatible run. |
| Tiny fixture data can trigger harmless numeric warnings in elbow/knee helpers. | Validation accepts successful completion; future work can suppress or guard the warning for tiny sample data. |

## Rollback Plan

Revert this plan's files and remove `/tmp/community-analysis-sample*` outputs. No database, remote service, or external model state is modified by the default sample commands.
