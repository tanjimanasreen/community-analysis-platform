# Plan 068: Final Review Batch B4 — Benchmark Test Reconciliation

## 1. Goal
Reconcile remaining benchmark review fixtures and provider-batch unit tests with the current Parquet artifact and theme-pipeline contracts, without changing production Python behavior, provider lifecycle, theme generation, analytical outputs, or protected thesis methodology.

## 2. Source Snapshot
- Archive: `community-analysis-full-review-20260814-1825.zip`
- SHA-256: `26707b68e585ec3c7710e97ceb2071681390a0357b73f28bc8c70c70418fbe1a`
- Branch recorded by snapshot: `feature/frontend-ui-upgrade`
- HEAD recorded by snapshot: `4d05a1adbcf524858972ad5d20e9f0f7444141fc`
- The snapshot already contains completed Batch A and B1-B3 work and is the exact baseline for this task.

## 3. Findings and Classification

### B4-01 — Blinded-review test decodes a Parquet artifact as UTF-8 text
**Classification:** `STALE_TEST`

Current production writes `review/blinded_export.parquet` and `review/review_import_template.parquet`. The stale test calls `Path.read_text()` on the binary blinded export, causing the previously reported Unicode decode failure. The test must read the artifact with `pandas.read_parquet()` and assert the review contract at the dataframe level.

**Production behavior change:** No.
**Analytical output change:** No.

### B4-02 — Review-import validation tests write CSV fixtures
**Classification:** `STALE_TEST`

`validate_review_import()` reads Parquet by contract, while residual tests still create `.csv` fixtures with `to_csv()`. The fixtures are changed to `.parquet` with `to_parquet()` while preserving the same validation expectations for missing score columns, duplicate review IDs, provider identity leakage, and invalid score ranges.

**Production behavior change:** No.
**Analytical output change:** No.

### B4-03 — Provider-batch test patches removed Sankey-path symbol
**Classification:** `STALE_TEST`

The provider lifecycle test still monkeypatches `theme_pipeline.find_all_sankey_paths`, but path construction now delegates through `build_community_path_artifact()` / `paths_as_lists()` and that symbol is no longer exposed by `theme_pipeline`. The obsolete monkeypatch is removed. The local fake for `process_single_file_themes()` is also updated to accept the current keyword-only `max_workers` argument. Finally, the identity-only provider sentinel is changed from an unrestricted `MagicMock` to a plain object so `hasattr(provider, "run_metrics")` does not fabricate a non-serializable metrics attribute. These changes keep the test focused on provider-instance reuse rather than obsolete helper/mock behavior.

**Production behavior change:** No.
**Analytical output change:** No.

### B4-04 — Plan 016 current artifact note omits current review Parquet names
**Classification:** `STALE_DOCUMENTATION`

The current-state note is extended to identify `review/blinded_export.parquet` and `review/review_import_template.parquet`. Historical `.csv` references in Plan 016 are intentionally retained as execution history.

## 4. Protected Contracts
This batch must not change:
- `shared_post`, `total_post`, or `weighted_post`;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- approved LDA implementation/defaults;
- evolution overlap semantics;
- Telegram input support;
- provider construction/routing/fallback behavior;
- LLM theme generation behavior;
- community transition/path algorithms;
- benchmark scoring/evaluation behavior;
- generated-table Parquet contract.

## 5. Implementation Scope
Only the following files are approved:
1. `tests/unit/test_theme_benchmark.py`
   - read blinded review as Parquet and assert blinded dataframe contents;
   - create the missing-score review-import fixture as Parquet.
2. `tests/unit/test_theme_benchmark_freeze.py`
   - create duplicate/leak/invalid-score review-import fixtures as Parquet.
3. `tests/unit/test_theme_pipeline_provider_batch.py`
   - remove the obsolete `find_all_sankey_paths` monkeypatch;
   - make the local processing fake accept the current keyword-only `max_workers` argument;
   - use a plain identity sentinel for the constructed provider so the mock does not fabricate `run_metrics`.
4. `docs/exec-plans/active/016-theme-generation-alternatives-benchmark.md`
   - extend only the current artifact note; preserve historical logs.
5. This execution plan.

No production Python file is approved for executable changes.

## 6. Validation Plan
Focused validation where a Parquet engine is available:

```bash
python -m pytest -q \
  tests/unit/test_theme_benchmark.py \
  tests/unit/test_theme_benchmark_freeze.py
python -m pytest -q tests/unit/test_theme_pipeline_provider_batch.py
```

Surrounding theme/provider validation where dependencies are available:

```bash
python -m pytest -q \
  tests/unit/test_theme_pipeline.py \
  tests/unit/test_theme_pipeline_provider_batch.py \
  tests/unit/test_theme_inputs.py \
  tests/unit/test_theme_data_loader.py
python -m pytest -q \
  tests/unit/test_provider_factory.py \
  tests/unit/test_theme_benchmark_gemini.py \
  tests/unit/test_theme_benchmark_llm7.py
```

Protected analytical smoke tests:

```bash
python -m pytest -q \
  tests/unit/test_current_defaults.py \
  tests/unit/test_follower_followee_metrics.py \
  tests/unit/test_graph_thresholds.py \
  tests/unit/test_louvain_defaults.py \
  tests/unit/test_community_transition.py
```

Structural/repository gates:

```bash
python -m compileall -q src tests
make validate-config
make format
make lint
make test-unit
make test-integration
make test
git diff --check
```

Missing Parquet engines or offline dependency resolution are recorded as `ENVIRONMENT_BLOCKER`; production code must not be changed to bypass them.

## 7. Acceptance Criteria
- Blinded-review test reads and validates the current Parquet artifact.
- Review-import validation fixtures use Parquet and retain all validation semantics.
- Provider-batch test no longer patches a removed symbol.
- The provider is still constructed exactly once and the same instance is passed for every month.
- Plan 016 current note describes current review Parquet artifacts without rewriting historical records.
- Zero production Python files are changed by this batch.
- No analytical/provider/theme/path behavior changes.
- `git diff --check` passes.
- The task-only patch applies cleanly to a second pristine extraction of the exact source ZIP.
- Every affected file byte-matches between the implementation workspace and the fresh patch-applied copy.

## 8. Progress Log
- 2026-08-14: Verified source ZIP SHA-256 against the supplied manifest.
- 2026-08-14: Reviewed mandatory repository contracts, Plan 016, and the current benchmark review/theme-pipeline implementations before editing.
- 2026-08-14: Reproduced the provider-batch stale-symbol failure on the pristine snapshot.
- 2026-08-14: Confirmed direct benchmark review execution is environment-blocked because the review interpreter lacks the declared `pyarrow`/`fastparquet` Parquet engine.
- 2026-08-14: Applied test/documentation-only reconciliation; no production Python file changed.
- 2026-08-14: Follow-up focused execution surfaced one additional stale unrestricted-`MagicMock` behavior: `hasattr(provider, "run_metrics")` fabricated a non-serializable attribute. Replaced the identity-only provider with a plain object; production metrics handling remains unchanged.
- 2026-08-14: Direct focused execution without a Parquet engine now reaches only the expected `pyarrow`/`fastparquet` environment blocker; the prior stale-symbol, UTF-8 decode, and CSV-fixture paths are removed.
- 2026-08-14: Using a temporary review-only Parquet shim outside the repository, the complete `test_theme_benchmark.py` + `test_theme_benchmark_freeze.py` selection passed: 23 tests. The four directly modified behavior tests (three review tests plus provider-batch) passed together: 4 tests.
- 2026-08-14: Surrounding theme pipeline/input/data-loader selection passed with the review-only shim: 12 tests.
- 2026-08-14: Protected analytical smoke selection passed without a shim: 17 tests.
- 2026-08-14: `python -m compileall -q src tests` and `make validate-config PYTHON=python` passed.
- 2026-08-14: `make format PYTHON=python` is blocked because Black is not installed. `make lint`, `make test-unit`, `make test-integration`, and `make test` are blocked by offline locked-dependency resolution/DNS; `make test-integration` specifically failed while fetching `blis==1.3.3`. No production code was changed to bypass these environment blockers.
- 2026-08-14: Preliminary task-only patch passed `git apply --check` and applied cleanly to a second pristine extraction of the exact 18:25 ZIP; all five affected files byte-matched the implementation workspace.
- 2026-08-14: On the patch-applied fresh copy, the full benchmark/freeze selection passed with the review-only Parquet shim (23 tests), provider-batch passed (1 test), protected analytical smoke tests passed without a shim (17 tests), `compileall` passed, and config validation passed.
- 2026-08-14: Final patch regeneration follows this completed progress log and is rechecked against a fresh extraction before handoff.
