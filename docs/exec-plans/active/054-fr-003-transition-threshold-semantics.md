# Plan 054 — FR-003 Transition Threshold Semantics

Status: code-complete; environment acceptance gates pending

Owner: agent

Last updated: 2026-08-11

## Goal

Resolve Codex FR-003 by making the existing community-transition acceptance
semantics explicit and regression-tested without changing analytical output.
A transition requires positive member overlap. The configured threshold remains
an additional lower bound.

Approved transition contract:

```text
accept when Jaccard > 0 and Jaccard >= configured threshold
```

Therefore:

- Reply keeps `reply_transition_threshold = 0.0` and accepts any positive
  Jaccard score.
- Other content types keep `transition_threshold = 0.5` and accept Jaccard
  scores greater than or equal to `0.5`.
- Zero-overlap community pairs are never transitions.

## Protected analytical behavior

This plan does not change:

- `shared_post` or `weighted_post`;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- the approved production LDA contract;
- transition threshold values (`0.0` for reply, `0.5` otherwise);
- Jaccard calculation or transition output columns/order;
- the positive-overlap candidate index optimization;
- DFS path construction, membership mobility, or thematic similarity;
- Telegram/Twitter support, provider behavior, API contracts, or frontend behavior.

## Tasks

- [x] Add regression coverage for zero-overlap exclusion at threshold `0.0`.
- [x] Add regression coverage for positive-overlap acceptance at threshold `0.0`.
- [x] Protect the inclusive `Jaccard == 0.5` non-reply boundary.
- [x] Protect rejection below the non-reply `0.5` threshold.
- [x] Make the positive-overlap acceptance rule explicit in runtime code while
      retaining the indexed candidate pruning.
- [x] Clarify the algorithm configuration comment and authoritative contracts.
- [x] Remove stale test commentary that describes the old strict `> 0.5`
      boundary.
- [x] Run focused and available broader validation.
- [x] Generate and verify a task-only patch against a second pristine extraction.

## Validation

Focused checks:

```bash
python -m pytest tests/unit/test_community_transition.py tests/unit/test_transitions.py -q
python -m pytest \
  tests/unit/test_current_defaults.py \
  tests/unit/test_evolution_configs.py \
  tests/unit/test_evolution_service_paths.py -q
```

Repository gates where the review environment permits:

```bash
make run-evolution-pipeline-test
make format
make lint
make test
git diff --check
```

The known offline evolution-test TEI dependency from FR-002 remains separate
from this plan and must not be solved by making TEI mandatory.

## Acceptance criteria

- `Jaccard == 0` is explicitly rejected even when the configured threshold is
  `0.0`.
- Every positive Jaccard score is eligible for reply transitions when the
  configured threshold is `0.0`.
- `Jaccard == 0.5` remains accepted for the normal non-reply threshold.
- Jaccard values below `0.5` remain rejected for the normal non-reply threshold.
- Runtime code, configuration comments, contracts, and tests describe the same
  semantics.
- Representative transition results are unchanged from the pristine baseline.
- No protected metric/default, downstream path logic, schema, API, or frontend
  behavior changes.

## Progress log

| Date | Update |
|---|---|
| 2026-08-11 | User approved interpretation B: threshold `0.0` means any positive-overlap community pair, not zero-overlap pairs. Created Plan 054 as a behavior-preserving contract-hardening task separate from Plan 053. Baseline focused transition tests passed: 7 tests. |
| 2026-08-11 | Implemented the approved contract surgically: the optimized positive-overlap candidate index is unchanged, while the final acceptance predicate now explicitly requires `Jaccard > 0` in addition to the configured threshold. Updated the algorithms comment and transition contracts, added reply zero-threshold/positive-overlap regression coverage, and corrected the stale strict-`> 0.5` test commentary. Focused transition tests passed (8 tests); evolution config/service path tests passed (10 tests); pristine-vs-working behavior probes for `J=0`, `1/3`, `0.4`, `0.5`, and `1.0` were byte-identical. Protected graph/Louvain/LDA/transition defaults were re-parsed and confirmed unchanged. |
| 2026-08-11 | Broader gate evidence: the combined defaults/evolution regression selection has one pre-existing provider fallback-model assertion failure, reproduced identically in the pristine baseline. `make run-evolution-pipeline-test` and `make format` cannot start because the archive intentionally has no `.venv`. `make lint` and `make test` attempted locked dependency resolution but are blocked by sandbox DNS/download failures (`virtualenv` and `tiktoken`, respectively). These blockers are unrelated to FR-003. |
| 2026-08-11 | Patch discipline completed against the supplied source-of-truth archive: generated a task-only patch, verified it with `git apply --check` on a fresh second extraction, applied it successfully, and byte-compared all affected files against the working copy. |
