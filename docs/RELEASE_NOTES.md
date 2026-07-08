# Release Notes

## Summary

Plans 007-014 modernized the project into a reproducible, offline-safe,
stage-separated community-analysis workflow with verified outputs, a read-only
artifact API, and a read-only dashboard.

## Completed Work

- Plan 007: `run-topics` is truly topic-only and loads saved topic-input
  artifacts.
- Plan 008: `run-theme-analysis` is truly theme-only and loads saved LDA/theme
  inputs.
- Plan 009: two-month longitudinal sample validation proves month-to-month
  transition outputs.
- Plan 010: public and internal output artifact contracts are frozen and
  verified.
- Plan 011: read-only FastAPI artifact API serves generated outputs under
  `/api/v1`.
- Plan 012: Vite/React dashboard consumes only the read-only `/api/v1` API.
- Plan 013: reproducible install, demo, cleanup, dependency, and generated-file
  hygiene commands are in place.
- Plan 014: fresh-copy release-candidate validation passed from
  `/tmp/community-analysis-fresh-clone-rc`.

## Validation Snapshot

Successful validation includes:

- `make test`: 118 unit tests passed.
- `make demo`: one-month sample, longitudinal sample, output verification,
  report indexing, and API smoke tests passed.
- `make frontend-lint`: dashboard lint passed.
- `make frontend-build`: dashboard build passed without the backend running.
- `make api-smoke-test`: backend API smoke tests passed.
- Fresh-copy validation confirmed no hidden local state was required.

## Known Limitations

- Database workflows remain optional; the default demo does not require Neo4j,
  Memgraph, or Docker.
- Real OpenAI theme generation is optional; tests and demos must remain
  offline-safe and must not call OpenAI.
- Visualization rendering is optional; missing Sankey, membership-change, or
  similarity files are expected when rendering is disabled.
- The dashboard is read-only and intentionally does not include pipeline-run
  controls.
- Dependency declarations prioritize reproducible current behavior over minimal
  optional-extra splitting.

## Future Work

- Add richer dashboard visualizations using the existing read-only API.
- Add deployment hardening for the backend, such as authentication and
  configured CORS origins.
- Split optional heavy dependencies into extras if a lighter install profile is
  needed.
- Add a real-data runbook for non-fixture datasets and optional database usage.
- Expand report generation beyond the current artifact index if a thesis
  reporting package is needed.
