# Plan 037 — Matched-Community Theme Trends and Progression

Status: implemented — validation constrained by review-package omissions

Scope note: the persisted-path presentation on the Thematic Analysis route was superseded by Plan 038. Transition and similarity capabilities remain preserved under Community Evolution.

Owner: agent

Last updated: 2026-08-06

## Goal

Redesign the Thematic Analysis route so researchers can inspect selected-month exact themes, the dominant exact-label timeline, and persistent matched-community theme progression while retaining LDA evidence, provider provenance, and saved theme-similarity outputs.

This is a read-only presentation and deterministic aggregation change. It does not change thesis metrics, graph thresholds, Louvain, LDA, theme generation, transition generation, or similarity behavior.

## Approved review decisions

- Mockup approved on 2026-08-06.
- Default timeline range: all available theme months.
- Monthly ranking: top five exact labels.
- Exact labels remain separate; no synonym, fuzzy, embedding, or GPT regrouping is performed in the dashboard.

## Analytical definitions

### Matched pair

```text
normalized absolute_community + normalized weighted_community
```

Rows with neither ID are excluded and reported. Repeated rows for one pair and one exact label count once.

### Monthly coverage

```text
community_count = distinct matched pairs carrying the exact label
percentage = community_count / total themed matched pairs
```

General labels take precedence. IF/WIF labels are used only when no general label is present. A pair may carry multiple labels, so percentages need not total 100%.

### Timeline leader

Exact labels rank by total community-month count, months present, peak monthly count, then exact label ascending.

### Progression

Paths are derived only from saved transition rows. Saved transition labels take precedence; monthly theme evidence is joined only where a transition community ID maps unambiguously to one matched pair. Jaccard and retained-member values are displayed, not recomputed.

## Implementation

- Added complete read-only monthly and timeline aggregation endpoints.
- Added exact-label server-side filtering for paginated theme evidence.
- Added period-scoped topic/theme reads.
- Added four-month Retweet–Quote dashboard fixture data with repeated labels, multi-label pairs, keywords, and six canonical transitions.
- Added monthly top-theme, dominant timeline, progression timeline, and progression evidence components.
- Preserved matched/partial LDA evidence, metric/token controls, provider metadata, saved similarity, pagination, and network deep links.
- Removed disconnected hard-coded platform insight components.
- Added deterministic backend/model/page/fixture tests.

## Progress log

### 2026-08-06 — Source restoration

- Source archive: `community-analysis-frontend-review-20260806-0450.zip`.
- Verified SHA-256: `cfc7ea9f710248e4ff565fa7f1dfe4c31a2d653fbee26e4df155981b2830e92e`.
- Recorded source state: modified `frontend/src/pages/ThematicAnalysis.jsx`; untracked Telegram/Twitter insight components and archive metadata.
- Read repository contracts and active plans before editing.

### 2026-08-06 — Protection and implementation

- Preserved single-period fixture paths and data shapes; added longitudinal behavior only to the Retweet–Quote fixture.
- Added aggregation tests including more than 500 source rows, exact-label separation, deterministic ties, year ordering, serialized provider fields, missing pair IDs, and invalid/unavailable filters.
- Added progression tests for canonical path ranking, missing retained counts, evidence joins, period formats, and incomplete transition pages.
- Added page tests for URL state, exact-theme selection, independent pagination, progression details/deep links, unavailable states, and absence of hard-coded platform conclusions.

### 2026-08-06 — Validation

Passed:

```text
isolated pytest bootstrap for tests/unit/test_theme_trend_service.py (9 passed)
python -m py_compile <modified backend and fixture files>
tsc --noEmit --strict --target ES2022 --module ESNext --moduleResolution Bundler --skipLibCheck \
  src/features/themes/themeProgressionModel.ts \
  src/features/themes/themeTrendModel.ts
TypeScript transpileModule syntax check over 23 modified frontend TS/TSX/JS/JSX files
compiled frontend model runtime assertions
git diff --check
```

Review-package limitations:

- Full backend/API/fixture collection is blocked because the supplied review archive omits `src.artifacts` and other modules imported by the canonical fixture/API stack.
- Frontend install/check is blocked because the configured package registry does not contain `yargs-parser@21.1.1`, public registry DNS is unavailable, and `node_modules` was excluded from the archive.
- Browser screenshots, Playwright, full lint, unit suite, and production build therefore require the complete repository/dependency environment.

## Acceptance checklist

- [x] Mockup approved.
- [x] Complete monthly distinct-pair aggregation.
- [x] Exact-label timeline and deterministic leader.
- [x] No 500-row dependency for summary charts.
- [x] Complete theme periods from artifact metadata.
- [x] Persistent paths from canonical transitions only.
- [x] Fail closed on incomplete transition responses.
- [x] LDA evidence remains upstream and visible.
- [x] Existing output categories retained.
- [x] Contracts, test matrix, and handoff updated.
- [ ] Run full backend/frontend/Playwright gates in a complete checkout with dependencies available.
