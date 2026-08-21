# Plan 064 — Final Review Batch A: Production Correctness

Status: complete

## Objective

Remediate three production-correctness findings verified against the
2026-08-14 01:28 source snapshot without changing protected analytical behavior:

1. community-summary API reads must accept the canonical four-column summary
   contract while preserving additive layout coordinates when present;
2. theme-benchmark manifests must reference the Parquet score summaries that
   the runner actually writes;
3. the optional Gemini benchmark provider must normalize an unavailable
   `google-genai` SDK import into the existing `ThemeBenchmarkError` install
   guidance rather than leaking a raw `ImportError`.

## Classification

| Finding | Classification | Production behavior change | Analytical output change |
|---|---|---|---|
| Community-summary `x`/`y` read mismatch | `REAL_REGRESSION` | Yes — canonical summaries become readable again | No |
| Benchmark manifest `.csv` score paths | `REAL_REGRESSION` | Yes — lineage points to produced Parquet files | No |
| Gemini namespace-package `ImportError` leakage | `REAL_REGRESSION` | Yes — optional-dependency failure is normalized | No |

## Protected Contracts

This plan must not change:

- `shared_post`, `total_post`, or `weighted_post`;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- approved `LdaMulticore` defaults or alpha/eta handling;
- positive-overlap evolution semantics or configured thresholds;
- Telegram support or normalization;
- LDA-before-LLM theme generation;
- Memgraph as the current default graph database;
- the Parquet generated-artifact contract;
- provider routing, retries, models, request payloads, or live-call policy.

## Baseline Evidence

Verified on the pristine source snapshot before implementation:

- `tests/unit/test_overview_monthly_services.py`: 4 failed, 3 passed. All four
  failures are `KeyError: "['x', 'y'] not in index"` because the API projects
  layout columns from canonical four-column community-summary fixtures.
- `_update_manifest(..., split="development")` records
  `scores/development_summary.csv`, while `run_benchmark()` writes
  `scores/development_summary.parquet`.
- with `GEMINI_API_KEY` present and `google-genai` unavailable in the review
  interpreter, `GeminiBenchmarkProvider(...)` leaks
  `ImportError: cannot import name 'genai' from 'google'`.
- `test_theme_benchmark_freeze.py::test_split_aware_benchmark_run_executes_only_requested_split`
  cannot reach its stale score-path assertion in this environment because
  PyArrow/Fastparquet is unavailable.

## Surgical Implementation

### A1 — Community summary reads

Files:

- `src/api/services/network_service.py`
- `tests/unit/test_overview_monthly_services.py`

Implementation:

- Keep `community_id`, `node_count`, `edge_count`, and `total_weight` as the
  required summary columns.
- Treat `x` and `y` as additive optional layout metadata.
- Read the small dashboard summary artifact without forcing optional column
  projection, then validate/normalize the required columns locally.
- Preserve `x`/`y` in the normalized frame when present and return `None` in API
  nodes when absent.
- Do not weaken `ArtifactReader` globally and do not change the output-artifact
  contract.

Protection:

- Existing four-column fixtures must pass unchanged.
- Add explicit coverage that summary coordinates survive when present.

### A2 — Benchmark manifest score paths

Files:

- `src/themes/benchmark/runner.py`
- `tests/unit/test_theme_benchmark_freeze.py`
- `docs/exec-plans/active/016-theme-generation-alternatives-benchmark.md`

Implementation:

- Record `scores/{split}_summary.parquet` for split runs.
- Record `scores/summary.parquet` for unsplit runs.
- Do not reintroduce generated benchmark score CSVs.
- Add a current-state note to Plan 016 clarifying that current benchmark score
  summaries are Parquet and historical CSV references remain historical.

Protection:

- Update the split-run path assertion to `.parquet`.
- Add a lightweight direct manifest regression test that does not require
  PyArrow and covers split and unsplit score paths.

### A3 — Gemini optional SDK error normalization

Files:

- `src/providers/gemini.py`
- `tests/unit/test_theme_benchmark_gemini.py`

Implementation:

- Catch import-level `ImportError` for `from google import genai` and translate it
  to the existing `ThemeBenchmarkError(GEMINI_INSTALL_MESSAGE)`.
- Leave the existing optional `google-genai` dependency declaration unchanged.
- Do not perform live provider calls in tests.

Protection:

- Keep missing-key coverage.
- Cover both `ModuleNotFoundError` and namespace-package-style `ImportError`.

## Validation

Focused:

```bash
python -m pytest -q tests/unit/test_overview_monthly_services.py
python -m pytest -q tests/unit/test_network_dashboard_sample.py
python -m pytest -q tests/unit/test_theme_benchmark_gemini.py -k "missing_key or missing_sdk"
python -m pytest -q tests/unit/test_theme_benchmark_freeze.py -k "manifest or split_aware"
```

Surrounding regression and protected-contract smoke tests:

```bash
python -m pytest -q tests/unit/test_backend_api.py tests/unit/test_overview_monthly_services.py tests/unit/test_network_dashboard_sample.py
python -m pytest -q tests/unit/test_theme_benchmark.py tests/unit/test_theme_benchmark_freeze.py tests/unit/test_theme_benchmark_gemini.py tests/unit/test_theme_benchmark_llm7.py
python -m pytest -q tests/unit/test_current_defaults.py tests/unit/test_graph_thresholds.py tests/unit/test_follower_followee_metrics.py tests/unit/test_louvain_defaults.py tests/unit/test_community_similarity.py tests/unit/test_community_transition.py
python -m compileall -q src tests
make validate-config
make lint
make format
make test-unit
make test-integration
make test
git diff --check
```

Dependency/DNS failures are recorded as `ENVIRONMENT_BLOCKER`; production code
must not be weakened to bypass them.

## Acceptance Criteria

- Four-column canonical community summaries are accepted by the API.
- Additive summary `x`/`y` coordinates are preserved when present.
- Benchmark manifests point to the Parquet score summaries actually produced.
- No generated score CSV is restored.
- Missing/unavailable `google-genai` imports consistently raise the project's
  `ThemeBenchmarkError` installation guidance.
- `google-genai` remains optional and tests make no live provider calls.
- Protected analytical behavior is unchanged.
- A task-only patch applies cleanly to a second pristine extraction and affected
  files byte-match the working implementation.

## Progress Log

| Date | Progress |
|---|---|
| 2026-08-14 | Verified archive SHA-256 against the supplied manifest, extracted pristine and working copies, read the mandatory contracts and relevant active plans, inspected current runtime/test behavior, and reproduced the three Batch A production findings. |
| 2026-08-14 | Added regression protection before production edits. The new benchmark-manifest test failed on stale `.csv` paths and the Gemini import test reproduced the namespace-package `ImportError`; canonical four-column summary fixtures reproduced the `x`/`y` projection failure. |
| 2026-08-14 | Implemented the three surgical fixes. Focused validation then exposed one secondary stale coverage assertion in `test_overview_monthly_services.py`; Plan 036 explicitly defines legacy community-map behavior as all community nodes, no cross-community edges, and an explicit compatibility reason, so only that test expectation was reconciled. |
| 2026-08-14 | Focused API validation passed 12/12 (`test_overview_monthly_services.py` + `test_network_dashboard_sample.py`). Gemini missing/disabled dependency guards passed 4/4, and the direct benchmark-manifest regression test passed. The split benchmark path test reaches a PyArrow environment blocker before exercising benchmark execution. |
| 2026-08-14 | Protected-contract smoke selection passed 20/20. `python -m compileall -q src tests`, `make validate-config PYTHON=python`, and `git diff --check` passed. Broader API and benchmark selections were partially blocked only by the review interpreter's missing Parquet engine; the benchmark selection had 22 passing tests and 39 PyArrow-blocked tests. |
| 2026-08-14 | Repository gates were attempted without claiming blocked work as passed: `make format PYTHON=python` is blocked because Black is absent; `make lint` is blocked by DNS while `uv` downloads `openai`; `make test-unit` is blocked by DNS while downloading `setuptools`; `make test-integration` is blocked by DNS while downloading `gensim`; `make test` is blocked while downloading `pyarrow`. |
| 2026-08-14 | Patch verification completed against a second pristine extraction of the source ZIP: `git apply --check` and application succeeded, all eight affected files byte-matched the working implementation, fresh-copy focused API/Gemini/manifest/protected-contract tests passed 37/37, and `python -m compileall -q src tests` passed. |
