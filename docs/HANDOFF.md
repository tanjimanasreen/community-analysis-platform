# Final Handoff

This handoff summarizes the current community-analysis project state for the
next maintainer or presenter.

## Architecture Summary

- CLI pipeline: `src.cli` exposes ingestion, network/community, topic, theme,
  output verification, and report-index commands.
- Network/community stage: `run-social-network` writes public thesis CSVs and
  internal topic-input artifacts.
- Topic-only stage: `run-topics` loads
  `_intermediate/topic_inputs/...` and runs only LDA/topic export.
- Theme-only stage: `run-theme-analysis` loads
  `_intermediate/theme_inputs/...` and runs only theme intelligence.
- Output verifier: `verify-output-contract` validates public output schemas,
  internal manifests, and theme-input hashes without rerunning the pipeline.
- Artifact index: `build-report` writes a lightweight Markdown index of
  generated outputs.
- Read-only API: FastAPI serves generated artifacts under `/api/v1`; it does
  not run or mutate pipeline stages.
- Read-only dashboard: Vite/React consumes only `/api/v1` and has no controls
  that run ingestion, analysis, models, databases, or visualization rendering.

## Main Commands

Fresh setup:

```bash
make install-dev
make frontend-install
```

Offline proof:

```bash
make demo
make frontend-lint
make frontend-build
```

Manual demo:

```bash
make demo-api
make demo-frontend
```

Cleanup:

```bash
make clean-generated
make clean-cache
```

## Generated Outputs

One-month sample:

```text
/tmp/community-analysis-sample/
/tmp/community-analysis-theme-sample/
/tmp/community-analysis-sample-interactions.csv
/tmp/community-analysis-artifact-index.md
```

Longitudinal sample:

```text
/tmp/community-analysis-longitudinal-sample/
/tmp/community-analysis-longitudinal-theme-sample/
/tmp/community-analysis-longitudinal-artifact-index.md
```

The frozen artifact schema is documented in
`docs/design-docs/output-artifact-contract.md`.

## Commit Checklist

Commit:

- source code
- configs
- tests and fixtures
- docs
- `frontend/package-lock.json`
- `.env.example` files

Do not commit:

- `.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `src/*.egg-info/`
- `__pycache__/`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- generated sample outputs or report files
- local `.env` files

## Validation Summary

Latest fresh-copy release-candidate validation passed:

- `make install-dev`
- `make frontend-install`
- `make test`
- `make demo`
- `make frontend-lint`
- `make frontend-build`
- `make api-smoke-test`
- `make clean-generated`
- `make clean-cache`
- `.venv/bin/python -m src.cli --help`

See `docs/exec-plans/active/014-fresh-clone-release-candidate-validation.md`
for exact commands, warnings, and cleanup checks.

## Known Warnings

- FastAPI/Starlette emits a TestClient deprecation warning related to `httpx`.
- Tiny LDA fixtures can emit numerical warnings from Gensim, SciPy, Kneed, or
  NumPy.
- These warnings are non-blocking and were present during successful
  validation.

## Guardrails

Do not change thesis metric definitions, graph thresholds, Louvain defaults,
LDA defaults, GPT defaults, public output schemas, API contracts, or dashboard
behavior without a new documented plan and validation pass.
