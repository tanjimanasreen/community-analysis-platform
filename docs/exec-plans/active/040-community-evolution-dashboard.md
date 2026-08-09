# Plan 040 — Community Evolution Dashboard

Status: code-complete; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-08

## Goal

Consolidate the thesis-aligned longitudinal experience into one Community Evolution page built around persisted community paths. Preserve the existing community-transition Jaccard semantics, member-mobility semantics, and `paraphrase-MiniLM-L6-v2` thematic-similarity contract while making path, mobility, and similarity data first-class immutable artifacts that the API only reads.

## Dependencies

- Plans 004, 024–031, and 039 are complete.
- `community_transition.parquet` remains the authoritative month-to-month transition artifact.
- Community Evolution remains analytically separate from Plan 039 theme clustering/canonicalization.

## Non-goals

- Do not change IF/shared_post or WIF/weighted_post behavior.
- Do not change graph/Louvain or LDA defaults.
- Do not change transition thresholds; reply remains `0.0` and other content types remain `0.5` unless configured by the existing experiment contract.
- Do not use the Plan 039 HDBSCAN/canonical-theme embedding profile for evolution similarity.
- Do not run TEI, GPT, NetworkX, DFS path discovery, or cosine similarity in API request handlers.
- Do not remove Telegram support or existing transition/report artifacts.

## Milestones

### 1. Protect thesis path and mobility semantics

- Add branching-path regression coverage around the existing DFS transition-path behavior.
- Add explicit regression coverage for retained/new/lost/reappearing members.

### 2. Persist path-native analytical artifacts

- Persist deterministic path-step records from the accepted transition graph.
- Persist path/month membership-mobility records using `calculate_membership_changes`.
- Compute path-scoped absolute/weighted/general theme cosine-similarity records upstream when evolution similarity is enabled.
- Keep similarity computation independent of report rendering; `render_visuals` gates only visual reports.

### 3. Publish artifact contracts

- Register path, mobility, and path-theme-similarity schemas in the output contract.
- Publish them through the immutable run manifest with stable artifact keys.
- Keep similarity embedding artifacts float32, revision-pinned, and outside Memgraph.

### 4. Add read-only path APIs

- Add path summary/read endpoints.
- Add path-scoped membership mobility and thematic similarity endpoints.
- Expose resolved methodology metadata from the secret-safe run configuration.
- Keep legacy transition/persistent/membership/similarity routes for compatibility.

### 5. Consolidate the frontend Community Evolution route

- `/evolution` becomes the canonical thesis-aligned page.
- Preserve the old run-history page at `/run-history`.
- Redirect `/transitions` to `/evolution` while preserving query state.
- Replace duplicate sidebar entries with one Community Evolution entry.

### 6. Build the one-page research narrative

- Add a compact methodology strip.
- Add a persistent-path selector and structural continuity timeline.
- Add a visually distinct member-mobility flow/status view.
- Add monthly theme progression plus path-scoped cosine-similarity heatmap.
- Add a collapsible analytical evidence table.
- Reuse the existing sticky right-side `PageNavigationRail`; provide a native jump-to-section select on narrow screens.

### 7. Fixture, validation, and documentation

- Extend the deterministic dashboard fixture with path, mobility, and similarity data including a reappearing member.
- Update API/frontend contract tests and route fixtures.
- Run focused unit/frontend tests and repository gates available in the environment.
- Record blockers precisely; automated tests must not call OpenAI or TEI.

## Acceptance criteria

- `/evolution` is one page containing Community Similarity over Time, Member Mobility, and Thematic Similarity for persistent paths.
- Persistent path identity comes from the existing DFS transition semantics, not connected components.
- Path count is artifact-derived and never hard-coded.
- Member mobility exposes reappearing members.
- Evolution similarity stays on the revision-pinned `paraphrase-MiniLM-L6-v2` profile.
- `render_visuals=false` no longer suppresses path/mobility analytical artifacts.
- Similarity analytics can be enabled independently from PNG/HTML rendering.
- API handlers only read immutable artifacts/configuration; no analytical runtime executes on request.
- The right-side vertical navigation rail tracks the visible section; a mobile section selector remains accessible.
- Existing thesis metrics/defaults, Telegram support, Memgraph defaults, raw theme evidence, and old report artifacts remain unchanged.

## Progress log

### 2026-08-08 — Source-of-truth inspection

- Unpacked `community-analysis-full-review-20260808-0120.zip` as the absolute source of truth.
- Read the required harness, architecture, feature inventory, product/data/database/metric/pipeline/theme contracts, quality gates, test matrix, and relevant Plans 004/030/039 before editing.
- Confirmed the current split UX (`/evolution` run history vs `/transitions` thesis-like analysis), connected-component API persistence model, existing DFS path implementation, missing reappearing-member API field, and similarity/path computation currently gated by `render_visuals`.

### 2026-08-08 — Implementation complete

- Added a path-native Community Evolution domain read model that delegates path discovery to the existing thesis DFS implementation and assigns deterministic persisted path IDs/display order.
- Persisted `community_paths.parquet` and `community_path_membership.parquet` independently of visual rendering, including retained/new/lost/reappearing member evidence.
- Added optional `community_path_theme_similarity.parquet` plus the existing immutable float32 similarity embedding store behind `theme.evolution_similarity_enabled`; dedicated Twitter evolution configs opt in while `render_visuals` remains `false`.
- Preserved the Community Evolution `paraphrase-MiniLM-L6-v2` model/revision contract and kept Plan 039 HDBSCAN/canonicalization out of the evolution read model.
- Published the three new artifacts through output schemas, run-manifest routing, orchestration bundles, and output-contract checks.
- Added artifact-only evolution API endpoints for persisted paths, path mobility, and General/IF/WIF path theme similarity. Legacy persistent-community reads prefer persisted DFS paths while retaining an old-run connected-component fallback.
- Rebuilt `/evolution` as one thesis-aligned page with the methodology strip, persistent-path timeline, member-mobility view, monthly raw-theme progression, cosine heatmap, analytical evidence, a sticky right-side vertical navigation rail, and a narrow-screen jump selector.
- Preserved the old completed-run comparison at `/run-history`, redirected `/transitions` to `/evolution` with query parameters intact, and linked Run History from Reports.
- Extended the deterministic dashboard fixture and frontend/API contracts/tests, including a leave-and-return member so reappearance is exercised explicitly.
- Updated architecture, pipeline/theme intelligence contracts, verification matrix, and frontend baseline-route documentation.

### 2026-08-08 — Validation evidence

Passed in the available system-Python environment:

- `python -m pytest tests/unit/test_community_paths.py tests/unit/test_evolution_service_paths.py tests/unit/test_artifact_key_routing.py tests/unit/test_output_artifact_contract.py::test_evolution_output_checks_include_path_contract tests/unit/test_backend_api.py::test_openapi_contract_and_invalid_filters -q` — 14 passed.
- Python compile checks for all modified Community Evolution pipeline/API/orchestration/fixture modules.
- Direct validation of both evolution YAMLs with `python -m src.cli validate-config`.
- An offline pipeline smoke using the mock theme/similarity providers confirmed path, mobility, path-similarity, and similarity-embedding outputs are emitted while `render_visuals=false`.
- Pure deterministic fixture-row smoke confirmed two persistent paths, a reappearing member, and the pinned paraphrase similarity model provenance.
- TypeScript compiler `transpileModule` syntax parsing passed for every changed frontend source file.
- `git diff --check` passed.
- Source-of-truth comparison confirmed network metric, Louvain, LDA implementation files, and `configs/algorithms.yml` are unchanged; resolved thesis defaults and evolution model revision remain pinned.

Environment-blocked repository gates (no analytical failure was observed before the environment failure):

- `make format`: the partial sandbox `.venv` does not contain `black`.
- `make lint`: the sandbox package mirror cannot resolve the tracking dependency split (`mlflow-skinny==3.14.0`).
- `make test` and `make pipeline-preflight ...`: `uv` cannot resolve build-system `setuptools>=61.0` from the sandbox registry.
- `make frontend-check`: `frontend/node_modules` is absent and `npm ci` cannot retrieve a lockfile tarball (`yargs-parser@21.1.1`) from the sandbox registry; global `tsc` therefore cannot load the project type libraries.
- `make dashboard-fixture` and Parquet-backed system-Python tests: the partial `.venv`/system environment lacks `pyarrow`, although `pyarrow` remains present in `pyproject.toml` and the committed `uv.lock`.

Status: code-complete. The authoritative locked-environment `make format`, `make lint`, `make test`, `make frontend-check`, dashboard fixture/E2E, and real TEI-backed evolution run remain developer-environment acceptance gates because the sandbox dependency mirrors are incomplete.


### 2026-08-08 — Member-mobility serialization regression fix

- Investigated the post-Plan-040 dashboard state where valid persistent paths
  rendered zero members and zero mobility counts.
- Reproduced the production-shaped failure with NumPy scalar member IDs: the
  transition artifact persisted values such as `np.int64(1)`, which the
  path/mobility parser correctly rejected as non-literal serialized data.
- Normalized NumPy scalar member IDs to native Python scalars at the community
  transition serialization boundary without changing Jaccard calculation,
  transition thresholds, path discovery, or membership-change semantics.
- Added regression coverage for mixed NumPy integer/string member IDs and an
  end-to-end `46 -> 74 -> 37` path fixture that verifies member counts, retained
  counts, new/lost counts, and leave-and-reappear behavior survive persistence.
- Focused Community Evolution regression/API/artifact suite passed: 23 tests.
- Production-shaped in-memory smoke confirmed `46 -> 74 -> 37` persists three
  members per step, two retained members per transition, and one reappearing
  member at the final step; persisted transition member strings contain no
  NumPy scalar reprs.
- Python compile checks passed for the modified source/tests, and protected graph,
  Louvain, LDA, threshold, and algorithm-default files/configuration remain
  unchanged.
- Repository `make format`, `make lint`, and `make test` remain environment-blocked:
  the archive has no `.venv`/Black, the sandbox registry cannot resolve the
  tracking dependency split, and frozen build-system `setuptools>=61.0` cannot
  be resolved. Broader orchestration collection is also blocked by missing
  Prefect; these blockers are unrelated to the serialization fix.
