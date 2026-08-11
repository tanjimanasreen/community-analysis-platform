# Plan 042 — Thesis-Led Methodology Page Redesign

Status: implemented; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-10

Presentation note: Plan 047 refines the implemented seven-section card hierarchy into five diagrammatic sections; the thesis-content and analytical constraints defined here remain authoritative.

## Goal

Redesign `/methodology` into a concise, thesis-led explanation of the research rather than a provenance-first technical reference. The page should answer, in order:

1. what the study investigates;
2. which research questions guide it;
3. how the methodological workflow answers those questions;
4. how the current system realizes that workflow;
5. how Telegram and Twitter interaction models project into the shared analytical network;
6. how baseline methodology and selected-run metadata remain reproducible.

The methodological workflow is the dominant visual. Reproducibility and selected-run provenance remain available as secondary detail.

## Source constraints

- Preserve the exact four thesis research questions.
- Preserve the thesis distinction between structural, semantic, and temporal analysis.
- Preserve LDA as the analytical topic-modeling stage; downstream provider-generated theme labels remain interpretations of LDA keyword evidence.
- Distinguish the historical thesis graph implementation (Neo4j) from the current production graph-store boundary (Memgraph Community Edition by default).
- Reuse existing thesis defaults and selected-run metadata models; do not infer baseline defaults for a selected run when metadata is absent.

## Non-goals

- No backend, API, artifact, pipeline, graph-store, or analytical algorithm changes.
- No changes to `shared_post`, `weighted_post`, graph thresholds, Louvain, LDA, community transition, member mobility, theme similarity, or clustering.
- No new charting/diagram dependency.
- No changes to Telegram/Twitter support or provider behavior.
- No pipeline rerun requirement.

## Milestones

### 1. Protect existing methodology provenance behavior

- Preserve `THESIS_BASELINE` and `methodologyRunView()`.
- Preserve selected-run resolved configuration, provider/model metadata, and artifact categories.
- Preserve non-OpenAI provider support and search-parameter-preserving dashboard links.
- Expand tests before/with the redesign so baseline and selected-run values remain visibly separate.

### 2. Add a thesis methodology content model

- Centralize Aim/Scope, exact RQs, workflow stages, architecture stages, network explanatory models, and RQ-method mapping in `frontend/src/features/methodology/methodologyContent.ts`.
- Keep the content model presentation-safe and independent of API data.

### 3. Build the research narrative

- Add a concise hero and Aim & Scope panel with Structural / Semantic / Temporal dimensions.
- Promote the exact RQs to four compact cards linked to the relevant analytical dashboard pages while preserving current search params.
- Build a seven-stage methodological workflow as the visual centerpiece.
- Visually group workflow stages into structural, semantic, and temporal dimensions.

### 4. Add supporting architecture views

- Add a simplified current system architecture that connects platform sources, the graph-store/processing boundary, analysis modules, persisted artifacts, and the read-only API/dashboard.
- Add a tabbed Network Architecture view for Telegram, Twitter Retweet/Quote, and Twitter Reply.
- Show each platform-specific interaction pattern resolving into the common monthly Creator → Spreader analytical projection and IF/WIF edge definitions.
- Add a compact Method → RQ mapping.

### 5. Move technical detail into Reproducibility

- Move protected defaults, IF/WIF definitions, selected-run metadata, provider/model metadata, and artifact categories into a compact `Reproducibility & Analytical Contract` section.
- Use collapsible/native details where appropriate.
- Keep Thesis baseline and Selected run visually and semantically distinct.

### 6. Navigation, responsive behavior, and accessibility

- Reuse `PageNavigationRail` on desktop for Aim & Scope, Research Questions, Workflow, System, Network, RQ Mapping, and Reproducibility.
- Add the existing native mobile `Jump to section` interaction pattern.
- Ensure network tabs use accessible button/tab semantics and selection is not color-only.
- Ensure diagrams remain understandable from text without hover or decorative arrows.
- Avoid full-page horizontal overflow at narrow widths.

### 7. Tests, docs, and validation

- Expand `MethodologyPlan030.test.jsx` for thesis content, exact RQs, workflow order, tabs, selected-run provenance, search-param-preserving links, and mobile section navigation.
- Update Playwright shell/accessibility coverage for the new page heading and interactions.
- Update product specification and test matrix.
- Run focused frontend checks and repository gates available in the environment.

## Acceptance criteria

- Page heading is `Methodology`, not `Methodology and run provenance`.
- Aim & Scope appears before technical provenance.
- All four exact thesis RQs are visible as distinct cards.
- The methodological workflow is the dominant full-width explanatory visual.
- Workflow preserves LDA → downstream theme interpretation ordering.
- Structural, Semantic, and Temporal dimensions are visible without paragraph-heavy explanation.
- System Architecture is clearly labeled as the current implementation and does not misstate historical Neo4j as current production storage.
- Network Architecture provides Telegram, Twitter Retweet/Quote, and Twitter Reply tabs and a shared Creator → Spreader projection.
- A concise Method → RQ mapping is visible.
- Protected thesis defaults and selected-run metadata remain available under Reproducibility and remain distinct.
- Right-side section rail and mobile jump selector work.
- No backend, API, artifact, configuration, dependency, or analytical behavior changes occur.

## Progress log

### 2026-08-08 — Source-of-truth inspection

- Unpacked `community-analysis-full-review-20260808-2036.zip` as the absolute source of truth.
- Read the required harness, architecture, feature inventory, product/data/database/metric/pipeline/theme contracts, quality gates, test matrix, and active Plan 041 before editing.
- Inspected the current Methodology page, methodology model/hook, page tests, PageNavigationRail, application routes, Playwright shell/accessibility coverage, product spec, and frontend test matrix.
- Rechecked the thesis Research Objectives/Questions and methodology/network-model descriptions to preserve exact RQ wording and platform relationship semantics.
- Confirmed this plan can remain frontend/tests/docs-only while reusing the current methodology API read model.


### 2026-08-08 — Implementation

- Rebuilt `/methodology` around the agreed thesis-first hierarchy: Aim & Scope → Research Questions → Methodological Workflow → System Architecture → Network Architecture → Method → RQ mapping → Reproducibility.
- Added a centralized `methodologyContent.ts` model containing the exact thesis RQs, research dimensions, workflow stages, system stages, network modes, and method/RQ traceability.
- Added compact Aim/Scope and four RQ cards with search-parameter-preserving links to Network, Thematic Analysis, and Community Evolution.
- Added the seven-stage workflow as the dominant visual and explicitly preserved LDA → downstream theme interpretation ordering.
- Added a current-system architecture view that retains the thesis A–D stage model and clearly distinguishes the historical Neo4j implementation from the current configurable graph-store boundary with Memgraph Community Edition as the default local target.
- Added keyboard-accessible Telegram, Twitter Retweet/Quote, and Twitter Reply network tabs using the thesis relationship vocabulary, each resolving to the shared monthly Creator → Spreader projection with IF/WIF definitions.
- Moved protected defaults, affinity definitions, selected-run configuration/model metadata, artifact categories, and the artifact-library link into collapsed Reproducibility details.
- Reused the existing right-side `PageNavigationRail` and added the mobile native Jump to Section pattern.
- Expanded Methodology component coverage and Playwright shell/accessibility coverage, then updated the product spec and frontend test matrix.
- No backend, API, artifact, configuration, dependency, metric, Louvain, LDA, theme, or evolution code was changed.

### 2026-08-08 — Validation

Passed in the available sandbox:

- Verified the uploaded source ZIP SHA-256 is `ec5f28908217447965d97e47f16178b66a22a3daf47a0b83d7d107b937c22fd9`, matching the supplied manifest.
- TypeScript 5.8.3 `transpileModule` syntax parsing passed for every changed Methodology source/test file and the modified Playwright specs.
- Static contract assertions passed for all four exact RQs, Structural/Semantic/Temporal dimensions, seven workflow stages, LDA-before-theme ordering, Telegram/Twitter relationship labels, common Creator → Spreader projection, current Memgraph vs historical Neo4j wording, and all section IDs.
- Protected scope comparison confirmed `src/`, `configs/`, `pyproject.toml`, `uv.lock`, `Makefile`, `methodologyModel.ts`, and `useMethodologyData.ts` are unchanged from the source-of-truth archive.
- Secret/machine-path scan passed for Plan 042 files.
- `git diff --check` passed.

Environment-blocked acceptance gates:

- `npm ci --ignore-scripts` cannot restore frontend dependencies because the sandbox npm registry returns 404 for the locked `yargs-parser-21.1.1.tgz` artifact.
- Focused Methodology Vitest cannot start without `frontend/node_modules` (`vitest: not found`).
- `make frontend-check` reaches TypeScript and stops because the intentionally excluded frontend dependencies provide `@testing-library/jest-dom`, `vite/client`, and `vitest/globals` type libraries.
- `make frontend-e2e` cannot build the deterministic dashboard fixture because the partial sandbox Python environment has no `pandas`.
- `make test` cannot resolve the existing `setuptools>=61.0` build-system requirement from the sandbox registry.
- `make lint` cannot resolve the existing tracking split because `mlflow-skinny==3.14.0` is unavailable from the sandbox registry.
- `make format` cannot run because the partial `.venv` does not contain `black`.
- The existing Methodology visual-regression baseline must be intentionally regenerated/reviewed in a normal frontend environment because this plan deliberately changes that page's appearance.

Developer-environment acceptance gates remain: focused Methodology Vitest, `make frontend-check`, Methodology Playwright/axe coverage, visual baseline review/update, and the repository test/lint gates.
