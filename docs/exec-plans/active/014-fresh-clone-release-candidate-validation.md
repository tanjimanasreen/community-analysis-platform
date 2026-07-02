# Execution Plan: Fresh-Clone Release Candidate Validation

Status: complete

Owner: agent

Last updated: 2026-07-02

## Goal

Validate the release-candidate working tree from a clean `/tmp` copy without
relying on local virtualenvs, frontend dependencies, caches, egg-info,
generated sample outputs, or local environment files.

## Copy Details

Copy path:

```text
/tmp/community-analysis-fresh-clone-rc
```

Command:

```bash
rsync -a \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='frontend/node_modules/' \
  --exclude='frontend/dist/' \
  --exclude='frontend/.vite/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='.mypy_cache/' \
  --exclude='.ruff_cache/' \
  --exclude='*.egg-info/' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='*.env' \
  ./ /tmp/community-analysis-fresh-clone-rc/
```

## Pre-Install Generated-State Checks

All passed in the copy:

```bash
test ! -d .venv
test ! -d frontend/node_modules
test ! -d frontend/dist
test ! -d .pytest_cache
test -z "$(find . \( -name '__pycache__' -o -name '*.egg-info' -o -name '.pytest_cache' \) -print -quit)"
```

## Command Results

| Command | Result | Notes |
|---|---:|---|
| `make install-dev` | Passed after retry | Initial sandbox run failed because DNS to PyPI/package indexes was blocked. Rerun with network approval passed. |
| `make frontend-install` | Passed | Installed from `frontend/package-lock.json` with `npm ci`. |
| `make test` | Passed | 118 passed, 6 warnings. |
| `make demo` | Passed | Regenerated one-month and longitudinal sample outputs and verified output contracts. |
| `make frontend-lint` | Passed | `oxlint` completed successfully. |
| `make frontend-build` | Passed | Vite build completed without backend running. |
| `make api-smoke-test` | Passed | 12 passed, 1 warning. |
| `make clean-generated` | Passed | Removed documented demo outputs and `frontend/dist`. |
| `make clean-cache` | Passed | Removed caches and egg-info while preserving dependency installs. |
| `.venv/bin/python -m src.cli --help` | Passed | Lightweight post-clean CLI smoke check. |

## Warnings Observed

- FastAPI/Starlette TestClient deprecation warning about `httpx`.
- Tiny-fixture topic tests emitted expected numerical warnings from Gensim,
  SciPy, Kneed, and NumPy.
- These warnings are non-blocking and match earlier validation behavior.

## Cleanup Verification

All post-clean checks passed:

```bash
test -d .venv
test -d frontend/node_modules
test ! -d frontend/dist
test ! -e /tmp/community-analysis-sample-interactions.csv
test ! -d /tmp/community-analysis-sample
test ! -d /tmp/community-analysis-theme-sample
test ! -d /tmp/community-analysis-longitudinal-sample
test ! -d /tmp/community-analysis-longitudinal-theme-sample
test ! -e /tmp/community-analysis-artifact-index.md
test ! -e /tmp/community-analysis-longitudinal-artifact-index.md
test -z "$(find . \( -name '__pycache__' -o -name '*.egg-info' -o -name '.pytest_cache' -o -name '.mypy_cache' -o -name '.ruff_cache' \) -print -quit)"
```

## Skipped Checks

No required checks were skipped.

Manual browser verification of `make demo-api` plus `make demo-frontend` was
not part of this phase's required command list and was not run.

## Acceptance Status

Accepted.

- Clean copy started without generated/local dependency state.
- Fresh Python and frontend installs completed.
- Unit tests, demo workflow, frontend checks, and API smoke tests passed.
- Cleanup targets preserved `.venv` and `frontend/node_modules`.
- Cleanup targets removed documented demo outputs, frontend build output,
  caches, and egg-info.
- No thesis metrics/defaults, public output schemas, API contracts, or
  dashboard behavior were changed.
