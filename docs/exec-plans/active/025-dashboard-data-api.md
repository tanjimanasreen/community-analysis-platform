# Plan 025 — Dashboard Data API

## Goal

Build a small, read-only FastAPI layer over validated run-scoped artifacts.
The API is a presentation/read model only. It must not execute analytical,
database, embedding, provider, or visualization-generation code.

## Scope

- Discover canonical runs below `<artifact_root>/runs/<run_id>/`.
- Read and validate `manifest.json` and manifest-listed artifacts.
- Provide stable `/api/v1` schemas for runs, overview, networks, communities,
  topics, themes, evolution, reports, and downloads.
- Enforce pagination and bounded graph responses.
- Return explicit structured errors for missing, invalid, or tampered artifacts.
- Keep all analytical calculations outside the request path.
- Preserve all existing pipeline and CSV behavior.

## Non-Goals

- Running NetworkX, Louvain, LDA, GPT, TEI, or pipeline stages.
- Mutating artifacts or repairing invalid runs.
- Querying raw source data or graph databases.
- Authentication, Redis, background jobs, or cloud deployment.
- Frontend implementation.

## Acceptance Criteria

- The dashboard can operate from documented API responses only.
- API readers resolve files exclusively through manifest artifact keys.
- Broken artifacts are rejected before their contents are returned.
- Graph responses enforce configured node and edge limits.
- Report and download endpoints cannot escape the run root.
- OpenAPI schemas remain deterministic and versioned under `/api/v1`.
- Tests prove pipeline/model modules are not imported during API requests.

## Progress Log

### 2026-07-17

- Plan created from the approved dashboard data API roadmap.

### 2026-07-17 — Implementation

- Added `src/api` with versioned schemas, read-only services, routers, and an
  application factory.
- Added cached run discovery and checksum-keyed CSV caching without eager
  startup loading.
- Added manifest-only artifact resolution, selected-artifact verification,
  pagination, graph caps, chart-ready transformations, report serving, and
  structured errors.
- Added focused tests for filters, OpenAPI schemas, pagination, graph limits,
  tampering, path escape, optional artifacts, reports, and analytical isolation.
- Updated the API command and repository contracts to use the canonical
  run-scoped artifact root.

## Validation Record

### 2026-07-17

Passed in the available offline environment:

```bash
python -m compileall -q src/api src/artifacts tests/unit/test_backend_api.py
python -m pytest -q \
  tests/unit/test_backend_api.py \
  tests/unit/test_run_manifest.py \
  tests/unit/test_output_artifact_contract.py \
  tests/unit/test_tracking_summaries.py
```

Result: `31 passed`.

A broader regression selection covering thesis defaults, IF/WIF metrics, graph
thresholds, Louvain defaults, configuration, artifact contracts, tracking
contracts, sanitization, summaries, and the API also passed: `62 passed`.

The full repository suite could not be collected in this sandbox because the
locked optional/runtime dependencies (`prefect`, `mlflow`, `kneed`, `demoji`,
and related packages) were unavailable and outbound package downloads were
blocked. Run the normal dependency-complete gates after applying the patch:

```bash
make format
make lint
make test
```
