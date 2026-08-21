# Plan 070: Theme-Analysis Provider Override CLI Regression

## 1. Goal
Restore the already-intended `run-theme-analysis --theme-provider` command contract used by the canonical offline sample Make target, without changing evolution-pipeline behavior, provider-routing semantics, theme-analysis methodology, or any protected analytical contract.

## 2. Source Snapshot
- Archive: `community-analysis-full-review-20260814-2248.zip`
- SHA-256: `975f83195e27ffc6426de65e4ad8b5d7d9e6d761cbd2efb1965ec3f9e575de54`
- Branch recorded by snapshot: `feature/frontend-ui-upgrade`
- HEAD recorded by snapshot: `4d05a1adbcf524858972ad5d20e9f0f7444141fc`
- The snapshot contains completed Batch A and B1-B4 work and is the exact baseline for this task.

## 3. Finding and Classification

### RF-069-001 — `run-theme-sample` passes an unsupported CLI option
**Classification:** `REAL_REGRESSION`

The Makefile invokes:

```bash
python -m src.cli run-theme-analysis \
  --config tests/configs/test_single_month.yml \
  --theme-provider mock
```

but the `run-theme-analysis` subparser does not define `--theme-provider`. The command therefore fails at argument parsing before theme execution begins. Other theme-running entry points (`run-all`, `run-evolution-pipeline`, and `pipeline-preflight`) already expose the same override semantics.

**Production behavior change:** Yes, limited to restoring the intended command-line override for `run-theme-analysis`.
**Analytical output change:** No.
**Evolution-pipeline behavior change:** No.

## 4. Root Cause
The Makefile/provider-routing modernization and the `run-theme-analysis` parser drifted apart. The canonical offline sample target already assumes an invocation-local override of `theme_provider.primary`, but the theme-only command never received the corresponding parser argument or dispatch plumbing.

## 5. Protected Contracts
This plan must not change:
- `shared_post`, `total_post`, or `weighted_post` behavior;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- approved LDA implementation/defaults;
- transition/Jaccard semantics or thresholds;
- Telegram support or ingestion normalization;
- provider fallback/fallback-chain/cache settings other than leaving them untouched when the primary provider is overridden;
- theme-generation methodology or downstream-of-LDA ordering;
- evolution-pipeline parser, dispatch, orchestration, configs, or runtime behavior;
- any generated artifact schema or output category.

## 6. Implementation Scope
Only the following files are approved:
1. `src/cli.py`
   - add optional `--theme-provider` to `run-theme-analysis` using the existing help text/semantics;
   - forward the parsed value to `_run_theme_analysis_command()`;
   - apply an invocation-local override only to `config["theme_provider"]["primary"]` after config validation.
2. `tests/unit/test_cli_theme_only.py`
   - add parser/dispatch regression coverage for `--theme-provider`;
   - add focused propagation coverage proving only `theme_provider.primary` changes and existing fallback/cache fields remain intact.
3. This execution plan.

No Makefile, provider implementation, theme-pipeline, orchestration, configuration-schema, or evolution-pipeline file is approved for modification.

## 7. Validation Plan
Focused regression checks:

```bash
python -m src.cli run-theme-analysis --help
python -m pytest -q tests/unit/test_cli_theme_only.py
```

Provider/config surrounding tests where dependencies permit:

```bash
python -m pytest -q \
  tests/unit/test_cli_theme_only.py \
  tests/unit/test_config.py \
  tests/unit/test_provider_factory.py \
  tests/unit/test_release_hygiene.py
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
make validate-config PYTHON=python
make run-theme-sample PYTHON=python
make run-pipeline-test PYTHON=python
make format PYTHON=python
make lint
make test-unit
make test-integration
make test
git diff --check
```

If project dependencies cannot be resolved in the review environment, those gates are recorded as `ENVIRONMENT_BLOCKER`; production behavior must not be weakened to make the sandbox pass.

## 8. Acceptance Criteria
- `run-theme-analysis --help` exposes `--theme-provider`.
- `run-theme-analysis --theme-provider mock` passes argparse instead of failing as an unknown argument.
- The dispatcher forwards the override to `_run_theme_analysis_command()`.
- The command changes only `theme_provider.primary` in the in-memory resolved config for that invocation.
- Existing fallback, fallback-chain, cache, retry, and other provider settings remain untouched.
- Config files are not rewritten.
- `run-evolution-pipeline` code and behavior remain byte-identical to the source snapshot.
- No real provider API call occurs in unit tests.
- No analytical metric/default/methodology or artifact contract changes.
- The task-only patch applies cleanly to a second pristine extraction of the exact source ZIP and all affected files byte-match the implementation workspace.

## 9. Progress Log
- 2026-08-14: Verified the source ZIP SHA-256 against the supplied manifest and extracted separate pristine/working copies with 609 files each.
- 2026-08-14: Read the mandatory repository contracts and relevant active plans before editing.
- 2026-08-14: Reproduced the pristine failure: `run-theme-analysis --theme-provider mock` exits at argparse with `unrecognized arguments`.
- 2026-08-14: Applied the surgical CLI parser/dispatch/primary-provider override and added focused regression tests. No Makefile, provider, theme-pipeline, orchestration, config, or evolution-pipeline implementation was changed.
- 2026-08-14: `python -m src.cli run-theme-analysis --help` now exposes `--theme-provider`; direct `run-theme-analysis --theme-provider mock` validates config and advances past argparse, then stops only because the review interpreter lacks Prefect.
- 2026-08-14: The two new regression tests pass directly: 2 passed. The full `test_cli_theme_only.py` selection reaches only pre-existing environment blockers (two missing Parquet-engine failures and one missing-Prefect failure); with a temporary review-only Parquet/Prefect shim outside the repository, all 5 tests pass.
- 2026-08-14: Surrounding config/provider/release-hygiene selection passed: 29 tests. Protected defaults/IF-WIF/threshold/Louvain/transition selection passed: 17 tests.
- 2026-08-14: `python -m compileall -q src tests` and `make validate-config PYTHON=python` passed.
- 2026-08-14: `make run-theme-sample PYTHON=python` now passes argument parsing and config validation, then stops at the missing-Prefect environment blocker. `make run-pipeline-test PYTHON=python` is blocked earlier at ingestion because neither `pyarrow` nor `fastparquet` is installed.
- 2026-08-14: Verified the source text of `_run_evolution_pipeline_command` is byte-for-byte identical between pristine and working copies; `run-evolution-pipeline --help` output is also identical.
- 2026-08-14: `make format PYTHON=python` is blocked because Black is not installed. `make lint` is blocked by DNS while resolving `jiter==0.16.0`; `make test-unit` timed out during offline dependency retries; `make test-integration` failed resolving `scikit-learn==1.9.0`; and `make test` failed resolving `pandas==2.3.3`. These are `ENVIRONMENT_BLOCKER`s and no production code was changed to bypass them.
- 2026-08-14: A preliminary task-only patch passed `git apply --check` and applied cleanly to a second pristine extraction of the exact 22:48 ZIP; all three affected files byte-matched the implementation workspace.
- 2026-08-14: On the patch-applied fresh copy, the two new regression tests passed directly, the surrounding config/provider/release-hygiene selection passed (29 tests), the protected analytical smoke selection passed (17 tests), `compileall` and config validation passed, and the full theme-only CLI module passed all 5 tests with the review-only external Parquet/Prefect shim.
- 2026-08-14: Final patch regeneration follows this completed progress log and is rechecked against a fresh extraction before handoff.
