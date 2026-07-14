# Execution Plan: Baseline And Foundation

Status: active

Owner: agent

Last updated: 2026-06-23

## Goal

Preserve the current thesis behavior and create a clean configurable project foundation before deeper refactoring.

## Context

Read first:

- `AGENTS.md`
- `HARNESS.md`
- `ARCHITECTURE.md`
- `docs/design-docs/current-code-feature-inventory.md`
- `docs/design-docs/metric-contract.md`
- `docs/verification/test-matrix.md`

## Non-Goals

- Do not rewrite the full pipeline in this plan.
- Do not change metrics, thresholds, LDA settings, or GPT settings.
- Do not make OpenAI calls in tests.

## Files Expected To Change

- `README.md`
- `.env.example`
- `pyproject.toml` or `requirements.lock`
- `configs/`
- `src/config/`
- `src/cli.py`
- `tests/fixtures/`
- `tests/unit/test_current_defaults.py`

## Milestone 1: Capture Defaults

Tasks:

- [x] Extract current hard-coded parameters from `social-network-analysis.py`.
- [x] Extract current hard-coded parameters from `theme-analysis.py`.
- [x] Extract current graph/LDA/theme defaults into docs and config.
- [x] Add tests that assert current defaults.

Validation:

```bash
pytest tests/unit/test_current_defaults.py
```

## Milestone 2: Project Foundation

Tasks:

- [x] Add package layout under `src/`.
- [x] Add `.env.example`.
- [x] Add sample config files for Telegram and Twitter.
- [x] Add CLI skeleton.
- [x] Add Makefile commands.

Validation:

```bash
python -m src.cli validate-config --config configs/sample_twitter_reply.yml
make test
```

## Milestone 3: Fixture Data

Tasks:

- [x] Create small exported relationship CSV fixture.
- [x] Include exact, partial, unmatched, and self-spread cases.
- [x] Add expected output fixtures for metrics and community matching.

Validation:

```bash
pytest tests/unit
```

## Acceptance Criteria

- [x] Current behavior defaults are documented and tested.
- [x] No real credentials are present in source or docs.
- [x] Project has a CLI entry point.
- [x] Sample configs exist.
- [x] Fixture data exists.

## Progress Log

| Date | Update |
|---|---|
| 2026-06-23 | Created plan from inspected thesis code. |
| 2026-06-24 | Completed all milestones. Extracted defaults to config, built CLI skeleton, updated Makefile, and created mock data fixture. |
