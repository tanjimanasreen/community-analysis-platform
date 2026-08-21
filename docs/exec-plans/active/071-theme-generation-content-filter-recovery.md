# Plan 071 — Research Theme Generation Content-Filter Recovery

## 1. Goal
Make downstream LLM theme generation recoverable when one or many provider safety filters block otherwise valid research payloads, while preserving the thesis analytical evidence and all upstream methodology.

A provider safety failure means **theme interpretation unavailable**. It must never mean missing LDA evidence, a deleted community, altered IF/WIF structure, or a failed longitudinal run by itself.

## 2. Source Snapshot
- Archive: `community-analysis-full-review-20260815-0302.zip`
- SHA-256: `085ba635f720a002947063f4fb625a4552eadf459a245772118f88a4e4ab1c40`
- Branch recorded by snapshot: `feature/frontend-ui-upgrade`
- HEAD recorded by snapshot: `4d05a1adbcf524858972ad5d20e9f0f7444141fc`

## 3. Confirmed Failure Evidence
The read-only isolation probe mapped the failed request hash
`5d11a25c48676b2b85f31a50403ac3c47a25f794eecb9c8fb44a252e4b1d8ee4`
to February 2019 row 9, absolute community 9 / weighted community 7. The same ordered payload is used by both the `absolute` and `general` source assignments. The provider returned a completion-side content-filter outcome.

The exact LDA-derived input is analytical evidence and must remain unchanged.

## 4. Protected Contracts
This plan must not change:
- `shared_post`, `total_post`, or `weighted_post` behavior;
- graph thresholds (`min_total_post=10`, `min_shared_post=5`);
- Louvain defaults (`resolution=1`, `seed=123`);
- approved LDA implementation/defaults;
- LDA keyword columns, ordering, normalization, or input hashing;
- IF/WIF matching semantics;
- transition/Jaccard thresholds or persistent path semantics;
- membership mobility semantics;
- Telegram forwarding semantics or Twitter support;
- HDBSCAN methodology/defaults;
- embedding model/revision/cosine semantics for valid themes;
- provider fallback routing or fallback enablement.

## 5. Approved Methodological Change
All theme requests use one canonical V2 interpretation contract.

The model receives the exact ordered LDA keywords, but the provider-facing output schema becomes:

```json
{
  "themes": [
    {
      "name": "Faithful descriptive research theme",
      "keyword_indices": [0, 3, 7]
    }
  ]
}
```

Application code validates the indices and reconstructs the exact original keyword strings. Existing downstream/public theme mappings remain `{theme_name: [original_keyword, ...]}`.

Theme labels must be **faithful, descriptive, non-endorsing, and severity-preserving**. The prompt must prohibit both euphemistic minimization and unsupported exaggeration.

## 6. Prompt/Schema Versioning
- Define the canonical prompt-contract version centrally in code; do not add a dataset YAML `prompt_version` switch.
- Bump the provider wire output schema version to V2.
- Persist prompt-contract version, prompt hash, output-schema version, input hash, provider, and model in provenance.
- Bump the coarse Prefect theme-stage semantic cache version and include the canonical prompt/output contract versions in its key.
- Existing V1 provider cache entries remain on disk but cannot satisfy V2 requests because prompt/output identity changes.

## 7. Provider Safety Failure Contract
Introduce a small typed provider safety exception for:
- `content_filter`;
- `policy_refusal`.

The failure records a safe category/stage (`prompt`, `completion`, or `unknown`), provider/model, full input/prompt hashes, and sanitized provider diagnostics. It must not contain the raw keyword payload in exception text or operational logs.

OpenAI keeps its existing one dedicated content-filter retry with identical input, prompt, model, and schema. Persistent safety failure becomes the typed terminal payload outcome. Other errors remain fatal.

## 8. Batch Recovery
Theme batching changes only at the safety boundary:
- success -> keep theme result;
- typed safety failure -> record unavailable outcome and continue;
- any other exception -> cancel outstanding work and re-raise as today.

The existing exact ordered-payload de-duplication remains authoritative. One failed unique payload may map to several analytical source assignments.

## 9. Provenance Artifact
Add `theme_generation_provenance.parquet`, one row per non-empty analytical source assignment (`absolute`, `weighted`, `general`). Required fields:
- `year`, `month`, `source_row_index`, `keyword_kind`;
- `absolute_community`, `weighted_community`;
- `provider_keywords`, `keyword_count`, `input_hash`;
- `prompt_hash`, `prompt_contract_version`, `output_schema_version`;
- `status`, `failure_category`, `failure_stage`;
- `configured_provider`, `configured_model`;
- `content_filter_summary`.

The artifact preserves the exact ordered provider input. Operational logs and safe JSON summaries continue to avoid raw keyword payloads.

## 10. Coverage Reporting
Provider lineage reports both:
- unique payload request/generated/unavailable counts;
- analytical source assignment request/generated/unavailable counts;
- content-filter and refusal counts;
- `partial` boolean.

No arbitrary research-readiness threshold is introduced.

## 11. Missing Theme Semantics
For a persistent safety failure:
- LDA/community row remains present;
- `*_theme_names` stays null/absent;
- no placeholder label such as `Unknown`, `Sensitive Content`, or `Filtered` is invented;
- structural transitions remain unchanged.

Theme-similarity computation must never embed an empty/missing theme. Pairs involving a missing interpretation persist with null cosine similarity. Valid-to-valid similarity is numerically unchanged. Heatmaps retain path positions and show gaps for missing observations.

## 12. Artifact/Orchestration Integration
Register the new provenance Parquet in `ThemeOutputBundle`, task output discovery, run-manifest canonical publication, and known Parquet schema validation. New theme executions must produce it. Public/historical output verification treats it as additive so old V1 run bundles are not retroactively invalidated.

Provider-run summary uses the canonical code-defined prompt version, not a dataset config value.

## 13. Tests
Required offline regression coverage:
1. Prompt V2 contains research context, fidelity/severity preservation, no euphemization, no unsupported exaggeration, no keyword-list reproduction, and index-based association.
2. Provider wire schema requires `name + keyword_indices`, not copied keyword strings.
3. Index normalization rejects negative/out-of-range/non-integer/boolean indices and deterministically de-duplicates valid indices.
4. OpenAI completion/prompt content-filter retries once; persistent filtering raises the typed safety failure; refusal is typed; logs remain payload-safe.
5. Multiple simultaneous safety failures do not abort the batch; unrelated exceptions still do.
6. Duplicate source assignments sharing one payload call the provider once but create multiple provenance rows.
7. Representative sensitive keyword fixtures preserve exact strings/order/hash without provider calls.
8. Pipeline writes all month/evolution artifacts with missing interpretations preserved.
9. Similarity does not embed empty strings and writes null similarities for missing pairs.
10. Existing missing-general-theme clustering exclusion behavior remains unchanged.
11. Provider/Prefect V1 caches cannot satisfy V2 execution.
12. Protected IF/WIF/Louvain/LDA/transition tests remain green.

## 14. Explicitly Out of Scope
- keyword filtering/redaction/sanitization;
- content-dependent prompt branching;
- automatic provider switching or new fallback behavior;
- fallback configuration changes;
- new LDA/HDBSCAN/transition methodology;
- frontend changes;
- database changes;
- new cloud/paid dependencies;
- live provider calls in automated tests.

## 15. Validation
Run focused provider/theme tests first, then artifact/orchestration and protected analytical suites. Finally attempt repository gates where the review environment permits:

```bash
python -m compileall -q src tests
make validate-config PYTHON=python
make run-theme-sample PYTHON=python
make run-pipeline-test PYTHON=python
make run-evolution-pipeline-test PYTHON=python
make verify-output-contract PYTHON=python
make verify-evolution-output-contract PYTHON=python
make format PYTHON=python
make lint
make test
```

Environment/dependency blockers are reported separately and must not be worked around by weakening production behavior.

## 16. Progress Log
- 2026-08-15: User explicitly approved Plan 071 and authorized implementation against the 03:02 source snapshot.
- 2026-08-15: Verified source ZIP SHA-256 matches the supplied manifest and created separate pristine/working extracts.
- 2026-08-15: Read mandatory repository contracts and relevant active provider/theme/orchestration plans before editing.
- 2026-08-15: Baseline focused test selection reached the pre-existing review-environment blocker `ModuleNotFoundError: prefect` during orchestration-test collection; no production change was made to bypass it.
- 2026-08-15: Implemented canonical Prompt/Schema V2 (`theme + keyword_indices`) with centralized code-defined prompt/output versions and exact application-side reconstruction of supporting LDA keywords.
- 2026-08-15: Added typed OpenAI `content_filter` / `policy_refusal` outcomes, preserved the existing single content-filter retry, and changed concurrent theme batching to recover only those approved safety outcomes while retaining fail-fast behavior for all other exceptions.
- 2026-08-15: Added per-source `theme_generation_provenance.parquet`, aggregate unique/source coverage reporting, and additive run-manifest/output-contract registration without changing dataset YAML fallback settings.
- 2026-08-15: Updated missing-theme similarity semantics so absent interpretations remain null/NaN and are never embedded as empty strings; structural transition/path and HDBSCAN methodology were not changed.
- 2026-08-15: Added focused offline regression coverage for the V2 schema/prompt, exact failed-payload hash preservation, strict index validation, multiple safety failures, duplicate source assignments, unexpected-error fail-fast behavior, coverage aggregation, provenance schema registration, and missing-theme embedding behavior.
- 2026-08-15: Focused provider/theme/protected-contract unit suite passed, including OpenAI, provider factory/cache, current defaults/config, transitions, membership changes, HDBSCAN clustering, release hygiene, and absolute-path checks. Direct offline normalization checks also passed for OpenAI, LLM7, Mistral, and NVIDIA adapters.
- 2026-08-15: `make validate-config PYTHON=python` passed. `make run-theme-sample PYTHON=python` could not start because the review environment lacks the optional `prefect` dependency. Parquet-heavy tests cannot run because `pyarrow`/`fastparquet` are absent. `make format PYTHON=python` cannot run because `black` is absent. A frozen dependency sync was attempted but the sandbox could not download missing packages, so no production behavior was weakened to bypass environment constraints.
- 2026-08-16: Plan 073 follow-up retains the V2 `name + keyword_indices` output shape but advances the prompt contract to V3, adds explicit zero-based evidence IDs, and bounds each request schema to its exact keyword count after a real Twitter boundary failure exposed the ambiguity.
