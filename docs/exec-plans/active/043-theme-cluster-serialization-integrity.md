# Plan 043 — Canonical Theme Serialization Integrity & Defensive Rendering

Status: implemented; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-09

## Goal

Prevent malformed legacy multi-theme serialization and tuple-shaped keyword evidence from entering canonical theme clustering, while preserving the existing HDBSCAN/canonical-medoid methodology and adding bounded frontend rendering for long but valid generated text.

## Source constraints

- `general_theme_names` remains the only clustering label source.
- `general_theme_gpt` may only reconstruct saved dot-joined labels when its keys round-trip exactly to the saved `general_theme_names` value.
- LDA remains upstream evidence; no LLM cleanup/relabeling step is introduced.
- HDBSCAN configuration, embedding model/revision contract, matched-pair denominator semantics, canonical medoid selection, and Community Evolution similarity remain unchanged.
- Existing immutable runs are not rewritten by this plan.

## Implementation

1. Normalize tuple-valued list evidence at the shared theme-input boundary so `all_keywords=(...)` becomes an ordered list of individual keywords.
2. Add conservative detection for the historical dot-joined multi-theme shape. If the companion mapping is absent or does not round-trip, exclude the record from semantic observations instead of promoting the composite string as one label.
3. Preserve the matched-pair denominator for those ambiguous records and persist a separate `excluded_records_ambiguous_general_theme_serialization` diagnostic.
4. Bump monthly clustering and cross-month canonicalization contracts from `2.0` to `2.1` because the admitted observation population changes for malformed legacy records.
5. Expose the new diagnostic through the read-only API and frontend types without request-time analytical repair.
6. Bound compact canonical-theme labels and keyword chips visually while leaving the complete text in the DOM/title for evidence and accessibility.
7. Add production-shaped backend regressions, API normalization coverage, frontend layout guards, and a deterministic long-valid-label dashboard fixture case.

## Validation performed

- Focused clustering/service/generation/trend/contract/fixture command: **34 passed**.
- Python syntax compilation passes for modified backend/fixture/test modules.
- TypeScript/JSX syntax transpilation passes for all 10 modified frontend/type/test files using TypeScript 5.8.3 available in the sandbox.
- Cluster-summary writer and reporting contracts are aligned at 32 columns, including the new diagnostic.
- Protected metric, Louvain, LDA, evolution-config, theme-generation, and embedding-store files are unchanged from the 2026-08-09 01:13 source snapshot.
- `git diff --check` passes and the Plan 043 diff contains no detected secret-like values or developer absolute paths.
- Repository acceptance gates were attempted but remain environment-blocked: `make format` lacks the packaged `.venv`; `make lint` cannot resolve `mlflow-skinny==3.14.0` from the sandbox registry; `make test` cannot resolve build-system `setuptools>=61.0`; `make frontend-check` lacks the archive-excluded frontend type dependencies.
- A broader output-contract/API test attempt confirms existing environment/baseline blockers: Parquet-writing tests lack `pyarrow`/`fastparquet`, while the existing backend API fixture returns 409 against the current Parquet-era artifact contract. These are not represented as passing.

## Acceptance criteria

- Python tuple keyword evidence is emitted as individual keywords.
- A verified legacy dot-joined theme mapping still reconstructs its individual saved labels.
- An absent/mismatched mapping for a structurally ambiguous dot-joined value is excluded and counted separately from missing general themes.
- Ambiguous composite text cannot become an HDBSCAN observation or canonical medoid.
- Legitimate labels containing abbreviations such as `U.S. Immigration Policy` are not rejected.
- Monthly summary/API/frontend expose the ambiguity diagnostic.
- Compact ranking surfaces cannot be stretched vertically/horizontally by one long valid label or keyword.
- Raw theme artifacts, HDBSCAN defaults, canonical medoid behavior, IF/WIF metrics, Louvain defaults, LDA defaults, and Community Evolution methodology remain unchanged.

## Progress log

- 2026-08-09: inspected repository docs and Plan 039 before implementation.
- 2026-08-09: reproduced March-style composite-label + tuple-keyword failure directly from current source.
- 2026-08-09: implemented normalization, ambiguity exclusion/diagnostic, contract versioning, API propagation, frontend containment, fixture coverage, and regression tests.
- 2026-08-09: focused Plan 043 validation completed with 34 passing tests, Python and frontend syntax checks, protected-file checks, and `git diff --check`; environment-blocked repository gates are not represented as passing.
