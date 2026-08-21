# Plan 066 — Final Review Batch B2: Text-Preprocessor Test Reconciliation

Status: complete

## Objective

Reconcile residual text-preprocessor unit tests with the current production
responsibility boundary verified against the 2026-08-14 17:42 source snapshot,
without changing production preprocessing behavior, stopword policy, or LDA
analytical behavior.

## Classification

| Finding | Classification | Production behavior change | Analytical output change |
|---|---|---|---|
| `clean_text()` tests expect emoji and HTML processing owned by the full message pipeline | `STALE_TEST` | No | No |
| Several `clean_text()` fixtures use words that are intentionally present in the frozen custom stopword set | `STALE_TEST` | No | No |
| Unicode-normalization behavior required by the verification matrix lacks direct coverage in this focused test module | `STALE_TEST` / coverage gap | No | No |

## Protected Contracts

This plan must not change:

- `clean_text()` production logic;
- `message_preprocess()` sequencing;
- the custom stopword list;
- emoji-removal, HTML-cleaning, or Unicode-normalization production behavior;
- approved LDA implementation or defaults;
- `shared_post`, `total_post`, or `weighted_post` behavior;
- graph thresholds or Louvain defaults;
- evolution transition semantics;
- Telegram support or graph database behavior;
- provider behavior.

## Baseline Evidence

The review interpreter does not have the declared `demoji` dependency installed,
so direct collection is environment-blocked. With a temporary external import
stub used only to permit module collection (and not committed to the project),
the pristine 2026-08-14 17:42 snapshot reproduces the historical failure shape:

```text
python -m pytest -q tests/unit/test_text_preprocessor.py

7 failed, 3 passed
```

The seven failures show two stale assumptions:

1. `clean_text()` is a regex/stopword cleaning helper and does not itself run
   the emoji-removal or BeautifulSoup stages. Those stages are composed by
   `message_preprocess()` through `_preprocess_messages()`.
2. Test fixtures such as `hello`, `world`, `system`, and `going` are present in
   the current custom stopword set, so they cannot be used as expected retained
   tokens in tests whose purpose is casing, repetition, or username removal.

The verification matrix identifies `message_preprocess` as the boundary that
must cover emoji removal, HTML cleaning, Unicode normalization, and stopword
removal.

## Surgical Implementation

### B2-01 — Keep `clean_text()` tests scoped to its responsibility

File:

- `tests/unit/test_text_preprocessor.py`

Use non-stopword fixture terms for username removal, repeated-word collapse,
and lowercasing. Preserve URL, hashtag, empty-input, and stopword assertions.
Do not alter production cleaning code or the stopword list.

### B2-02 — Move composed preprocessing expectations to `message_preprocess()`

File:

- `tests/unit/test_text_preprocessor.py`

Exercise the public dataframe-level preprocessing boundary for:

- emoji removal;
- HTML tag/entity cleaning;
- Unicode normalization.

Use a minimal helper that creates one `messages` row and returns the processed
text. This verifies the current composition instead of duplicating lower-level
implementation assumptions.

### B2-03 — Preserve explicit stopword-policy coverage

File:

- `tests/unit/test_text_preprocessor.py`

Assert exact output for representative base/custom stopwords while retaining a
non-stopword signal token. The test documents the existing policy rather than
changing it.

## Validation

Focused:

```bash
python -m pytest -q tests/unit/test_text_preprocessor.py
```

Surrounding topic preprocessing coverage:

```bash
python -m pytest -q \
  tests/unit/test_text_preprocessor.py \
  tests/unit/test_topics.py
```

Protected analytical smoke coverage:

```bash
python -m pytest -q \
  tests/unit/test_current_defaults.py \
  tests/unit/test_graph_thresholds.py \
  tests/unit/test_follower_followee_metrics.py \
  tests/unit/test_louvain_defaults.py \
  tests/unit/test_lda_contract.py
```

Structural/repository gates where available:

```bash
python -m compileall -q src tests
make validate-config
make lint
make format
make test-unit
make test-integration
make test
git diff --check
```

Missing declared dependencies, DNS/network limitations, Docker/service
availability, or absent Parquet engines are recorded as `ENVIRONMENT_BLOCKER`;
production code must not be changed to bypass them.

## Acceptance Criteria

- The seven stale assertions are reconciled with current function ownership.
- `clean_text()` remains unchanged.
- `message_preprocess()` remains unchanged.
- The custom stopword list remains unchanged.
- Emoji, HTML, and Unicode behavior is tested at the composed preprocessing
  boundary.
- No production Python file is changed.
- No analytical output changes.
- Focused tests pass in a dependency-complete environment; review-sandbox
  dependency blockers are reported explicitly.
- The task-only patch applies cleanly to a second pristine extraction and all
  affected files byte-match the working implementation.

## Progress Log

| Date | Progress |
|---|---|
| 2026-08-14 | Verified the 17:42 archive SHA-256 against the supplied manifest, extracted pristine and working copies, read the mandatory contracts and relevant active plans, and reproduced the B2 baseline as 7 failed / 3 passed using only an external temporary `demoji` import stub because the review interpreter lacks the declared dependency. |
| 2026-08-14 | Reconciled only `tests/unit/test_text_preprocessor.py`: low-level `clean_text()` tests now use retained non-stopword fixtures, emoji/HTML expectations target the composed `message_preprocess()` boundary, explicit stopword coverage matches the current custom list, and Unicode normalization gained direct coverage. No production source or stopword file was changed. |
| 2026-08-14 | Focused B2 validation passed 11/11 with an external temporary `demoji` stub used only because the review interpreter lacks the declared dependency. Direct collection without the stub remains correctly classified as an environment blocker (`ModuleNotFoundError: demoji`). The surrounding `tests/unit/test_topics.py` module is additionally blocked by missing declared `kneed`. |
| 2026-08-14 | Protected current-default/graph-threshold/IF-WIF/Louvain smoke coverage passed 12/12. LDA-contract collection is blocked by missing `kneed`. `python -m compileall -q src tests` and `make validate-config PYTHON=python` passed. |
| 2026-08-14 | Repository gates were attempted and not hidden: `make format PYTHON=python` is blocked because Black is absent; `make lint`, `make test-unit`, `make test-integration`, and `make test` are blocked by DNS while `uv` attempts to resolve locked dependencies. No blocked gate is claimed as passed. |
| 2026-08-14 | Final task-only patch verification was repeated against a fresh extraction of the 17:42 ZIP: `git apply --check` and patch application succeeded, both affected files byte-matched the working implementation, focused B2 tests passed 11/11 with the external review-only `demoji` stub, protected defaults/IF-WIF/Louvain smoke tests passed 12/12, `python -m compileall -q src tests` passed, and configuration validation passed. |
