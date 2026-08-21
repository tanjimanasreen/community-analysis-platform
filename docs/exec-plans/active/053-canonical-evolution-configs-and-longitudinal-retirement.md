# Plan 053 — Canonical Evolution Configs And Longitudinal Retirement

Status: code-complete; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-11

## Goal

Resolve FR-002 by making the evolution pipeline the single canonical production
workflow for Twitter replies, Twitter retweet/quote data, and Telegram forwarded
messages. Retire the obsolete `configs/longitudinal/` family and prevent future
content-type/relation mismatches from executing silently.

## Canonical production configs

- `configs/twitter/reply_evolution.yml`
- `configs/twitter/retweet_quote_evolution.yml`
- `configs/telegram/forwarded_message_evolution.yml`

The Telegram config keeps the analytical `content_type: forward` contract and
uses January-October 2019 inputs under
`data/raw/telegram/forwarded_message/2019/<month>_2019.csv` (through
`${DATA_ROOT}`).

## Protected analytical behavior

This plan does not change:

- `shared_post` or `weighted_post`;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- the approved production LDA contract;
- community-transition threshold mathematics (FR-003 remains separate);
- DFS path construction, membership mobility, theme similarity, HDBSCAN, or
  embedding-model separation.

## Tasks

- [x] Protect the existing reply and retweet/quote evolution mappings.
- [x] Add the canonical Telegram forwarded-message evolution configuration.
- [x] Retire `configs/longitudinal/` and superseded production-only dataset
      configs now replaced by the evolution configs.
- [x] Add fail-fast cross-field validation for the canonical
      platform/content/relation/column mappings.
- [x] Apply mapping validation to CLI config validation, orchestration validation,
      and raw-to-derived ingestion resolution.
- [x] Reuse the existing Telegram raw relationship normalization before monthly
      network analysis; do not duplicate IF/WIF logic.
- [x] Make the two-month evolution test config inherit canonical reply semantics.
- [x] Remove environment interpolation settings used only by the retired
      longitudinal YAML family.
- [x] Replace live examples/current documentation with canonical evolution
      configuration paths while retaining legitimate historical/methodological
      uses of “longitudinal”.
- [x] Move completed Plan 009 to `docs/exec-plans/completed/` without rewriting
      its historical record.
- [x] Run focused validation and repository gates available in the environment.
- [x] Record final validation evidence and blockers.

## Validation

Focused checks:

```bash
python -m src.cli validate-config --config configs/twitter/reply_evolution.yml
python -m src.cli validate-config --config configs/twitter/retweet_quote_evolution.yml
python -m src.cli validate-config --config configs/telegram/forwarded_message_evolution.yml
pytest tests/unit/test_evolution_configs.py
pytest tests/unit/test_ingestion_pipeline.py tests/unit/test_orchestration_tasks.py
make run-evolution-pipeline-test
make format
make lint
make test
git diff --check
```

Real production preflight may fail in review environments because the archive
intentionally excludes `data/`, provider credentials, local TEI services, and
installed dependencies. Such blockers must be reported rather than treated as
analytical failures.

## Progress log

| Date | Update |
|---|---|
| 2026-08-11 | User approved retiring the longitudinal YAML family and standardizing production evolution on Twitter reply, Twitter retweet/quote, and Telegram forwarded-message configs. Telegram raw export shape was confirmed as `source,target,relation`, with `PRODUCED` and `FORWARDED_BY` forming the creator/spreader pair; production filenames were confirmed as `data/raw/telegram/forwarded_message/2019/<month>_2019.csv` for January-October 2019. |
| 2026-08-11 | Implemented the three-config production surface, mapping validation, Telegram raw-export normalization reuse, test-config inheritance, retired config/environment cleanup, Plan 009 archival, and current documentation updates. Focused config/ingestion/path-hygiene/metric-propagation tests passed (21 tests). All three canonical configs passed `src.cli validate-config`; an intentionally mismatched reply/retweet config failed as expected. The supplied September 2019 Telegram sample normalized from 6 raw relationship rows to one creator/spreader message row and one unchanged IF/WIF interaction edge. Python compileall and YAML parsing passed. |
| 2026-08-11 | Environment blockers: the archive intentionally has no `.venv`; `make run-evolution-pipeline-test` and `make format` therefore could not start. `make lint` created a temporary uv environment but failed because sandbox DNS could not download the locked `pandas==2.3.3` wheel; `make test` likewise stalled during dependency resolution and was terminated by the command timeout. System-Python longitudinal tests reached the Parquet boundary but 3 cases were blocked by missing `pyarrow`; two non-Parquet cases passed. Prefect is absent, so the focused orchestration mapping test was additionally exercised with an external no-op Prefect decorator and passed. The pre-existing NVIDIA fallback-model assertion still fails identically in the pristine baseline and implementation copy and was not changed. |
