# Plan 044 — Thematic Analysis Page UX Hardening

Status: implemented; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-09

## Goal

Improve the Thematic Analysis page without changing any analytical contract. The page should explain how its results are derived, remain readable for variable timeline lengths and variable monthly theme counts, expose a consistent section-navigation rail, and present evidence in a result-to-source drill-down order.

## Source of truth

Implementation is based on `community-analysis-full-review-20260809-0151.zip` exactly as uploaded. The archive working tree, including its modified and untracked files, is the patch baseline rather than Git HEAD.

## Scope

Frontend/tests/docs only:

1. Add a concise Thematic Analysis methodology overview below the page header and above timeline controls.
2. Add stable page section anchors plus the shared right-side `PageNavigationRail` and mobile jump selector.
3. Rename monthly ranking wording to make the `up to 5` contract explicit.
4. Rework Aggregate Theme Progression into fixed-width month columns so edge labels cannot be clipped and long timelines scroll locally.
5. Wrap chart labels to at most two compact lines, preserve the full canonical label in SVG title/accessibility text, and derive rank guides from the configured display limit.
6. Preserve sparse months naturally: a month may contain fewer than five ranked canonical themes with no fabricated placeholders or warnings.
7. Reorder evidence presentation to Canonical Theme Evidence → Generated Theme Labels → Matched LDA Topic Records → Provider/Model Metadata.
8. Add focused component/page/E2E regression coverage and update the frontend test matrix/product spec where the visible contract changes.

## Analytical non-goals

- No IF/`shared_post` changes.
- No WIF/`weighted_post` changes.
- No graph-filter, Louvain, or LDA default changes.
- No HDBSCAN or canonicalization changes.
- No embedding-model or embedding-store changes.
- No provider prompt/model changes.
- No API/schema/artifact changes.
- No request-time analysis or frontend analytical repair.
- No Community Evolution methodology changes or artifact backfill.

## Required behavior

- Thematic clustering remains based on `sentence-transformers/all-MiniLM-L6-v2` and generated general-theme labels downstream of LDA evidence.
- Community Evolution remains analytically separate and continues to use its dedicated `paraphrase-MiniLM-L6-v2` profile.
- A month may legitimately expose 0–5 ranked canonical themes; the UI renders only returned themes.
- HDBSCAN noise is never promoted to fill ranking slots.
- Progression connects canonical IDs only across adjacent ranked months and preserves existing gap/re-entry semantics.
- The chart supports one month, short timelines, and long timelines without page-level horizontal overflow.
- The right navigation rail is navigation-only and does not alter analytical filters or URL state.

## Information architecture

1. Methodology Overview
2. Timeline Scope + KPI Summary
3. Top Themes by Month
4. Aggregate Theme Progression
5. Evidence Explorer
6. Canonical Theme Evidence
7. Generated Theme Labels
8. Matched LDA Topic Records
9. Provider & Model Metadata

## Validation plan

Focused checks:

- Aggregate progression component tests for sparse theme counts, one-month timelines, long timelines, long final-month labels, dynamic rank limits, and full-label accessibility.
- Thematic Analysis page tests for methodology placement, navigation sections, `up to 5` wording, evidence ordering, URL behavior, and existing evidence interactions.
- Existing theme-trend model tests for canonical identity, adjacency gaps, and re-entry semantics.
- Playwright thematic coverage for page hierarchy/navigation and local progression overflow where the environment supports it.

Repository gates to attempt:

- `make format`
- `make lint`
- `make test`
- `make frontend-check`
- focused Vitest/Playwright checks
- `git diff --check`

Environment failures will be reported exactly and will not be represented as passing.

## Progress log

### 2026-08-09 — Plan / inspect

- Verified the uploaded 2026-08-09 01:51 full-review archive as the implementation baseline.
- Read the required repository documentation and active thematic plans before editing.
- Traced the Thematic Analysis page through `ThematicAnalysis.jsx`, `MonthlyThemeMatrix.tsx`, `AggregateThemeProgression.tsx`, the canonical theme timeline model, the shared `PageNavigationRail`, and existing frontend tests.
- Confirmed the observed right-edge truncation is a chart-layout problem: month points are positioned near the SVG boundary and labels are additionally shortened to 28 characters.
- Confirmed sparse monthly rankings are valid upstream results and the frontend progression model does not synthesize or discard missing Rank 3–5 observations.


### 2026-08-09 — Protect / implement

- Added a compact, research-first methodology overview above Timeline Scope. It keeps the production derivation explicit: community messages → LDA topic evidence → generated theme labels → `all-MiniLM-L6-v2` semantic embeddings → monthly HDBSCAN plus cross-month canonicalization → monthly ranking/progression. The full Methodology page remains the detailed reference.
- Reused the shared `PageNavigationRail` and existing mobile jump-selector pattern with stable anchors for Methodology, Overview, Monthly Themes, Theme Progression, Evidence Explorer, Canonical Evidence, Theme Labels, LDA Evidence, and Provenance.
- Kept the navigation rail presentation-only; no analytical filter or URL semantics were added to it.
- Renamed the ranking UI to `Top Themes by Month` / `Up to 5 per month` and `Up to 5 themes per month`. Sparse months render only persisted ranked themes and do not receive placeholders or noise promotion.
- Reworked Aggregate Theme Progression geometry around fixed-width month columns. One-month timelines remain valid, longer timelines expand horizontally inside the chart container, and the final month receives a full half-column of label space rather than being positioned against the SVG edge.
- Replaced fixed single-line label shortening with deterministic two-line SVG wrapping while preserving each complete canonical label in the interactive point's accessible name and SVG `<title>`.
- Derived rank guide rows from the component display limit instead of a hard-coded five-row array.
- Reordered the evidence presentation to Canonical Theme Evidence → Generated Theme Labels → Matched LDA Topic Records → Provider/Model Metadata without changing the analytical dependency order.
- Added focused component/page/E2E regression coverage for sparse month counts, one-month and long timelines, long final-month labels, dynamic rank limits, methodology/navigation hierarchy, evidence ordering, local chart overflow, and page-level overflow protection.
- Updated the product spec and verification matrix only for these visible frontend contracts.
- Confirmed by exact baseline comparison that `src/`, `configs/`, `pyproject.toml`, `uv.lock`, and `Makefile` are byte-for-byte unchanged by Plan 044.

### 2026-08-09 — Validate

Passed checks available in the sandbox:

- TypeScript/JSX syntax transpilation with the globally available TypeScript compiler for every changed frontend/test file.
- Static layout/contract assertions: section-anchor order, dynamic rank guides, month-column width derivation, `up to 5` wording, and final-column right-side space for 1–24 month timelines.
- Protected-scope byte comparison against the exact uploaded snapshot: backend analytical source/configuration and protected dependency/Makefile files are unchanged.
- Secret/machine-path scan over changed files: no API keys, credentials, or machine-specific absolute paths introduced.
- Embedding-profile separation check: Thematic Analysis continues to describe/use `all-MiniLM-L6-v2`; Community Evolution remains on `paraphrase-MiniLM-L6-v2`.

Attempted gates blocked by the packaged environment/dependency registry:

- Focused Vitest command: blocked because `frontend/node_modules` is intentionally absent and `vitest` is not installed (`status 127`).
- `npm ci --ignore-scripts`: blocked by the configured internal package registry returning 404 for `yargs-parser-21.1.1.tgz`.
- `make frontend-check`: reached TypeScript typecheck but is blocked by the absent frontend dependencies (`@testing-library/jest-dom`, `vite/client`, `vitest/globals`).
- `make format`: blocked because the archived snapshot does not contain `.venv/bin/python`.
- `make lint`: dependency bootstrap is blocked because the internal registry cannot provide `mlflow-skinny==3.14.0`.
- `make test`: dependency bootstrap is blocked because the internal registry cannot resolve the build-system requirement `setuptools>=61.0`.
- Playwright/visual-regression regeneration: blocked by the same absent frontend dependency installation. The checked-in Thematic Analysis screenshot baseline predates the current canonical-theme interface and should be regenerated in a dependency-complete environment rather than fabricating a replacement in this sandbox.

Final patch validation against the exact uploaded snapshot:

- `git diff --cached --check` on a temporary Git repository seeded from the pristine uploaded working tree: **passed**.
- `git apply --check` against an independently extracted pristine copy of `community-analysis-full-review-20260809-0151.zip`: **passed**.
- Applied-patch byte comparison for all ten changed task files against the implementation working copy: **passed (10/10)**.
