# Plan 047 — Methodology Visual Compression & Diagrammatic Redesign

Status: implemented; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-10

## Goal

Refine the thesis-led `/methodology` page from seven card-heavy sections into five concise visual sections without changing methodology or analytical behavior:

1. Research Framing
2. Methodological Workflow
3. Network Models
4. System Implementation
5. Reproducibility

The redesign preserves the exact thesis research questions, Structural/Semantic/Temporal framing, LDA-before-theme interpretation, platform relationship vocabulary, historical Neo4j/current Memgraph distinction, and selected-run reproducibility data.

## Source constraints

- Treat `community-analysis-full-review-20260810-0128.zip` as the exact working-tree baseline, including Plans 045 and 046 changes.
- Preserve all protected metric and algorithm defaults.
- Preserve exact RQ wording and search-parameter-preserving links.
- Keep provider-generated themes downstream of LDA keyword evidence.
- Preserve Telegram, Twitter Retweet/Quote, and Twitter Reply relationship models.
- Do not introduce a diagram/chart dependency.

## Non-goals

- No backend/API/artifact/configuration changes.
- No IF/WIF, Louvain, LDA, HDBSCAN, theme, or Community Evolution behavior changes.
- No changes to `methodologyModel.ts` or `useMethodologyData.ts`.
- No request-time analysis or provider calls.

## Implementation

- Merge Aim & Scope and Research Questions into one `ResearchFraming` visual with Structural/Semantic/Temporal lanes, exact RQs, compact scope context, and preserved links.
- Replace the seven equal workflow cards with a shared Platform Data → Interaction Network → IF/WIF → Louvain foundation feeding three analytical branches.
- Embed RQ1/RQ2/RQ3/RQ4 at branch endpoints and remove the standalone Method → RQ presentation.
- Preserve LDA → topic keywords → generated theme interpretation and explicitly show generated themes contributing to longitudinal theme similarity.
- Refine Network Models so Telegram `FORWARDED_BY` is an actual relationship in the diagram, Retweet/Quote and Reply use directional graph flows, and all tabs resolve to the shared Creator → Spreader projection.
- Replace the repeated horizontal System Architecture pipeline with a layered System Implementation view: sources → graph/ingestion boundary → analytical pipelines → immutable artifacts → FastAPI → dashboard/reports.
- Preserve historical Neo4j and current configurable/Memgraph CE wording as separate implementation contexts.
- Keep Reproducibility behavior intact and shorten only its visible introduction.
- Reduce navigation to the five canonical sections and reuse the same list for desktop rail and mobile jump navigation.
- Remove obsolete Aim/Scope, RQ Grid, and Method→RQ components only after reference scanning confirms no remaining callers.

## Tests

- Exact four RQs and contextual links remain visible.
- Workflow foundation order is preserved.
- Structural/Semantic/Temporal branches and embedded RQ mapping render.
- LDA precedes generated theme interpretation.
- Semantic theme evidence is visibly linked to longitudinal theme similarity.
- Telegram relationships include CREATED, SENT_TO, PRODUCED/ORIGINATED, FORWARDED_BY, and FORWARDED_TO.
- Twitter tabs preserve TWEETED/RETWEETED_BY and REPLIED_BY/REPLIED_TO.
- Common Creator → Spreader IF/WIF projection remains.
- System Implementation exposes Memgraph CE, FastAPI, immutable artifacts, dashboard/reports, and keeps Neo4j historical.
- Reproducibility baseline/selected-run separation and non-OpenAI metadata remain.
- Mobile navigation exposes exactly five logical sections.

## Progress log

### 2026-08-10 — Inspect and protect

- Verified the uploaded archive SHA-256 matches the supplied manifest.
- Read the required repository documentation in the mandated order and reviewed active Plan 042 before editing.
- Inspected the current Methodology page, content model, all methodology components, page tests, Playwright methodology coverage, product spec, test matrix, and shared navigation rail.
- Confirmed the redesign can remain frontend/tests/docs-only.
- Reference-scanned the three presentation components planned for retirement and confirmed they were Methodology-page-only.

### 2026-08-10 — Implementation

- Added `ResearchFraming.tsx` and reduced the page to five primary sections.
- Refactored methodology content into explicit workflow foundation/branches and system implementation layers.
- Rebuilt the workflow as a branched visual with embedded RQ traceability and explicit LDA/theme and semantic/temporal dependencies.
- Refined platform network diagrams and made Telegram `FORWARDED_BY` visible as a relationship rather than prose.
- Reworked System Architecture into a layered System Implementation diagram.
- Kept Reproducibility data behavior intact with only concise introductory copy.
- Removed the now-unused AimScopePanel, ResearchQuestionGrid, and ResearchQuestionMapping presentation components.
- Updated focused unit/E2E expectations plus product/test documentation.

### 2026-08-10 — Validation

Passed in the available sandbox:

- Uploaded source ZIP SHA-256 matched the supplied manifest: `1e04bcda983ea031984f0af51ddac8bdb9442915fd5deea7a0564ff3230d2964`.
- `git diff --check` passed.
- TypeScript `transpileModule` syntax parsing passed for all changed frontend JS/TS/JSX/TSX files.
- Static methodology-contract assertions passed for all four exact RQs, five section IDs, shared workflow foundation, LDA-before-generated-theme ordering, semantic→temporal theme-similarity dependency, platform relationship vocabulary, common Creator→Spreader IF/WIF projection, layered implementation vocabulary, and search-preserving RQ links.
- Protected-scope byte comparison confirmed `src/`, `configs/`, `pyproject.toml`, `uv.lock`, `Makefile`, `.env.example`, `methodologyModel.ts`, and `useMethodologyData.ts` are unchanged from the source-of-truth archive.
- Secret/local-machine-path scan passed for the changed files.
- Reference scan confirmed the retired presentation components and old methodology section IDs have no remaining frontend callers.

Environment-blocked gates:

- `npm ci --ignore-scripts` cannot restore frontend dependencies because the configured npm registry returns 404 for `yargs-parser-21.1.1.tgz`.
- `make frontend-check` stops at missing `@testing-library/jest-dom`, `vite/client`, and `vitest/globals` types because `frontend/node_modules` is intentionally absent.
- `make frontend-test` cannot start because `vitest` is not installed.
- `make frontend-e2e` cannot build the dashboard fixture because the partial sandbox Python environment has no `pandas`.
- `make lint` cannot resolve the existing optional `mlflow-skinny==3.14.0` dependency from the configured registry.
- `make test` cannot resolve the existing `setuptools>=61.0` build-system dependency from the configured registry.
- The existing Methodology visual-regression baseline was not regenerated without a dependency-complete browser environment; it must be reviewed and refreshed locally after rendering the redesigned page.
