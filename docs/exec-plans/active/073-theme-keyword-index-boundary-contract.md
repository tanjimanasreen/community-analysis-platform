# Plan 073 — Theme Keyword-Index Boundary Contract

## 1. Objective
Harden the Plan 071 indexed-theme provider contract so every request exposes an unambiguous, request-bounded zero-based evidence-ID domain without changing LDA evidence, generated-theme semantics, or downstream analytical behavior.

## 2. Production Evidence
The Twitter `retweet_quote` evolution run failed on input hash `cb0db3cac2295a5ebc60af239977dcc9bdab3bdb054f3eee6fda917aaf750917` after OpenAI returned `keyword index 12` for a payload containing exactly 12 ordered keywords. Valid zero-based evidence IDs were therefore `0..11`.

The response completed normally (`content_filter_summary=none`); the existing local validator correctly rejected the out-of-range reference. The static provider schema allowed any non-negative integer because it declared `minimum: 0` without a request-specific `maximum`.

## 3. Root Cause
Plan 071 correctly moved supporting evidence to `keyword_indices`, but two ambiguity gaps remained:

1. the provider-facing schema did not bound indices to the current keyword count;
2. the prompt showed an unnumbered keyword array, requiring the model to infer zero-based positions.

The local validator protected evidence integrity by failing instead of repairing or dropping the invalid index. That validator remains authoritative and unchanged.

## 4. Protected Contracts
This plan must not change:
- LDA keyword values, order, normalization, or input hashing;
- `shared_post`, `total_post`, or `weighted_post` behavior;
- graph thresholds, Louvain defaults, or LDA defaults;
- IF/WIF community matching, transitions, paths, or membership mobility;
- Telegram/Twitter ingestion or network semantics;
- Plan 071 safety-failure semantics, retries, provenance, or fallback routing;
- theme label fidelity/severity requirements;
- embeddings, cosine similarity, or HDBSCAN behavior.

## 5. Approved Surgical Change
- Bump the centrally defined prompt contract from `v2` to `v3` because the provider-visible prompt presentation changes.
- Keep `OUTPUT_SCHEMA_VERSION = 2`; the output shape remains `name + keyword_indices`.
- Derive a fresh request-local output schema from the immutable canonical V2 shape. For `N` keywords, `keyword_indices.items` requires `minimum: 0` and `maximum: N - 1`.
- Never mutate the shared global schema; concurrent requests may have different keyword counts.
- Render the exact same ordered keywords with explicit canonical IDs such as `[0] "keyword"`, `[1] "keyword"`, and instruct the model to return only those shown IDs without renumbering or one-based conversion.
- Preserve the existing application-side strict index validator as defense in depth. Do not clamp, decrement, drop, or otherwise repair invalid references.
- Use the request-local schema in structured-output provider calls that accept a JSON Schema; providers using JSON-object mode still receive the bounded schema through the canonical system prompt.

## 6. Cache and Provenance
The original keyword JSON used for `input_hash` remains unchanged, so the confirmed Twitter hash remains stable. Prompt V3 and the request-bounded schema change the prompt hash and existing orchestration/cache keys already include the central prompt-contract version, preventing V2 results from satisfying V3 execution.

## 7. Tests
Required offline regression coverage:
1. request-local bounds for keyword counts 1, 5, 12, and 26 are 0, 4, 11, and 25;
2. the canonical shared schema remains unmutated/unbounded;
3. the exact 12-keyword Twitter payload retains input hash `cb0db3cac229...`;
4. Prompt V3 visibly renders `[0]` through `[11]` and no `[12]` for that payload;
5. local normalization accepts index 11 and rejects index 12;
6. OpenAI strict structured output receives `maximum = len(keywords) - 1`;
7. existing Plan 071 content-filter/recovery tests remain green;
8. no automated test performs a live provider call.

## 8. Validation
Run focused provider/theme tests first, then broader offline provider/benchmark tests where dependencies permit:

```bash
python -m pytest -q tests/unit/test_theme_content_filter_recovery.py tests/unit/test_openai_provider.py
python -m compileall -q src tests
make validate-config PYTHON=python
make lint
make test
```

Parquet/Prefect or optional-provider environment blockers must be reported separately and must not be bypassed by changing production behavior.

## 9. Progress Log
- 2026-08-16: User approved the robust follow-up design: request-bounded indices plus explicit zero-based prompt IDs with unchanged strict local validation.
- 2026-08-16: Verified the 18:18 source archive SHA-256 and read required repository contracts and Plan 071 before editing.
- 2026-08-16: Reproduced baseline focused Plan 071/OpenAI tests successfully before changes.
- 2026-08-16: Implemented request-local bounded schemas, Prompt V3 explicit IDs, OpenAI/Gemini/Mistral structured-schema propagation, and exact Twitter boundary regression coverage without changing input hashing or analytical algorithms.
- 2026-08-16: Focused Plan 073/Plan 071/OpenAI/protected-contract tests passed (76 selected tests). `python -m compileall -q src tests` and `make validate-config PYTHON=python` passed. Direct offline provider probes confirmed request-local `maximum=11` propagation for OpenAI, Gemini, and Mistral on a 12-keyword request while the original Twitter and Telegram input hashes remained unchanged.
- 2026-08-16: `make run-evolution-pipeline-test PYTHON=python` is blocked in the review interpreter because neither `pyarrow` nor `fastparquet` is installed. `make format PYTHON=python` is blocked because `black` is absent. `make lint` attempted its frozen `uv` environment but DNS/network restrictions prevented downloading locked dependencies. No production behavior was weakened to bypass these environment blockers.
