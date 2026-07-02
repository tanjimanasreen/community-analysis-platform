# Execution Plan: True Theme-Only Execution

Status: complete

Owner: agent

Last updated: 2026-07-01

## Goal

Make `run-theme-analysis` genuinely theme-only by loading saved LDA/theme-input artifacts produced by `run-topics`, without recomputing network, community, or topic stages.

## Context

- `src/cli.py`
- `src/pipelines/social_network_pipeline.py`
- `src/pipelines/theme_pipeline.py`
- `src/themes/theme_inputs.py`
- `docs/exec-plans/active/007-topic-only-execution.md`

## Non-Goals

- Do not change public thesis output schemas.
- Do not change LDA, GPT, theme-transition, or similarity defaults.
- Do not require Neo4j, Memgraph, Docker, OpenAI, model downloads, or Kaleido.
- Do not replace LDA keywords with GPT-only themes.

## Files Changed

- `src/themes/theme_inputs.py`
- `src/pipelines/social_network_pipeline.py`
- `src/pipelines/theme_pipeline.py`
- `src/cli.py`
- `configs/sample_twitter_reply.yml`
- `Makefile`
- `README.md`
- `code_setup.md`
- `tests/unit/test_theme_inputs.py`
- `tests/unit/test_cli_theme_only.py`
- `tests/unit/test_pipelines.py`
- `docs/exec-plans/active/008-theme-only-execution.md`

## Milestones

### Milestone 1: Theme Input Contract

Tasks:

- [x] Add `ThemeInputBundle`.
- [x] Add `build_theme_input_dir`.
- [x] Add `save_theme_inputs`.
- [x] Add `load_theme_inputs`.
- [x] Add `validate_theme_inputs`.
- [x] Preserve list-valued `members` and keyword columns on load.
- [x] Copy public matched LDA CSVs exactly into `_intermediate/theme_inputs`.
- [x] Write CSV files first, compute SHA256 hashes, and write manifest last.

Validation:

```bash
.venv/bin/python -m pytest tests/unit/test_theme_inputs.py
```

### Milestone 2: Pipeline And CLI Wiring

Tasks:

- [x] Save internal theme inputs after matched LDA output is produced.
- [x] Make `run-theme-analysis` use saved theme inputs by default.
- [x] Keep explicit `theme.input_dir` legacy/manual fixture behavior.
- [x] Keep `run-theme-sample` theme-only.
- [x] Keep `run-pipeline-sample` as the orchestrated end-to-end path.

Validation:

```bash
.venv/bin/python -m pytest tests/unit/test_cli_theme_only.py tests/unit/test_pipelines.py
```

### Milestone 3: Documentation And Samples

Tasks:

- [x] Update sample config to use generated theme inputs by default.
- [x] Update Makefile help.
- [x] Update README and setup instructions.

Validation:

```bash
make validate-config
make run-network-sample
make run-topic-sample
make run-theme-sample
make run-pipeline-sample
make build-report
```

## Acceptance Criteria

- [x] `run-theme-analysis` does not call network, community, or topic stages.
- [x] `run-topic-sample` creates `_intermediate/theme_inputs/...`.
- [x] `run-theme-sample` consumes saved theme inputs.
- [x] Explicit `theme.input_dir` still works without requiring a manifest.
- [x] Missing internal theme inputs fail clearly.
- [x] Manifest metadata and hash mismatches fail clearly.
- [x] Unit tests remain offline.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-01 | Implemented true theme-only execution. Added manifest-backed theme-input artifacts, saved matched LDA CSV copies after topic output, made theme CLI load saved inputs by default, kept explicit fixture input override, updated sample config/docs/Makefile, and added focused tests. Focused validation passed with 19 tests before full validation. |
| 2026-07-01 | Final validation passed: `.venv/bin/python -m pytest tests/unit` passed with 88 tests; `make validate-config`, `make run-network-sample`, `make run-topic-sample`, `make run-theme-sample`, `make run-pipeline-sample`, and `make build-report` completed offline. `run-topic-sample` created `_intermediate/theme_inputs/...`; `run-theme-sample` loaded saved theme inputs and did not run network/community/topic stages. |

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-01 | Store theme prerequisites by year under `_intermediate/theme_inputs`. | Theme transitions compare monthly outputs across a year, so the contract is year-scoped. |
| 2026-07-01 | Keep `theme.input_dir` as an explicit override. | Unit tests and manual fixture runs need the legacy behavior. |

## Risks

| Risk | Mitigation |
|---|---|
| Generated tiny sample currently has one topic month, so transitions may be empty. | Unit fixtures still cover multi-month transition behavior; sample validates theme-only execution and output generation. |

## Rollback Plan

Remove `src/themes/theme_inputs.py`, restore `run-theme-analysis` to direct directory loading only, restore sample `theme.input_dir`, and revert related tests/docs.
