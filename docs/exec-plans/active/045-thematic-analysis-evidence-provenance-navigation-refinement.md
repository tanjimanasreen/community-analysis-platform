# Plan 045 — Thematic Analysis Evidence, Provenance & Navigation Refinement

Status: implemented; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-09

## Goal

Refine the Thematic Analysis evidence and provenance experience without changing any analytical contract. The page should make the scope of source-evidence controls explicit, keep selected canonical-cluster evidence analytically complete, summarize provider runtime metadata without losing auditability, and use one shared navigation-rail layout that fits the dashboard scroll viewport.

## Source of truth

Implementation is based on `community-analysis-full-review-20260809-1718.zip` exactly as uploaded. Its SHA-256 is `ab464b8f6ed5316533d10d2c18a6a7aaef258d4e39f2f8ca7837b7515a1a93c3`; the packaged working tree is clean at commit `a7622c39291b50c36d78bbc1877d239cca630685`.

## Scope

Frontend/tests/docs only:

1. Move selected canonical-theme cluster evidence directly below Aggregate Theme Progression and make its selection-driven scope explicit.
2. Reframe Evidence Explorer as a source-record browser whose month/community controls apply only to Generated Theme Labels and Matched LDA Topic Records, while IF/WIF view remains display-only.
3. Move Token Representation into the Matched LDA Topic Records section because it only changes topic-summary presentation.
4. Preserve current URL semantics: changing the source-evidence month clears the period-specific canonical selection; selecting a ranked theme sets both the canonical ID and its period.
5. Replace the generic provider metadata dump with compact generation configuration, operational summary, and timing summaries; keep advanced/raw metadata collapsed and preserve unknown fields.
6. Never render prompt/response payloads from provider runtime metadata in the dashboard even if an unexpected artifact contains them.
7. Fix the shared right-side navigation rail by removing page-local `h-screen` centering wrappers, tightening item spacing, and centralizing sticky positioning in a shared slot component.
8. Update focused frontend regression coverage and visible-contract documentation.

## Analytical non-goals

- No IF/`shared_post` changes.
- No WIF/`weighted_post` changes.
- No graph-filter, Louvain, or LDA default changes.
- No HDBSCAN, canonicalization, ranking, or noise-handling changes.
- No embedding model/store changes.
- No theme-generation provider, prompt, cache, or run-metric collection changes.
- No API/schema/artifact changes.
- No canonical-theme filtering added to raw theme/topic endpoints.
- No Community Evolution methodology or artifact changes.

## Protected evidence boundaries

The existing read model remains:

```text
Timeline / monthly rankings
  -> clustered-theme timeline(period range)

Selected canonical result
  -> clustered-theme evidence(period, canonical_theme_id)

Source Evidence Explorer
  -> generated themes(period, community_id)
  -> matched topics(period, community_id)
```

`canonicalThemeId` must not be sent to generated-theme or matched-topic requests. `communityId`, IF/WIF display view, and token display view must not filter canonical-cluster evidence. IF/WIF and token controls must not create request-time analytical recomputation.

## Final Thematic Analysis order

1. Methodology Overview
2. Timeline Scope + KPI Summary
3. Top Themes by Month
4. Aggregate Theme Progression
5. Selected Canonical Theme · Cluster Evidence
6. Source Evidence Explorer
7. Generated Theme Labels
8. Matched LDA Topic Records (with Token Representation control)
9. Provider & Model Provenance

The right rail and mobile section selector must use the same DOM order.

## Provider provenance presentation

Always-visible content should contain only compact persisted metadata:

- configured primary provider/model/fallback chain;
- prompt/semantic-task/schema versions when present;
- scalar runtime counts/tokens/cost;
- p50/p95/sample-count summaries derived only from persisted latency, TTFT, and TPOT sample arrays.

Provider configuration/generation digests and unknown metadata remain under **Advanced provenance**. Sanitized raw run metrics remain under **Raw run metrics**, collapsed by default. Full digest values remain available accessibly while the visual form is shortened. `prompts_and_responses` must be removed from all dashboard render paths.

## Validation plan

Focused checks:

- `useThematicAnalysisData` tests for request/query-key boundaries.
- Thematic Analysis page tests for reordered evidence hierarchy, truthful Explorer copy, URL semantics, and Token Representation placement.
- Provider metadata model/component tests for large timing arrays, p50/p95 calculation, malformed/missing values, unknown metadata, digest containment, collapsed raw metrics, and prompt-body suppression.
- Shared PageNavigationRail tests plus page smoke checks for the common sticky rail slot.
- Playwright thematic/accessibility checks where dependencies are available.

Repository gates to attempt:

- `make format`
- `make lint`
- `make test`
- `make frontend-check`
- focused Vitest/Playwright checks
- `git diff --check`

Environment failures are recorded exactly and are not represented as passing.

## Progress log

### 2026-08-09 — Plan / inspect

- Verified the 17:18 full-review archive checksum and clean source snapshot.
- Read the required harness, architecture, feature/product/data/database/metric/pipeline/theme/quality/test documentation and relevant thematic execution plans before editing.
- Traced Evidence Explorer controls through URL state, `useThematicAnalysisData`, API query parameters, and the canonical-cluster evidence query.
- Confirmed Evidence Month and Exact Community ID drive generated-theme/matched-topic reads; IF/WIF and token controls are display-only; canonical evidence is keyed only by selected period + canonical ID.
- Confirmed both Monthly Themes and Aggregate Theme Progression use the same `selectThemeEvidence` handler, so canonical evidence is selection-driven from either ranked-theme surface rather than progression-only.
- Confirmed generic rendering of persisted `run_metrics` timing arrays causes the oversized provider metadata panel.
- Confirmed all four long analytical pages duplicate `sticky top-0 h-screen justify-center` around the shared rail inside the smaller `#main-content` scroll viewport.

### 2026-08-09 — Protect / implement

- Added request-boundary regression assertions proving that generated themes and matched topics receive only period/community filters, while canonical-cluster evidence receives only period/canonical-theme identity. No API/schema change was introduced.
- Reordered Thematic Analysis to place **Selected Canonical Theme · Cluster Evidence** directly after Aggregate Theme Progression and before the source-record browser. Both Monthly Themes and Aggregate Theme Progression continue to use the existing shared canonical-selection handler.
- Renamed the filter panel to **Source Evidence Explorer** and made its scope explicit: Evidence Month and Exact Community ID filter Generated Theme Labels + Matched LDA Topic Records; IF/WIF Evidence View changes metric-specific presentation only.
- Moved **Token Representation** into the Matched LDA Topic Records header and documented that it changes topic summaries while selected-record detail continues to expose all saved unigram/bigram evidence.
- Added `providerMetadataModel.ts` as a presentation-only adapter. It preserves provider-over-model metadata precedence, extracts persisted scalar run metrics, computes deterministic p50/p95 timing summaries from persisted numeric samples, keeps unknown metadata auditable, and strips `prompts_and_responses` from every raw dashboard render path.
- Replaced the generic provider metadata grid with compact Generation Configuration, Operational Summary, and Performance Summary groups plus collapsed **Advanced provenance** and **Raw run metrics** disclosures. Long digest values are visually shortened while the complete value remains available through accessible text/title.
- Centralized sticky rail layout in `PageNavigationRailSlot`, removed duplicated page-level `h-screen` centering wrappers from Overview, Methodology, Community Evolution, and Thematic Analysis, tightened rail spacing, and gave the shared rail an explicit navigation landmark.
- Updated Thematic Analysis/mobile rail ordering to match the corrected DOM order exactly.
- Added focused unit/page/E2E regression coverage and updated the product spec/test matrix for the visible evidence/provenance/navigation contracts.
- Confirmed by byte comparison that `src/`, `configs/`, `pyproject.toml`, `uv.lock`, `Makefile`, and `.env.example` are unchanged.

### 2026-08-09 — Validate

Passed checks available in the sandbox:

- TypeScript/JSX syntax transpilation for all 14 changed frontend/test source files using the installed TypeScript compiler.
- Isolated TypeScript typecheck for `providerMetadataModel.ts` and its dependency chain (`themeModel`, artifact utilities, API types).
- Runtime assertions for provider metadata partitioning, p50/p95 interpolation, raw prompt-payload suppression, and digest shortening.
- Static evidence-boundary inspection confirms no canonical ID is added to raw theme/topic requests and no community ID is added to canonical-cluster evidence.
- Shared-rail source scan confirms the four analytical pages no longer contain the duplicated `sticky top-0 h-screen justify-center` wrapper.
- Protected-scope byte comparison against the exact 17:18 snapshot: analytical/backend source, configs, dependency lock/configuration, Makefile, and environment example are unchanged.
- Secret/machine-path scan over task files: no credentials, API keys, or machine-specific absolute paths introduced.
- `git diff --check` on the task changes: passed.

Attempted gates blocked by the packaged environment/dependency registry:

- Focused Vitest suite: blocked because `frontend/node_modules` is intentionally absent and `vitest` is not installed (`status 127`).
- `npm ci --ignore-scripts`: blocked by the configured internal npm registry returning HTTP 404 for `yargs-parser-21.1.1.tgz`.
- `make frontend-check`: reaches TypeScript typecheck but is blocked by absent frontend type packages (`@testing-library/jest-dom`, `vite/client`, `vitest/globals`).
- `make format`: blocked because the archive has no `.venv/bin/python` (`status 127`).
- `make lint`: `uv` dependency resolution is blocked because the configured package registry cannot provide `mlflow-skinny==3.14.0`.
- `make test`: package bootstrap is blocked because the configured registry cannot resolve the build-system requirement `setuptools>=61.0`.
- Playwright execution is blocked by the same unavailable frontend dependency installation; E2E assertions were updated but are not represented as executed.

Final patch verification against the exact source snapshot:

- Generated a task-only Git patch from a temporary repository seeded from the pristine 17:18 archive.
- `git diff --cached --check`: passed.
- Independently re-extracted `community-analysis-full-review-20260809-1718.zip` and ran `git apply --check`: passed.
- Applied the patch to that independent extraction and byte-compared all 17 task files to the implementation working copy: passed (17/17).
