# Plan 055 — FR-004 Parquet Artifact Contract

Status: code-complete; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-11

## Goal

Resolve Codex FR-004 by aligning generated artifact writers, verification,
tests, and current documentation with the user-approved storage contract:

```text
raw external relationship inputs under data/raw/** -> CSV
generated analytical/intermediate tabular artifacts -> Parquet
```

The earlier promise to preserve generated public CSV compatibility artifacts is
explicitly retired. New runs must not rely on CSV/Parquet suffix fallback when
verifying generated outputs.

## Protected analytical behavior

This plan does not change:

- `shared_post` or `weighted_post`;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- the approved production LDA contract;
- GPT/theme semantics, transition thresholds, DFS paths, membership mobility,
  theme similarity, HDBSCAN, or embedding-model separation;
- raw legacy `source,target,relation` CSV ingestion;
- Telegram, Twitter Reply, or Twitter Retweet/Quote support;
- Memgraph CE as the default local graph database.

## Scope

- Make the core generated-output contract Parquet-only.
- Keep raw relationship CSV ingestion/export compatibility at the external data
  boundary.
- Keep readers capable of opening older derived CSVs where that compatibility is
  already isolated and does not cause new runs to emit CSV.
- Do not migrate benchmark review exports or rewrite historical execution-plan
  evidence; this FR concerns production analytical/intermediate artifacts.

## Tasks

- [x] Make social-network generated filenames explicitly Parquet instead of
      passing `.csv` names through a suffix-rewriting helper.
- [x] Make standalone generated derived-interaction output/export Parquet-only.
- [x] Change output-contract checks to require the exact `.parquet` paths and
      remove CSV/Parquet suffix fallback.
- [x] Align matched-LDA/theme-input schema comparison with Parquet paths.
- [x] Update sample Make targets and artifact-index roots to generated Parquet.
- [x] Update focused output-contract, ingestion, graph-store, and artifact-index
      tests.
- [x] Update authoritative architecture/product/data/database/pipeline/theme/
      output/verification documentation.
- [x] Mark the generated-CSV clauses in Plans 010 and 024 as superseded by this
      approved migration decision.
- [x] Run focused validation and available repository gates.
- [x] Generate a task-only patch and verify it against a second pristine
      extraction.

## Validation

Focused checks:

```bash
python -m pytest \
  tests/unit/test_output_artifact_contract.py \
  tests/unit/test_ingestion_pipeline.py \
  tests/unit/test_memgraph_repository.py \
  tests/unit/test_artifact_index.py -q
python -m compileall -q src tests
```

Repository gates where the review environment permits:

```bash
make verify-output-contract
make verify-evolution-output-contract
make format
make lint
make test
git diff --check
```

The source archive intentionally excludes `.venv`, generated outputs, and large
raw datasets. Missing `pyarrow` or locked-dependency download failures in the
review sandbox must be reported as environment blockers rather than treated as
analytical failures.

## Progress log

| Date | Update |
|---|---|
| 2026-08-11 | User approved the FR-004 contract decision: raw `data/raw/**` relationship inputs remain CSV; all generated analytical/intermediate tabular artifacts should be Parquet for performance, easier access, and future AWS/object-storage integration. Dual-writing generated CSV compatibility copies was explicitly rejected. |
| 2026-08-11 | Implemented the approved Parquet-only generated-artifact contract. Social-network outputs now use explicit `.parquet` filenames; standalone derived-interaction writes/exports reject generated CSV; raw `source,target,relation` ingestion remains CSV; existing readers may still consume older derived CSVs. Output verification now requires exact Parquet paths with no suffix fallback. Current docs, sample/runbook paths, and directly related tests were aligned; Plans 010, 019, and 024 retain historical evidence with Plan-055 supersession notes. |
| 2026-08-11 | Focused no-PyArrow contract checks passed (11 distinct tests across output-path enforcement, raw CSV boundary, generated-CSV rejection, CLI Parquet routing, and artifact indexing). `python -m compileall -q src tests` passed. Full Parquet-writing focused tests are blocked because the review interpreter has neither `pyarrow` nor `fastparquet`; `pyproject.toml` declares `pyarrow>=12.0.0` and the lockfile pins `pyarrow==24.0.0`. One unrelated stale `CachedProvider` test failure was reproduced in the pristine baseline. A pre-existing Memgraph raw-import assertion failure was also reproduced in the pristine baseline. |
| 2026-08-11 | Broader gates: `make verify-output-contract`, `make verify-evolution-output-contract`, and `make format` cannot start because the source archive intentionally excludes `.venv`. `make lint` attempted locked dependency resolution but failed on sandbox DNS while downloading NumPy. `make test` likewise entered locked dependency resolution and was terminated by the review timeout while network access was unavailable. |
| 2026-08-11 | Patch discipline completed against the supplied source-of-truth archive: `git diff --check` passed in a temporary baseline repository, the task-only patch passed `git apply --check` on a fresh extraction, applied successfully, and every affected file byte-compared equal to the working copy. |
