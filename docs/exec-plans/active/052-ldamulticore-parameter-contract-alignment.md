# Plan 052 — LdaMulticore Parameter Contract Alignment

## Goal

Resolve FR-001 by making the declared production LDA configuration match the
actual Gensim `LdaMulticore` constructor arguments without changing the thesis
pipeline structure or the existing default worker-selection behavior.

## Approved analytical migration

The thesis-era implementation used `alpha='auto'` and `eta='auto'`. The current
production implementation uses `LdaMulticore`, which does not support automatic
alpha optimization but does support `eta='auto'`.

Approved production contract:

- `implementation='ldamulticore'`
- `num_topics=15`
- `random_state=100`
- `iterations=100`
- `chunksize=20`
- `passes=80`
- `alpha='symmetric'`
- `eta='auto'`
- no default `workers` value is introduced; Gensim retains its existing worker
  selection unless a run explicitly configures `workers`.

This is an explicitly approved compatibility migration. It does not change IF,
WIF, graph thresholds, Louvain defaults, preprocessing, topic count, keyword
cutoff behavior, coherence/perplexity calculation, or downstream theme logic.

## Tasks

- [x] Align Python and YAML LDA defaults with the approved production contract.
- [x] Add `implementation='ldamulticore'` as validated project metadata without
      forwarding it to the Gensim constructor.
- [x] Remove hidden `alpha`/`eta` coercion from runtime LDA resolution.
- [x] Reject unsupported `alpha='auto'` and unknown LDA implementations before
      analytical execution.
- [x] Preserve `eta='auto'` exactly.
- [x] Preserve implicit default worker selection and explicit worker overrides.
- [x] Repair the focused LDA constructor regression test to mock
      `LdaMulticore`, which is the implementation actually used by the source.
- [x] Align current fixture run metadata and authoritative contract docs.

## Validation

Focused gates:

```bash
pytest tests/unit/test_current_defaults.py
pytest tests/unit/test_algorithm_config_propagation.py
pytest tests/unit/test_lda_contract.py
pytest tests/unit/test_orchestration_tasks.py
python -m compileall src tests
make lint
make test
```

Known unrelated baseline failures or dependency blockers must be reported
separately rather than hidden by this change.

## Progress log

| Date | Update |
|---|---|
| 2026-08-11 | User approved the LdaMulticore compatibility contract: `alpha='symmetric'`, `eta='auto'`, all other thesis-aligned LDA defaults unchanged, and no explicit default worker count. |
| 2026-08-11 | Implemented contract/default alignment, early and runtime validation, removal of hidden prior coercion, focused regression coverage, fixture provenance updates, and documentation updates. |
| 2026-08-11 | Focused LDA default/config propagation tests passed; targeted LDA contract tests passed using a temporary external `kneed` stub because `kneed` is not installed in the sandbox; canonical Twitter evolution configs validated with `alpha='symmetric'`, `eta='auto'`, implicit workers; `compileall` and YAML parsing passed. `make lint` and `make test` were attempted but blocked because `uv` could not download missing dependencies in the network-restricted sandbox. The pre-existing provider fallback assertion in `test_current_defaults.py` remains unrelated and unchanged. |
