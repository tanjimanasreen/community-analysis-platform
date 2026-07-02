# Execution Plan: CLI Stage Separation

Status: complete

Owner: agent

Last updated: 2026-07-01

## Goal

Make CLI and Makefile sample stages match their names: network/community sample execution should stop before LDA, while topic and full sample execution should still produce topic outputs offline.

## Context

- `src/pipelines/social_network_pipeline.py`
- `src/cli.py`
- `Makefile`
- `tests/unit/test_pipelines.py`
- `README.md`
- `code_setup.md`

## Non-Goals

- Do not change thesis metric definitions.
- Do not change graph thresholds, Louvain defaults, LDA defaults, or GPT defaults.
- Do not change output schemas or directory categories.
- Do not add external service requirements.

## Files Changed

- `src/pipelines/social_network_pipeline.py`
- `src/cli.py`
- `Makefile`
- `tests/unit/test_pipelines.py`
- `README.md`
- `code_setup.md`
- `docs/exec-plans/active/006-cli-stage-separation.md`

## Milestones

### Milestone 1: Pipeline Topic Gate

Tasks:

- [x] Add an `include_topics` flag to `run_full_pipeline`.
- [x] Preserve the old default by keeping `include_topics=True`.
- [x] Add `run_network_community_pipeline` as a compatibility wrapper for network/community-only execution.

Validation:

```bash
.venv/bin/python -m pytest tests/unit/test_pipelines.py
```

### Milestone 2: CLI And Make Target Alignment

Tasks:

- [x] Make `run-social-network` call the network/community-only pipeline.
- [x] Keep `run-topics` and `run-all` on the full network/community/topic pipeline.
- [x] Update `run-pipeline-sample` to call the topic sample so end-to-end output still includes LDA.

Validation:

```bash
make run-network-sample
make run-topic-sample
make run-pipeline-sample
```

### Milestone 3: Documentation

Tasks:

- [x] Update README command descriptions.
- [x] Update setup instructions with the stage distinction.

Validation:

```bash
make validate-config
```

## Acceptance Criteria

- [x] `make run-network-sample` completes without running topic/LDA messages.
- [x] `make run-topic-sample` still produces LDA output offline.
- [x] `run_full_pipeline` preserves full behavior by default.
- [x] Unit tests cover the no-topic and default-topic orchestration paths.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-01 | Completed CLI stage separation. Added `include_topics`, a network/community wrapper, CLI routing for social-network vs topic/full commands, and focused orchestration tests. Validation passed for `test_pipelines.py`, `make run-network-sample`, and `make run-topic-sample`; full offline validation continues after docs update. |
| 2026-07-01 | Final validation passed after Makefile/docs updates: full unit suite passed with 68 tests, `make validate-config`, `make ingest-sample`, `make run-pipeline-sample`, `make run-theme-sample`, and `make build-report` all completed offline. `make run-network-sample` now stops before LDA, while `make run-topic-sample` and the combined sample still produce LDA outputs. |

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-01 | Keep `run-topics` as network/community/topic execution for now. | The current topic stage depends on in-memory community messages from the prior stages; reading topic prerequisites from disk can be a future slice. |

## Risks

| Risk | Mitigation |
|---|---|
| `run-topic-sample` still recomputes network/community stages. | Documented behavior and kept output compatibility; a later plan can load topic prerequisites from saved community-message outputs. |

## Rollback Plan

Remove the `include_topics` flag and wrapper, restore the prior CLI branch to call `run_full_pipeline` for all social/topic commands, and revert the Makefile/docs updates.
