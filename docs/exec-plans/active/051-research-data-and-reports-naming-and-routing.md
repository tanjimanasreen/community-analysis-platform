# Plan 051 — Research Data & Reports naming and routing

## Goal

Rename the user-facing unified Evidence workspace to **Research Data & Reports**, use **Data & Reports** in primary navigation, and make `/data-reports` the canonical route without changing analytical behavior.

## Baseline

- Source of truth: `community-analysis-full-review-20260810-0550.zip`.
- Archive SHA-256: `e1dadd3ef09fbc1acd3960e8ba13e085c6aae4fbeb61808451884ded07acbf5d`.
- The snapshot already contains Plans 045–050 working-tree state; those changes are baseline, not Plan 051 work.

## Scope

1. Sidebar label: `Data & Reports`.
2. Page/Topbar title: `Research Data & Reports`.
3. Canonical route: `/data-reports`.
4. Compatibility redirects: `/evidence`, `/data`, and `/reports`, preserving query state and explicit `view=` values; `/data` defaults to `communities`, `/reports` defaults to `outputs`.
5. Update generic workspace copy from Evidence to Data/Analytical Records where it describes the product surface rather than a legitimate analytical evidence concept.
6. Keep `features/evidence/`, `EvidencePage`, evidence model/hook names, and analytical evidence terminology unchanged internally.
7. Update first-party links, route docs, unit/E2E/accessibility/visual route expectations.

## Non-goals

- No IF/WIF, graph, Louvain, LDA, theme, HDBSCAN, evolution, artifact-schema, API, database, provider, or report-generation changes.
- No mechanical rename of the evidence feature directory or internal evidence-domain types.
- No layout redesign beyond the already-applied Plan 050 horizontal navigation.

## Tests

- Sidebar exposes `Data & Reports` at `/data-reports` and no obsolete primary Evidence/Data Explorer/Reports entries.
- Topbar shows `Research Data & Reports` and keeps the global affinity selector hidden.
- `/evidence` preserves explicit view/query state when redirecting.
- `/data` defaults to `view=communities` only when a view is absent.
- `/reports` defaults to `view=outputs` only when a view is absent.
- Canonical Evidence-model/data-query behavior remains unchanged.
- Accessibility and visual-regression routes use `/data-reports`.

## Validation

Run focused frontend syntax/tests where dependencies are available, `git diff --check`, reference scans, protected-scope byte comparison, then attempt `make frontend-check`, `make lint`, and `make test`. Environment blockers are reported rather than treated as passes.

## Progress log

### 2026-08-10 — Plan / inspect

- Verified the 05:50 archive SHA-256 and file count against the supplied manifest.
- Read the required harness, architecture, feature/product/data/database/metric/pipeline/theme contracts, quality gates, test matrix, and active Plan 048 before editing.
- Confirmed Plan 050 horizontal navigation is present in the source snapshot.
- Confirmed `/evidence` is still canonical and `Evidence` / `Research Evidence & Outputs` remain the user-facing labels.

### 2026-08-10 — Protect / implement

- Added `/data-reports` as the canonical route without renaming the internal evidence feature boundary.
- Added query-preserving compatibility redirects for `/evidence`, `/data`, and `/reports`; defaults are applied only when `view` is absent.
- Updated Sidebar, Topbar, generic workspace copy, Methodology output link, route docs, and focused unit/E2E/accessibility/visual route expectations.
- Preserved the existing `view=` values and all evidence data/query/report/download behavior.

### 2026-08-10 — Validation

- `git diff --check`: passed.
- TypeScript `transpileModule` syntax validation over all changed frontend JS/JSX/TS/TSX files: passed (17 files, 0 syntax errors).
- Protected-scope byte comparison for `src/`, `configs/`, `pyproject.toml`, `uv.lock`, `Makefile`, and `.env.example`: passed; all are unchanged from the 05:50 source snapshot.
- First-party route/reference scan confirmed `/data-reports` is canonical and remaining `/evidence` references are compatibility/internal evidence-domain references.
- Changed-line secret/local-machine-path scan: passed.
- `make frontend-typecheck`: blocked because the archive excludes `node_modules`; TypeScript cannot resolve `@testing-library/jest-dom`, `vite/client`, or `vitest/globals`.
- `make frontend-lint`: blocked because `oxlint` is unavailable.
- `make frontend-test`: blocked because `vitest` is unavailable.
- `make frontend-check`: blocked at the same missing frontend type definitions.
- `npm ci --ignore-scripts --no-audit --no-fund`: attempted to restore dependencies, but the configured internal npm registry returns HTTP 404 for `yargs-parser@21.1.1`.
- `make format`: blocked because `.venv/bin/python` is absent in the source snapshot.
- `make lint`: blocked during dependency resolution because the configured package registry does not provide `mlflow-skinny==3.14.0`.
- `make test`: blocked during build-system resolution because the configured package registry does not provide `setuptools>=61.0`.

### 2026-08-10 — Patch verification

- Generated a Plan-051-only patch against the exact 05:50 working-tree snapshot rather than repository HEAD.
- Independently extracted a second pristine 05:50 snapshot and confirmed `git apply --check` succeeds.
- Applied the patch to that pristine extraction and byte-compared every affected path against the implementation copy with zero mismatches.
