# Plan 067: Final Review Batch B3 — Prefect Cache Contract Reconciliation

## 1. Goal
Reconcile the remaining stale topic-orchestration cache assertion and inline task documentation with the current Prefect runtime contract, without changing Prefect execution behavior, cache-key semantics, analytical behavior, or protected thesis defaults.

## 2. Source Snapshot
- Archive: `community-analysis-full-review-20260814-1757.zip`
- SHA-256: `6ff2b66e05b45b3c3005ea93316ac6f9bee82df0fc8430487c24236a0d2d42d9`
- Branch recorded by snapshot: `feature/frontend-ui-upgrade`
- HEAD recorded by snapshot: `4d05a1adbcf524858972ad5d20e9f0f7444141fc`
- The snapshot already contains completed Batch A, B1, and B2 work and is the exact baseline for this task.

## 3. Findings and Classification

### B3-01 — Topic task test expects caching to be disabled
**Classification:** `STALE_TEST`

Observed current runtime:

```python
@task(
    name="run-monthly-topic-phase",
    retries=0,
    persist_result=True,
    cache_key_fn=topic_cache_key_fn,
    cache_expiration=datetime.timedelta(days=30),
)
```

Observed stale test expectation:

```python
assert run_monthly_topic_phase_task.cache_key_fn is None
```

Expected current behavior is the implementation already present in production: the topic task uses the stage-specific `topic_cache_key_fn`. Existing helper tests already protect its invalidation behavior, including LDA/input sensitivity and provider-setting exclusion.

**Production behavior change:** No.
**Analytical output change:** No.

### B3-02 — Topic task docstring says caching is disabled
**Classification:** `STALE_DOCUMENTATION`

The `run_monthly_topic_phase_task()` docstring states that caching is disabled and that `topic_cache_key_fn` is reserved for future activation, while the decorator directly above it already enables that key function.

The fix is documentation-only inside the existing runtime module.

**Production behavior change:** No.
**Analytical output change:** No.

### Reviewed but not changed — historical Plan 020
`docs/exec-plans/completed/020-prefect-topic-model-orchestration.md` documents the historical decision to leave task caching disabled at that earlier implementation stage. It is retained unchanged as historical execution-plan evidence rather than rewritten to match later runtime evolution.

### Reviewed but not changed — monthly flow signature
The current `run_monthly_network_foundation_flow` test invocation matches the current function signature. The older review claim of a signature mismatch is obsolete for this source snapshot, so no flow or test change is included here.

## 4. Protected Contracts
This batch must not change:
- `shared_post`, `total_post`, or `weighted_post` behavior;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- approved LDA implementation/defaults;
- evolution transition semantics;
- Telegram support or input normalization;
- graph database backend resolution;
- theme-provider routing or fallback behavior;
- `topic_cache_key_fn` implementation or semantic version;
- Prefect task retries, result persistence, cache expiration, or execution behavior.

## 5. Implementation Scope
Only the following changes are approved:

1. `tests/unit/test_orchestration_topic_tasks.py`
   - replace the stale `cache_key_fn is None` assertion with an assertion that the topic task is wired to `topic_cache_key_fn`;
   - rename the test/docstring to describe the current contract.

2. `src/orchestration/tasks.py`
   - update only the `Caching:` prose in the topic-task docstring;
   - do not alter the decorator or executable statements.

3. This execution plan.

## 6. Validation Plan
Focused validation:

```bash
python -m pytest -q tests/unit/test_orchestration_topic_tasks.py
```

Surrounding orchestration validation where the optional Prefect dependency is available:

```bash
python -m pytest -q \
  tests/unit/test_orchestration_tasks.py \
  tests/unit/test_orchestration_topic_tasks.py \
  tests/unit/test_orchestration_theme_tasks.py \
  tests/unit/test_orchestration_monthly_flow.py
```

Protected analytical smoke tests:

```bash
python -m pytest -q \
  tests/unit/test_current_defaults.py \
  tests/unit/test_follower_followee_metrics.py \
  tests/unit/test_graph_thresholds.py \
  tests/unit/test_louvain_defaults.py
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

Environment limitations such as missing optional Prefect or unavailable dependency resolution are recorded as `ENVIRONMENT_BLOCKER`; production code must not be changed to bypass them.

## 7. Acceptance Criteria
- `run_monthly_topic_phase_task` executable code is byte-unchanged apart from docstring text.
- The unit test asserts `run_monthly_topic_phase_task.cache_key_fn is topic_cache_key_fn`.
- Existing cache-key helper behavior is untouched.
- Completed historical Plan 020 remains untouched.
- No analytical, provider, graph, topic, or orchestration behavior changes.
- `git diff --check` passes.
- The task-only patch applies cleanly to a second pristine extraction of the exact source ZIP.
- Every affected file byte-matches between the implementation workspace and the fresh patch-applied copy.

## 8. Progress Log
- 2026-08-14: Verified source ZIP checksum against the supplied manifest.
- 2026-08-14: Reviewed mandatory repository contracts and Prefect orchestration plans before editing.
- 2026-08-14: Confirmed topic task decorator already enables `topic_cache_key_fn` with 30-day cache expiration and `retries=0`.
- 2026-08-14: Confirmed the remaining unit assertion and task docstring were stale.
- 2026-08-14: Applied surgical test and docstring reconciliation only; no executable production behavior changed.
- 2026-08-14: Direct focused pytest collection is blocked because the review interpreter does not have the optional `prefect` dependency (`ModuleNotFoundError`).
- 2026-08-14: Using a temporary review-only Prefect stub outside the repository, reproduced the pristine stale assertion failure and verified the updated cache assertion plus all cache-key helper tests: 7 passed.
- 2026-08-14: Full topic-orchestration test module with the review-only Prefect stub reached 14 passing tests and 7 tests blocked only by the missing Parquet engine (`pyarrow`/`fastparquet`).
- 2026-08-14: Protected analytical smoke selection passed: 12 tests.
- 2026-08-14: `python -m compileall -q src tests` passed.
- 2026-08-14: `make validate-config PYTHON=python` passed.
- 2026-08-14: Broader gates were attempted. `make format` is blocked by missing Black; `make lint`, `make test-unit`, `make test-integration`, and `make test` are blocked by offline locked-dependency resolution. These are environment blockers, not production defects.
- 2026-08-14: Generated a task-only patch from a temporary Git baseline of the exact uploaded snapshot; `git diff --check` passed.
- 2026-08-14: First fresh-extraction patch verification passed: `git apply --check`, patch application, byte comparison of all three affected files, 7 cache-focused tests with the review-only Prefect stub, 12 protected analytical smoke tests, `compileall`, and config validation.
