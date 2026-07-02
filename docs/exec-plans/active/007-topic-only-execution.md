# Execution Plan: True Topic-Only Execution

Status: complete

Owner: agent

Last updated: 2026-07-01

## Goal

Make `run-topics` genuinely topic-only by loading saved topic prerequisites produced by `run-social-network`, instead of recomputing network extraction, graph construction, Louvain, community extraction, or community matching.

## Context

- `src/cli.py`
- `src/pipelines/social_network_pipeline.py`
- `src/communities/messages.py`
- `src/communities/similarity.py`
- `src/topics/lda.py`
- `src/topics/topic_matching.py`
- `docs/exec-plans/active/006-cli-stage-separation.md`

## Non-Goals

- Do not change `shared_post`.
- Do not change `weighted_post`.
- Do not change graph thresholds.
- Do not change Louvain, LDA, or GPT defaults.
- Do not change public thesis output schemas.
- Do not require Neo4j, Memgraph, Docker, OpenAI, model downloads, or Kaleido.
- Do not refactor theme intelligence.

## Files Changed

- `src/topics/topic_inputs.py`
- `src/pipelines/social_network_pipeline.py`
- `src/cli.py`
- `Makefile`
- `tests/unit/test_topic_inputs.py`
- `tests/unit/test_cli_topic_only.py`
- `tests/unit/test_pipelines.py`
- `README.md`
- `code_setup.md`
- `docs/exec-plans/active/007-topic-only-execution.md`

## Milestones

### Milestone 1: Topic Input Contract

Tasks:

- [x] Add `TopicInputBundle`.
- [x] Add `build_topic_input_dir`.
- [x] Add `save_topic_inputs`.
- [x] Add `load_topic_inputs`.
- [x] Add `validate_topic_inputs`.
- [x] Preserve list-valued columns through explicit serialization/deserialization.

Validation:

```bash
.venv/bin/python -m pytest tests/unit/test_topic_inputs.py
```

### Milestone 2: Pipeline Persistence

Tasks:

- [x] Persist topic prerequisites after community matching.
- [x] Write artifacts only under the additive internal path:
  `<output_base_path>/<data_type>/_intermediate/topic_inputs/<content_type>/<month>_<year>/`.
- [x] Keep public thesis output files unchanged.
- [x] Make full pipeline consume the same saved topic-input contract before LDA.

Validation:

```bash
make run-network-sample
make run-pipeline-sample
```

### Milestone 3: Topic-Only CLI

Tasks:

- [x] Make `run-topics` load saved topic inputs.
- [x] Ensure `run-topics` does not read raw CSV input.
- [x] Ensure `run-topics` does not call network/community stages.
- [x] Return a clear error when prerequisites are missing or mismatched.

Validation:

```bash
.venv/bin/python -m pytest tests/unit/test_cli_topic_only.py
make run-topic-sample
```

## Acceptance Criteria

- [x] `run-social-network` writes topic prerequisites and stops before LDA.
- [x] `run-topics` runs only LDA/topic modeling from saved inputs.
- [x] Missing topic prerequisites explain that `run-social-network` must be run first.
- [x] Stale or mismatched manifests fail clearly.
- [x] Empty partial matches round-trip with headers.
- [x] The full offline sample remains end-to-end.

## Progress Log

| Date | Update |
|---|---|
| 2026-07-01 | Implemented true topic-only execution. Added topic-input artifact contract, persisted internal prerequisites from the network/community stage, made `run-topics` load saved inputs only, updated Makefile/docs, and added unit coverage for round trips, list columns, missing inputs, manifest mismatches, empty partial matches, and CLI topic-only behavior. Full validation is run after this progress entry. |
| 2026-07-01 | Final validation passed: `.venv/bin/python -m pytest tests/unit` passed with 77 tests; `make validate-config`, `make run-network-sample`, `make run-topic-sample`, `make run-pipeline-sample`, and `make build-report` completed offline. `run-network-sample` wrote `_intermediate/topic_inputs/...` and stopped before LDA; `run-topic-sample` loaded saved topic inputs and did not run network/community stages. |

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-01 | Store topic prerequisites under `_intermediate/topic_inputs`. | Keeps artifacts additive and avoids changing public thesis output schemas. |
| 2026-07-01 | Keep `run-all`/full pipeline end-to-end while making it exercise the saved topic-input contract. | Avoids divergent in-memory and persisted topic behavior. |

## Risks

| Risk | Mitigation |
|---|---|
| Users may run `run-topics` before `run-social-network`. | CLI now exits with a clear prerequisite message. |
| CSV list columns can reload as strings. | Topic-input module serializes list columns as JSON and parses them on load. |

## Rollback Plan

Remove `src/topics/topic_inputs.py`, restore `run-topics` to call the full pipeline, and revert the Makefile, tests, and documentation changes from this plan.
