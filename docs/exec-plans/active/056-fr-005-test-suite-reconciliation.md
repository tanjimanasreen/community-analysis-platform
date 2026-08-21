# Plan 056 — FR-005 Test Suite Reconciliation

Status: code complete; locked-environment gates partially blocked

Owner: agent

Last updated: 2026-08-12

## Goal

Resolve Codex FR-005 by making the release tests exercise the current supported
contracts instead of obsolete configuration, provider, LDA, or generated-CSV
interfaces. A failing test should represent a current product regression rather
than historical implementation drift.

## Protected analytical behavior

This plan does not change:

- `shared_post` or `weighted_post`;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- the approved production `LdaMulticore` contract;
- GPT/theme semantics, transition thresholds, DFS paths, membership mobility,
  theme similarity, HDBSCAN, or embedding-model separation;
- Telegram, Twitter Reply, or Twitter Retweet/Quote support;
- raw `data/raw/**` relationship CSV compatibility;
- generated-artifact Parquet semantics established by Plan 055.

## Failure classification rule

Every stale/failing test encountered in this FR is classified before repair as
one of:

- `REAL_REGRESSION`
- `STALE_TEST`
- `OBSOLETE_CONTRACT`
- `ENVIRONMENT_BLOCKER`

Production code must not be changed merely to satisfy an obsolete test.

## Baseline classification

| Area | Baseline evidence | Classification | Action |
|---|---|---|---|
| `tests/unit/test_config.py` | 3 failures reference deleted `configs/sample_twitter_reply.yml` | `STALE_TEST` | Use the supported offline test config and isolate tracking mutations. |
| `tests/unit/test_theme_pipeline.py` cache test | Constructs `CachedProvider` without its cache and uses the old scalar keyword API | `STALE_TEST` | Exercise the current cache constructor/keyword-list contract. |
| LDA constructor tests | Current tests patch `LdaMulticore`; FR-001 already resolved the original Codex finding | current | Do not reopen FR-001; extend orchestration result guards to forbid `LdaMulticore` objects. |
| `tests/unit/test_current_defaults.py` provider fallback expectation | Baseline expects the retired NVIDIA model spelling while `ThemeProviderDefaults` declares `nvidia:meta/llama-3.3-70b-instruct` | `STALE_TEST` | Align the assertion with the current default; do not change provider runtime behavior. |
| Topic/theme/run-manifest/orchestration fixtures | Multiple tests still model generated analytical handoffs as CSV although Plan 055 defines Parquet | `OBSOLETE_CONTRACT` | Convert only generated-artifact fixtures/assertions to Parquet; retain raw/legacy compatibility CSV tests. |
| `tests/unit/test_theme_data_loader.py` | Writes CSV while loader scans only `*_<year>.parquet`; baseline returns no monthly data | `STALE_TEST` | Use canonical Parquet fixtures. |
| `kneed`, `pyarrow`, Prefect in review sandbox | Declared by project/locked environment but absent from system interpreter | `ENVIRONMENT_BLOCKER` | Validate with locked project environment when available; report sandbox limitations separately. |
| Theme benchmark tests importing `SYSTEM_PROMPT`, `USER_PROMPT_TEMPLATE`, or `LLM7_BASE_URL` | Current benchmark code uses packaged Jinja templates and environment-configured LLM7 base URLs, so the removed constants caused collection-time failures | `STALE_TEST` | Assert against the generated benchmark request/template contract and current environment-backed base-URL policy instead of removed implementation constants. |
| Theme benchmark fixture path | Tests reference `tests/fixtures/theme_benchmark/matched_lda.csv`, but the checked-in canonical fixture is `matched_lda.parquet` | `STALE_TEST` / `OBSOLETE_CONTRACT` | Point benchmark tests at the checked-in Parquet fixture established by the generated-artifact contract. |
| Theme-model/config expectations | Thesis/early benchmark plans reference GPT-4o, while the production provider registry and OpenAI adapter now intentionally use `openai:gpt-5-nano` with strict JSON Schema output | `OBSOLETE_CONTRACT` in current-runtime tests/docs | Keep historical GPT-4o benchmark names/evidence, but make current-runtime tests and authoritative current contracts follow `configs/providers.yml`. |
| `theme-benchmark build-dataset --gpt-5-nano-outputs` | Parser exposes the upgraded option name but `_run_theme_benchmark_command()` still reads the historical `gpt4o_outputs` argparse destination | `REAL_REGRESSION` caused by partial model-name migration | Preserve the public `--gpt-5-nano-outputs` option and explicitly map it to the legacy internal destination; add a parser regression test. |

## Tasks

- [x] Replace deleted sample-config references with the supported test config.
- [x] Reconcile the stale cache-wrapper test with the current provider contract.
- [x] Convert canonical generated topic/theme/run-artifact test fixtures from CSV
      to Parquet without touching raw-input or intentional legacy-reader tests.
- [x] Align orchestration topic/theme fixtures, media types, output assertions,
      and stale/debug files with generated Parquet semantics.
- [x] Extend result-boundary guards to reject `LdaMulticore` objects as well as
      the historical `LdaModel` type.
- [x] Reconcile removed benchmark prompt/base-URL constants and canonical
      benchmark fixture paths so the benchmark suite collects against the
      current request/provider and Parquet artifact interfaces.
- [x] Align current-runtime theme-model assertions/docs with the current provider
      registry while retaining historical `gpt4o_*` benchmark artifact names.
- [x] Fix the upgraded `--gpt-5-nano-outputs` CLI option mapping without
      renaming legacy internal benchmark artifact plumbing.
- [x] Correct directly related current-code inventory wording surfaced by the
      audit; preserve historical plan evidence.
- [x] Run focused tests available in the environment, compile checks, and
      repository gates where dependencies permit.
- [x] Record environmental blockers and any unrelated baseline failures
      separately.
- [x] Generate and verify a task-only patch against a second pristine extraction.

## Validation

Focused suites:

```bash
python -m pytest tests/unit/test_config.py
python -m pytest tests/unit/test_theme_pipeline.py
python -m pytest tests/unit/test_topic_inputs.py
python -m pytest tests/unit/test_theme_inputs.py
python -m pytest tests/unit/test_theme_data_loader.py
python -m pytest tests/unit/test_pipelines.py
python -m pytest tests/unit/test_run_manifest.py
python -m pytest tests/unit/test_cli_theme_only.py
python -m pytest tests/unit/test_topic_reproducibility.py
python -m pytest tests/unit/test_orchestration_topic_tasks.py
python -m pytest tests/unit/test_orchestration_theme_tasks.py
python -m pytest tests/unit/test_theme_benchmark.py
python -m pytest tests/unit/test_theme_benchmark_gemini.py
python -m pytest tests/unit/test_theme_benchmark_llm7.py
python -m pytest tests/integration/test_orchestration_smoke.py
```

Repository gates where the environment permits:

```bash
make test-unit
make test-integration
make test
make lint
make format
git diff --check
```

## Acceptance criteria

- No live test references deleted `configs/sample_twitter_reply.yml`.
- Provider/cache tests use the current constructor and keyword-list contract.
- Current generated analytical/intermediate test artifacts use Parquet and
  `application/octet-stream`; raw relationship fixtures remain CSV.
- Topic/theme loaders and orchestration tests exercise the same Parquet paths
  used by production.
- Result-boundary tests reject both legacy `LdaModel` and current
  `LdaMulticore` objects.
- Current-runtime theme provider tests/docs follow `configs/providers.yml`;
  historical GPT-4o benchmark artifact names remain compatibility/history only.
- The public `--gpt-5-nano-outputs` benchmark option reaches the existing
  internal reference-import field without an argparse attribute error.
- No analytical metric, threshold, algorithm default, output category, API, or
  frontend behavior changes.
- Environment/dependency blockers are reported rather than hidden by weakening
  tests.

## Progress log

| Date | Update |
|---|---|
| 2026-08-11 | Verified the 20:42 source archive checksum against the supplied manifest, extracted pristine and working copies, read the mandatory documentation/active plans, and classified the known FR-005 failures before editing. Baseline `tests/unit/test_config.py` reproduced 3 stale missing-config failures; the stale `CachedProvider(provider)` test reproduced its constructor failure; `test_theme_data_loader.py` reproduced the CSV-vs-Parquet fixture failure. |
| 2026-08-11 | Reconciled generated-artifact fixtures with Plan 055 Parquet semantics across topic/theme loaders, run manifests, orchestration task tests, CLI theme-only tests, and reproducibility tests. Raw dataset/legacy-reader CSV coverage was intentionally retained. |
| 2026-08-11 | Repaired stale config, cache-wrapper, provider-default, and benchmark-interface tests. Full collection no longer fails on removed benchmark constants; remaining collection errors in the review interpreter are missing declared dependencies (`neo4j`, `mlflow`, `prefect`, `kneed`, `demoji`). |
| 2026-08-11 | Focused dependency-available regression selection passed 20 tests; changed Python files passed `py_compile`, and `python -m compileall -q src tests` passed. `tests/unit/test_theme_pipeline.py` ran 2/3 tests successfully; its Parquet-writing test is blocked solely because the system interpreter lacks `pyarrow`/`fastparquet`. |
| 2026-08-11 | Reconfirmed protected defaults from `configs/algorithms.yml`: graph 10/5, Louvain 1.0/123, LdaMulticore 15/100/100/20/80 with alpha=symmetric and eta=auto, transition thresholds 0.5/default and 0.0/reply. |
| 2026-08-11 | Locked `make test-unit` could not resolve NumPy because sandbox DNS cannot reach PyPI; `make test-integration` likewise stalled in dependency resolution. `make lint` timed out in dependency resolution and `make format` could not run because the partially created `.venv` lacks Black. These are environment blockers, not claimed passes. |
| 2026-08-12 | User clarified that productionization intentionally upgrades models/configurations from the thesis. Reclassified GPT-4o-only current-runtime expectations as stale, aligned current contracts/tests to the provider registry (`openai:gpt-5-nano` today), retained historical `gpt4o_*` benchmark artifact names, and fixed the partial CLI option rename with a parser regression test. |
| 2026-08-12 | Found and repaired one additional stale benchmark fixture contract missed by the first draft: benchmark tests referenced `matched_lda.csv`, while the checked-in fixture is `matched_lda.parquet`. All four benchmark modules now point at the canonical Parquet fixture. |
| 2026-08-12 | Dependency-available focused regression selection passed 14 tests. Benchmark modules collect cleanly (59 tests total across base/freeze/Gemini/LLM7). Full-suite collection now advances until declared-but-unavailable sandbox dependencies (`neo4j`, `mlflow`, `prefect`, `kneed`, `demoji`); no stale benchmark import errors remain. Changed Python files pass `py_compile`; `python -m compileall -q src tests` passes. |
| 2026-08-12 | Runtime execution of Parquet-backed repaired tests is blocked in the review interpreter because neither `pyarrow` nor `fastparquet` is installed; Prefect orchestration tests are blocked by missing `prefect`, and one pipeline test import is blocked by missing `demoji`. These packages are declared by the project and are environment blockers, not test-contract regressions. |
| 2026-08-12 | Locked gates: `make test-unit` failed during dependency resolution on `asyncpg` because sandbox DNS cannot reach PyPI; `make test` failed similarly on `gensim`; `make test-integration` and `make lint` timed out while resolving dependencies; `make format` could not run because the partially created `.venv` lacks Black. No blocked gate is claimed as passed. |
| 2026-08-12 | Reconfirmed protected defaults from `configs/algorithms.yml`: graph 10/5, Louvain 1.0/123, LdaMulticore 15/100/100/20/80 with alpha=symmetric and eta=auto, transition thresholds 0.5/default and 0.0/reply. Final patch verification repeats `git diff --check`, fresh-extraction `git apply --check`, patch apply, byte comparison, and focused tests after this log update. |
