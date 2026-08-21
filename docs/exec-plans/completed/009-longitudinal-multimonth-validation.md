# Execution Plan: Longitudinal Multi-Month Validation

Status: complete

Owner: agent

Last updated: 2026-07-01

## Goal

Add a deterministic two-month offline validation path proving the separated network, topic, and theme stages work across months and produce longitudinal thesis artifacts.

## Context

- `configs/longitudinal/`
- `tests/fixtures/longitudinal/`
- `Makefile`
- `src/topics/topic_inputs.py`
- `src/themes/theme_inputs.py`
- `src/pipelines/theme_pipeline.py`
- `docs/exec-plans/active/007-topic-only-execution.md`
- `docs/exec-plans/active/008-theme-only-execution.md`

## Non-Goals

- Do not change thesis metric definitions or algorithm defaults.
- Do not change public output schemas.
- Do not add multi-month CLI semantics.
- Do not require Neo4j, Memgraph, Docker, OpenAI, SentenceTransformer downloads, or Kaleido.

## Files Changed

- `tests/fixtures/longitudinal/twitter_reply_03_2017.csv`
- `tests/fixtures/longitudinal/twitter_reply_04_2017.csv`
- `configs/longitudinal/sample_twitter_reply_03.yml`
- `configs/longitudinal/sample_twitter_reply_04.yml`
- `Makefile`
- `tests/unit/test_longitudinal_sample.py`
- `README.md`
- `code_setup.md`
- `docs/exec-plans/active/009-longitudinal-multimonth-validation.md`

## Milestones

### Milestone 1: Fixture And Config Path

Tasks:

- [x] Add two month-scoped legacy `source,target,relation` fixtures.
- [x] Preserve creator/replier source-target direction.
- [x] Include a self-spread edge for exclusion coverage.
- [x] Add two month-scoped configs sharing one output root.

Validation:

```bash
.venv/bin/python -m pytest tests/unit/test_longitudinal_sample.py
```

### Milestone 2: Make Target

Tasks:

- [x] Add longitudinal Make variables.
- [x] Add `run-longitudinal-sample`.
- [x] Run March ingestion/network/topic, then April ingestion/network/topic, then one theme pass and report.

Validation:

```bash
make run-longitudinal-sample
```

### Milestone 3: Documentation

Tasks:

- [x] Document the longitudinal sample command and output paths.
- [x] Keep one-month sample docs stable.

Validation:

```bash
make help
```

## Acceptance Criteria

- [x] Existing one-month sample commands remain unchanged.
- [x] Longitudinal fixtures preserve legacy CSV compatibility.
- [x] Self-spread edges are excluded from follower-followee metrics.
- [x] Topic inputs exist for `03_2017` and `04_2017`.
- [x] Theme input manifest accumulates `03` and `04`.
- [x] Theme transition output is non-empty for the two-month sample.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-01 | Implemented longitudinal two-month validation path with March/April fixtures, configs, Make target, docs, and unit tests. Focused longitudinal tests passed before full validation. |
| 2026-07-01 | Full offline validation passed: unit suite, config validation, one-month sample commands, two-month longitudinal sample, and artifact report generation. Longitudinal theme input manifest contains months `03` and `04`; `community_transition.csv` contains transition rows. |

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-01 | Use two month-scoped configs rather than adding multi-month CLI behavior. | Existing CLI contracts are intentionally month-scoped and already compose through Make. |
| 2026-07-01 | Keep the existing one-month sample unchanged. | Preserves fast default sample behavior and avoids breaking documented commands. |

## Risks

| Risk | Mitigation |
|---|---|
| Tiny LDA fixtures may emit numeric warnings. | Warnings are accepted if offline commands pass and outputs are generated. |

## Rollback Plan

Remove the longitudinal fixtures/configs/Make target/tests/docs from this plan. No production pipeline behavior or public output schema changes are required.
