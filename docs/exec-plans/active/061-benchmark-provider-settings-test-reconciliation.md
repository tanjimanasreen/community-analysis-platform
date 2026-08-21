# Plan 061 — Benchmark Provider Settings Test Reconciliation

Status: code-complete; broader environment gates pending

Owner: agent

Last updated: 2026-08-12

## Goal

Remove the stale release-hygiene dependency on the deleted
`src.cli._load_benchmark_dotenv` helper and protect the current centralized
provider-settings contract without changing runtime provider behavior.

## Finding

The supplied source snapshot has no `_load_benchmark_dotenv` symbol, so
`tests/unit/test_release_hygiene.py` fails during import. Current Gemini, LLM7,
NVIDIA, Mistral, and OpenAI provider implementations already resolve credentials
through `get_provider_settings()`, whose `ProviderSettings` reads `.env` via
Pydantic Settings. A focused runtime probe confirmed that a current-working-
directory `.env` value is loaded and that an exported environment value wins over
the corresponding `.env` value.

This is therefore stale test/documentation drift, not a reason to restore a
CLI-specific dotenv loader.

## Protected behavior

This plan does not change:

- any provider implementation or live-provider routing;
- any API key, secret, `.env`, or `.env.example` file;
- analytical metrics or thresholds;
- graph/community/LDA/theme outputs;
- benchmark prompts, datasets, provider IDs, or request behavior.

## Implementation

- [x] Replace the stale `_load_benchmark_dotenv` release-hygiene test with a
      contract test against `get_provider_settings()`.
- [x] Verify `.env` loading from the current working directory.
- [x] Verify exported environment values take precedence over `.env`.
- [x] Verify settings loading does not need to mutate `os.environ`.
- [x] Add a supersession note to Plan 016 while preserving its historical
      CLI-bootstrap record.
- [x] Record the current provider-environment contract in the test matrix.
- [x] Run focused and available broader validation.
- [x] Generate and verify a task-only patch against a second pristine extraction.

## Validation

Focused checks:

```bash
python -m pytest tests/unit/test_release_hygiene.py -q
python -m pytest tests/unit/test_theme_benchmark_gemini.py tests/unit/test_theme_benchmark_llm7.py -q
python -m compileall -q src tests
git diff --check
```

Repository gates where the review environment permits:

```bash
make test-unit
make test-integration
make test
make lint
make format
```

Environment/dependency blockers are reported separately and are not hidden by
restoring obsolete behavior.

## Acceptance criteria

- `tests/unit/test_release_hygiene.py` no longer imports a deleted CLI helper.
- Provider settings load `.env` values through the current settings layer.
- Exported environment values take precedence over `.env`.
- No production source code or secret-bearing files change.
- Historical Plan 016 evidence remains intact with an explicit supersession note.

## Progress log

| Date | Update |
|---|---|
| 2026-08-12 | Verified the 13:25 source archive checksum against the supplied manifest and reproduced the baseline failure: 7 release-hygiene tests passed and only the stale `_load_benchmark_dotenv` import failed. |
| 2026-08-12 | Runtime-probed current `ProviderSettings` behavior from a temporary working directory: `.env` supplied the missing Gemini/LLM7 values, an exported Gemini value took precedence, and no CLI bootstrap was required. |
| 2026-08-12 | Replaced the stale helper test with a current settings-contract test, documented the supersession in Plan 016, and added the provider-environment contract to the verification matrix. No production source or `.env*` file was changed. |
| 2026-08-12 | Focused validation passed: `tests/unit/test_release_hygiene.py` is 8/8 green; five dependency-available Gemini/LLM7 provider guard tests pass; `tests/unit/test_current_defaults.py` is 5/5 green; and `python -m compileall -q src tests` passes. The full Gemini+LLM7 benchmark selection has 16 passes and 21 environment-blocked failures, all at Parquet fixture loading because this interpreter lacks `pyarrow`/`fastparquet`. |
| 2026-08-12 | Locked repository gates remain environment-blocked: `make test-unit`, `make test-integration`, `make test`, and `make lint` fail during `uv` dependency downloads because sandbox DNS is unavailable; Black is not installed in the review interpreter, so the formatting gate cannot run here. No blocked gate is claimed as passed. |
| 2026-08-12 | Final patch discipline passed: task-only patch generation, `git apply --check --whitespace=error-all` on a second pristine extraction, clean patch application, byte-for-byte comparison of all four affected files, and focused release-hygiene/default/provider-guard tests rerun successfully on the patch-applied copy. |
