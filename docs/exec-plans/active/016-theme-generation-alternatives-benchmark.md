# Plan 016: Theme-Generation Alternatives Benchmark

> **Current production note (2026-08-12):** Plan 016 originally froze GPT-4o as
> the historical benchmark reference. Production theme generation has since
> migrated to the provider registry in `configs/providers.yml`, whose current
> primary is `openai:gpt-5-nano` with strict JSON Schema structured output.
> Legacy `gpt4o_*` benchmark artifact/function names are retained only for
> compatibility with existing benchmark bundles; they do not pin the current
> production provider/model. Tests of current production metadata must follow
> the current provider configuration, while historical benchmark artifacts may
> retain their original names.
>
> **Current artifact note (2026-08-14):** Generated benchmark score summaries
> are Parquet (`scores/summary.parquet` or `scores/<split>_summary.parquet`).
> Current blinded-review artifacts are also Parquet
> (`review/blinded_export.parquet` and `review/review_import_template.parquet`).
> Historical `.csv` score/review references below document earlier benchmark
> runs and are not the current generated-artifact contract.

## 1. Current Provider Assessment

- Current production theme generation is OpenAI-centered through `src/themes/llm_provider.py` and `src/themes/gpt_themes.py`.
- Frozen reference behavior:
  - model: `gpt-4o`
  - temperature: `0`
  - seed: `42`
  - response format: JSON object
  - GPT remains downstream of LDA keywords.
- Current cache is in-memory only, so benchmark work needs a persistent cache/resume layer.
- `MockProvider` already supports offline tests and should remain the test default.
- Ollama/local LLM support exists in code, but Plan 016 will not use or expand it.

## 2. Gemini Candidate-Selection Approach

- Use the official Google GenAI SDK in 016B, not raw HTTP unless the SDK blocks required behavior.
- Add Gemini only after 016A; do not add it to offline foundation.
- Discover available models at runtime using the Gemini Models API / SDK model listing.
- Prefer exact stable model IDs, not `latest` aliases.
- Initial pilot candidates:
  - one economical Flash-Lite-class model
  - one stronger Flash-class model
- Use native structured output with JSON Schema.
- Keep prompt text, keyword order, schema, temperature, batch size, and retry policy identical across providers.
- Record model ID, prompt hash, input hash, latency, usage/tokens when available, estimated cost, retries, timeout/errors, and raw provider metadata.

Source notes: Google documents model listing through `models.list`, structured output with JSON Schema, and stable-vs-latest model naming in the Gemini API docs:
[Models API](https://ai.google.dev/api/models), [Structured output](https://ai.google.dev/gemini-api/docs/structured-output), [Gemini models](https://ai.google.dev/gemini-api/docs/models).

## 3. LLM7 Discovery And Risk-Assessment Approach

- Inspect LLM7 live API/docs before implementation in 016C; do not hardcode guessed model IDs.
- Use `/v1/models` or SDK-compatible model listing to discover accessible models.
- Record:
  - LLM7 gateway model ID
  - claimed upstream model/provider if exposed
  - JSON mode support
  - token metadata availability
  - rate limits
  - pricing fields
  - retention/privacy notes from docs
  - error response format
- Select no more than 2-3 pilot models.
- If OpenAI-compatible behavior is confirmed, implement a reusable OpenAI-compatible gateway adapter; otherwise use a dedicated LLM7 adapter.
- Never assume an LLM7 alias is equivalent to the same directly hosted model.

Source notes: LLM7 documents OpenAI-compatible usage, model discovery, JSON mode capability flags, pricing metadata, and rate limits:
[Quickstart](https://docs.llm7.io/quickstart), [Models guide](https://docs.llm7.io/guides/models), [Models API](https://docs.llm7.io/guides/models-api), [JSON mode](https://docs.llm7.io/guides/json-mode), [Limits](https://docs.llm7.io/limits).

## 4. Benchmark Dataset

- Create a frozen benchmark dataset from saved theme inputs, not from raw network/topic recomputation.
- Default source: existing `_intermediate/theme_inputs/...` artifacts created by `run-topics`.
- Store benchmark examples as JSONL under:
  `<output_base_path>/_experiments/theme_model_benchmark/<run_id>/dataset.jsonl`
- Each example includes:
  - `example_id`
  - data type, content type, year, month
  - community identifiers
  - members count only, not full member list by default
  - absolute, weighted, and general keyword lists
  - original keyword order
  - input hash
- For 016A, include a small frozen fixture dataset for offline tests.
- For 016D, use:
  - 15-20 example compatibility screen
  - one generation per model initially
  - held-out set for finalists only

## 5. Provider-Neutral Contract

Add a benchmark-specific contract without replacing the production `LLMProvider`.

- `ThemeBenchmarkRequest`
  - `example_id`
  - `keyword_mode`: `general | absolute | weighted`
  - ordered keywords
  - prompt text
  - schema version
  - prompt hash
  - input hash
- `ThemeBenchmarkResult`
  - provider ID
  - model ID
  - normalized theme JSON
  - raw response path or raw response object
  - latency
  - usage/tokens when available
  - estimated cost when available
  - retries
  - cache hit
  - error fields
- Normalized output schema:
  - `themes`: list of `{name, keywords}`
  - keyword values must be derived from supplied LDA keywords, not invented as new inputs.
- Providers for 016A:
  - frozen GPT-4o reference importer/config snapshot
  - deterministic keyword baseline
  - mock provider
- Live providers in 016B/016C must be opt-in and require environment keys.

## 6. Experiment Artifacts

All benchmark files go only under:

`<output_base_path>/_experiments/theme_model_benchmark/<run_id>/`

Artifacts:

- `manifest.json`: run settings, schema version, provider list, model IDs, prompt hash, dataset hash, created time.
- `dataset.jsonl`: frozen benchmark inputs.
- `requests.jsonl`: exact provider-neutral requests.
- `generations/<provider_id>.jsonl`: normalized generation results.
- `raw/<provider_id>/...`: raw provider responses, redacted of secrets.
- `cache/<provider_id>.jsonl`: persistent response cache keyed by provider, model, prompt hash, input hash.
- `reference/gpt4o_config.json`: frozen GPT-4o prompt/config reference.
- `reference/gpt4o_outputs.jsonl`: optional imported existing GPT-4o outputs; no OpenAI calls in 016A.
- `review/blinded_export.csv`: randomized/blinded rows for human review.
- `review/review_import.csv`: expected import format for human scores.
- `scores/summary.csv`: automatic and human-evaluation summaries.
- `model_catalogs/gemini_models.json`: added in 016B.
- `model_catalogs/llm7_models.json`: added in 016C.

## 7. Evaluation Metrics

Automatic metrics:

- JSON/schema validity
- empty/error rate
- retry count
- latency
- token usage
- estimated cost
- cache hit rate
- keyword coverage
- duplicate theme rate
- theme count
- deterministic repeat agreement for finalists

Human blinded review metrics:

- fidelity to LDA keywords
- coherence
- specificity
- non-redundancy
- usefulness for thesis interpretation
- overall preference

Downstream metrics:

- theme-similarity stability using existing similarity utilities with injected/mock models in tests
- transition readability across months for longitudinal examples

## 8. Exact Files

016A adds offline benchmark foundation:

- `src/themes/benchmark/contracts.py`
- `src/themes/benchmark/dataset.py`
- `src/themes/benchmark/providers.py`
- `src/themes/benchmark/cache.py`
- `src/themes/benchmark/runner.py`
- `src/themes/benchmark/review.py`
- `src/themes/benchmark/metrics.py`
- `src/themes/benchmark/__init__.py`
- `tests/unit/test_theme_benchmark.py`
- `tests/fixtures/theme_benchmark/`
- CLI additions in `src/cli.py`
- docs: `docs/exec-plans/active/016-theme-generation-alternatives-benchmark.md`

016B adds Gemini:

- `src/themes/benchmark/gemini_provider.py`
- optional config sample for live Gemini benchmark
- `pyproject.toml` adds `google-genai`

016C adds LLM7:

- `src/themes/benchmark/openai_compatible_provider.py`
- `src/themes/benchmark/llm7_provider.py`
- optional config sample for live LLM7 benchmark

016D adds pilot comparison docs/results templates only:

- benchmark runbook section in docs
- review template documentation
- final recommendation template

## 9. Tests

016A offline tests:

- dataset creation from fixture theme inputs
- deterministic keyword baseline output
- mock provider output
- provider-neutral request/result serialization
- persistent cache hit/resume behavior
- experiment manifest creation and validation
- blinded review export hides provider IDs
- review import validates required score columns
- benchmark output path is restricted to `_experiments/theme_model_benchmark`
- no environment keys required
- no live provider calls

016B tests:

- Gemini adapter uses injected fake SDK client
- model discovery filters stable Flash/Flash-Lite candidates
- JSON Schema request construction is correct
- usage/cost/error metadata normalization works

016C tests:

- LLM7 model discovery uses fake HTTP/client responses
- JSON mode support is honored
- gateway model ID and upstream metadata are recorded separately
- rate-limit/error formats normalize cleanly

016D tests:

- finalist selection from compatibility results
- repeated-run aggregation
- blinded human scores join to generation results
- downstream similarity evaluation works with mocked embeddings

## 10. Validation Commands

For 016A:

```bash
.venv/bin/python -m pytest tests/unit/test_theme_benchmark.py
.venv/bin/python -m pytest tests/unit
.venv/bin/python -m src.cli theme-benchmark build-dataset --config configs/sample_twitter_reply.yml --run-id offline-smoke --limit 10
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id offline-smoke --providers keyword_baseline,mock
.venv/bin/python -m src.cli theme-benchmark export-review --config configs/sample_twitter_reply.yml --run-id offline-smoke
```

No 016A command may call Gemini, LLM7, OpenAI, Ollama, SentenceTransformer downloads, Neo4j, Memgraph, or Docker.

For 016B/016C live pilots, add separate explicit commands requiring `--allow-live` and the relevant API key environment variable.

## 11. Cost And Privacy Controls

- API keys only from environment variables:
  - `GEMINI_API_KEY`
  - `LLM7_API_KEY`
- Never write keys to manifests, caches, raw responses, logs, or review exports.
- Defaults:
  - concurrency: `1`
  - batch size: `5`
  - allowed range: `5-10`
  - max retries: `2`
  - exponential backoff
  - request timeout configurable
  - cost/request cap configurable
  - total run cost cap configurable
- Live provider execution requires explicit `--allow-live`.
- `make test`, `make demo`, release validation, API, and dashboard never call live providers.
- Raw benchmark inputs should use LDA keywords and minimal metadata; avoid exporting full member lists by default.

## 12. Acceptance Criteria

- 016A runs fully offline and creates reproducible benchmark artifacts.
- Existing GPT-4o prompt/config is frozen as the reference without changing production defaults.
- Deterministic keyword baseline and mock provider work without network access.
- Persistent cache/resume prevents repeated generation for identical provider/model/prompt/input hashes.
- Gemini and LLM7 plans require explicit live opt-in and environment keys.
- No production thesis output, API contract, dashboard behavior, or network/community/LDA stage changes.
- All outputs stay under `_experiments/theme_model_benchmark/<run_id>/`.
- No local LLM/Ollama benchmark work is added in this initial plan.

## 13. Implementation Prompt For Plan 016A Only

```text
Implement Plan 016A only: offline theme-generation benchmark foundation. Add a benchmark-specific provider-neutral request/result contract, frozen dataset builder from saved theme-input artifacts, deterministic keyword baseline provider, mock provider, persistent JSONL response cache/resume, experiment manifest, blinded review export/import, and offline unit tests. Store outputs only under <output_base_path>/_experiments/theme_model_benchmark/<run_id>/. Freeze the existing GPT-4o prompt/config as reference metadata and support importing prior GPT-4o outputs if present, but do not call OpenAI. Do not add Gemini or LLM7 live integrations yet. Do not change production default provider, public thesis outputs, API contracts, dashboard behavior, or network/community/LDA stages. Ensure make test remains offline and no provider keys are required.
```

## 14. Plan 016A Progress Log

Status: 016A offline benchmark foundation is implemented. 016B Gemini,
016C LLM7, and 016D pilot comparison are not started.

Completed milestones:

- Added a benchmark-only package under `src/themes/benchmark/`.
- Added provider-neutral request/result contracts, schema versions, canonical
  JSON hashing, and JSONL helpers.
- Built frozen datasets from saved theme-input artifacts only.
- Preserved the four original LDA keyword fields in every dataset row:
  `absolute_unigram_keywords`, `absolute_bigram_keywords`,
  `weighted_unigram_keywords`, and `weighted_bigram_keywords`.
- Added production-equivalent keyword preparation for general, absolute, and
  weighted requests using the current de-duplicate/preserve-order formatting.
- Froze GPT-4o reference metadata with exact prompt template, prompt hash,
  model ID, temperature, seed, response format, and output schema version.
- Added deterministic offline `keyword_baseline` and `mock` providers.
- Added persistent JSONL cache/resume behavior keyed by provider ID, model ID,
  prompt hash, input hash, schema versions, keyword mode, and generation
  parameters.
- Added benchmark manifest, request, generation, raw response, cache, review,
  reference, and score-summary artifacts under
  `<output_base_path>/_experiments/theme_model_benchmark/<run_id>/`.
- Added blinded review export and review import validation.
- Added initial offline automatic score summaries.
- Added focused offline unit tests and fixture data.

Files changed:

- `src/themes/benchmark/__init__.py`
- `src/themes/benchmark/contracts.py`
- `src/themes/benchmark/dataset.py`
- `src/themes/benchmark/providers.py`
- `src/themes/benchmark/cache.py`
- `src/themes/benchmark/runner.py`
- `src/themes/benchmark/review.py`
- `src/themes/benchmark/metrics.py`
- `src/cli.py`
- `tests/unit/test_theme_benchmark.py`
- `tests/fixtures/theme_benchmark/matched_lda.csv`
- `docs/exec-plans/active/016-theme-generation-alternatives-benchmark.md`

Design decisions:

- Benchmark code is additive and does not modify `run-theme-analysis`, public
  output contracts, the API, dashboard, production provider defaults, or
  network/community/LDA stages.
- Missing saved theme-input artifacts fail clearly and instruct the user to run
  existing topic/pipeline commands first; benchmark commands never recompute
  upstream stages.
- `--limit` is treated as a maximum. If fewer valid examples are available,
  all available examples are written and the manifest/CLI report the actual
  count.
- Full member lists are not written to benchmark rows; only `members_count` is
  exported.
- Benchmark run IDs are restricted to simple names so files cannot escape
  `_experiments/theme_model_benchmark/<run_id>/`.
- Prior GPT-4o outputs can be copied from a local JSONL file during dataset
  construction, but 016A never calls OpenAI.

CLI commands added:

```bash
.venv/bin/python -m src.cli theme-benchmark build-dataset --config configs/sample_twitter_reply.yml --run-id offline-smoke --limit 10
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id offline-smoke --providers keyword_baseline,mock
.venv/bin/python -m src.cli theme-benchmark export-review --config configs/sample_twitter_reply.yml --run-id offline-smoke
```

Validation results:

- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark.py`
  - Passed: 9 tests.
- `.venv/bin/python -m pytest tests/unit`
  - Passed: 127 tests.
  - Warnings only: existing FastAPI TestClient warning and tiny-fixture
    Gensim/SciPy/Kneed/NumPy warnings.
- `.venv/bin/python -m src.cli theme-benchmark build-dataset --config configs/sample_twitter_reply.yml --run-id offline-smoke --limit 10`
  - Passed.
  - Wrote 1 available valid example for requested limit 10.
  - Dataset hash:
    `9b483daad08abb900d38685ba6526ecd8738342e5c60307295645f7d9a794fc8`.
- `.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id offline-smoke --providers keyword_baseline,mock`
  - Passed.
  - Generated or resumed 6 benchmark results.
- `.venv/bin/python -m src.cli theme-benchmark export-review --config configs/sample_twitter_reply.yml --run-id offline-smoke`
  - Passed.
- `LLM_PROVIDER=mock make demo`
  - Passed.
  - Note: plain `make run-pipeline-sample` attempted the existing Ollama
    provider from local dotenv configuration and failed on sandboxed localhost
    access before the explicit `LLM_PROVIDER=mock` override was used. This was
    pre-existing production-provider selection behavior, not benchmark code.

Generated benchmark artifact path:

```text
/tmp/community-analysis-sample/_experiments/theme_model_benchmark/offline-smoke/
```

Observed artifact files:

- `manifest.json`
- `dataset.jsonl`
- `requests.jsonl`
- `generations/keyword_baseline.jsonl`
- `generations/mock.jsonl`
- `raw/keyword_baseline/*.json`
- `raw/mock/*.json`
- `cache/keyword_baseline.jsonl`
- `cache/mock.jsonl`
- `reference/gpt4o_config.json`
- `review/blinded_export.csv`
- `review/review_import_template.csv`
- `scores/summary.csv`

Known limitations:

- 016A providers are intentionally offline only; Gemini and LLM7 are not
  implemented.
- Automatic metrics are initial screening metrics only and do not replace
  blinded human review.
- Reusing a run ID is intended for identical/resumed benchmark runs. Use a new
  run ID for a materially different dataset or provider set to avoid mixing
  old generation artifacts with new experiment intent.
- The benchmark review import validator checks required score columns but does
  not yet join human scores back into aggregate model rankings; that belongs in
  later pilot-comparison work.

Next entry point for Plan 016B:

- Add Gemini as an opt-in live provider in `src/themes/benchmark/`, requiring
  explicit `--allow-live` and `GEMINI_API_KEY`.
- Use an injected fake SDK client in tests.
- Add model discovery/catalog artifacts under
  `_experiments/theme_model_benchmark/<run_id>/model_catalogs/`.
- Keep the production provider unchanged and keep all normal tests, demo
  commands, API startup, and dashboard startup offline.

## 15. Plan 016A Focused Closeout And 016B Gemini Progress

Status:

- Plan 016A closeout gate passed.
- Plan 016B Gemini benchmark integration is implemented with offline fake-client
  validation.
- Live Gemini discovery/generation is blocked in this environment because
  `GEMINI_API_KEY` is absent and the optional `google-genai` SDK is not
  installed.
- Plan 016C LLM7 and Plan 016D pilot comparison are not started.

### Plan 016A Closeout

Provider-isolation decision:

- `Makefile` keeps `OFFLINE_LLM_PROVIDER := mock` as a local Make variable.
- `run-theme-sample` prefixes only its theme command with
  `LLM_PROVIDER=$(OFFLINE_LLM_PROVIDER)`.
- `run-longitudinal-sample` prefixes only its `run-theme-analysis` invocation
  with `LLM_PROVIDER=$(OFFLINE_LLM_PROVIDER)`.
- `run-pipeline-sample` and `demo` inherit deterministic mock-backed theme
  execution through their dependencies.
- Normal direct CLI provider selection still respects `LLM_PROVIDER` and dotenv.
- No `.env` file was modified or printed.

Cache statistics implementation:

- Benchmark runner now returns structured aggregate and per-provider counts:
  request count, result count, cache hits, cache misses, provider executions,
  and failures.
- CLI now prints exact counts instead of only "Generated or resumed".
- Cache hits are counted only when a matching persistent
  `cache/<provider_id>.jsonl` entry is reused.
- Existing generation files are no longer treated as proof of cache hits.
- Failed provider results are written to generation output but are not inserted
  into the successful persistent cache.

Stage 1 validation results:

- `make run-theme-sample`
  - Passed.
  - Command showed `LLM_PROVIDER=mock`.
- `make run-pipeline-sample`
  - Passed.
  - Command showed `LLM_PROVIDER=mock` for theme generation.
  - Known warning: tiny LDA sample emitted a Kneed runtime warning.
- `make run-longitudinal-sample`
  - Passed.
  - Command showed `LLM_PROVIDER=mock` for longitudinal theme generation.
- `make demo`
  - Passed.
  - API smoke tests passed: 12 tests.
  - Known warning: FastAPI/Starlette TestClient deprecation warning.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark.py`
  - Passed: 11 tests.
- `.venv/bin/python -m pytest tests/unit`
  - Passed: 130 tests during Stage 1 gate, then 144 tests after Gemini tests
    were added.
  - Known warnings: existing FastAPI TestClient warning and tiny-fixture
    Gensim/SciPy/Kneed/NumPy warnings.

Reproducibility confirmation:

```bash
.venv/bin/python -m src.cli theme-benchmark build-dataset --config configs/sample_twitter_reply.yml --run-id reproducibility-a --limit 10
.venv/bin/python -m src.cli theme-benchmark build-dataset --config configs/sample_twitter_reply.yml --run-id reproducibility-b --limit 10
```

Both runs wrote 1 available valid example for requested limit 10.

Both dataset hashes matched:

```text
9b483daad08abb900d38685ba6526ecd8738342e5c60307295645f7d9a794fc8
```

Offline smoke cache confirmation:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id offline-smoke --providers keyword_baseline,mock
```

Second identical run reported:

```text
Requests: 6
Results: 6
Cache hits: 6
Cache misses: 0
Provider executions: 0
Failures: 0
Provider keyword_baseline: requests=3, results=3, cache_hits=3, cache_misses=0, provider_executions=0, failures=0
Provider mock: requests=3, results=3, cache_hits=3, cache_misses=0, provider_executions=0, failures=0
```

Generated Stage 1 artifact paths:

```text
/tmp/community-analysis-sample/_experiments/theme_model_benchmark/offline-smoke/
/tmp/community-analysis-sample/_experiments/theme_model_benchmark/reproducibility-a/
/tmp/community-analysis-sample/_experiments/theme_model_benchmark/reproducibility-b/
```

Known Stage 1 limitation:

- The configured sample benchmark has only one valid example, so it is useful
  for smoke/cache/schema validation but not for a meaningful model comparison.

Stage 1 acceptance:

- Passed. Plan 016B implementation began only after plain sample/demo targets,
  unit tests, reproducibility, cache reuse, and provider-execution-zero checks
  passed.

### Plan 016B Gemini Implementation

Files added:

- `src/themes/benchmark/gemini_provider.py`
- `tests/unit/test_theme_benchmark_gemini.py`

Files modified:

- `Makefile`
- `pyproject.toml`
- `src/cli.py`
- `src/themes/benchmark/contracts.py`
- `src/themes/benchmark/dataset.py`
- `src/themes/benchmark/providers.py`
- `src/themes/benchmark/runner.py`
- `tests/unit/test_release_hygiene.py`
- `tests/unit/test_theme_benchmark.py`
- `docs/exec-plans/active/016-theme-generation-alternatives-benchmark.md`

Dependency strategy:

- Added optional extra:

```text
benchmark-gemini = ["google-genai>=2.3.0,<3.0.0"]
```

- `requirements.txt` remains the small compatibility wrapper: `-e .[dev]`.
- Gemini SDK imports are lazy and isolated to the benchmark Gemini provider.
- If the SDK is missing, live Gemini commands show:

```bash
.venv/bin/python -m pip install -e '.[benchmark-gemini]'
```

Gemini provider design:

- Gemini exists only as a benchmark provider.
- CLI provider spec is `gemini:<exact_model_id>`.
- Provider artifact ID is filesystem-safe, for example:
  `gemini__gemini-3.5-flash`.
- Exact model ID is stored separately in metadata.
- `--allow-live` is required before client creation.
- `GEMINI_API_KEY` is required for live execution and is never printed or
  persisted.
- Every Gemini call is stateless with `store=False`.
- Gemini call construction preserves prompt roles:
  - frozen production system prompt -> `system_instruction`
  - rendered production user prompt -> `input`
- Gemini uses structured output with:

```python
response_format={
    "type": "text",
    "mime_type": "application/json",
    "schema": THEME_OUTPUT_JSON_SCHEMA,
}
```

- Temperature is fixed at `0.0`.
- Prompt/request hashing now includes system prompt, user template, rendered
  input, keyword order, output schema, and generation settings.

Model discovery design:

- Added:

```bash
.venv/bin/python -m src.cli theme-benchmark discover-models --provider gemini --config CONFIG --run-id RUN_ID --allow-live
```

- Discovery uses `client.models.list()` and writes:

```text
<output_base_path>/_experiments/theme_model_benchmark/<run_id>/model_catalogs/gemini_models.json
```

- Catalog records:
  - SDK version
  - Models API accessibility
  - exact model IDs
  - display names
  - token limits when available
  - generateContent capability
  - Interactions support status: documented or unknown
  - latest/preview/experimental classification
  - Flash-Lite/Flash candidate classification
  - selection/rejection reasons
  - no secrets
- Discovery does not treat Models API `generateContent` support as proof of
  Interactions API support. Shortlisting requires documented Interactions
  support or a future compatibility probe.

Request, retry, cap, and cost controls:

- Live run options:
  - `--allow-live`
  - `--max-examples`
  - `--keyword-modes`
  - `--max-concurrency` (Plan 016B supports only `1`)
  - `--max-retries` (default `2`)
  - `--timeout`
  - `--max-outbound-requests` (default `50`)
- Retryable: rate limit, timeout, transient server, and network errors.
- Non-retryable: missing key, auth, permission, invalid model, schema
  configuration, and request-cap exhaustion.
- Total outbound request budget is shared across Gemini providers in one run.
- Cost estimation remains `null`; token usage is recorded when returned.
- Raw responses are reduced/redacted and written only under
  `raw/<provider_id>/`.

Gemini fake-client validation:

- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark.py tests/unit/test_theme_benchmark_gemini.py tests/unit/test_release_hygiene.py`
  - Passed: 30 tests.
- `.venv/bin/python -m pytest tests/unit`
  - Passed: 144 tests.

Offline release validation after Gemini implementation:

- `make demo`
  - Passed.
  - API smoke tests passed: 12 tests.
- `make api-smoke-test`
  - Passed: 12 tests.
- `make frontend-lint`
  - Passed.
- `make frontend-build`
  - Passed.

Live Gemini validation:

- Environment check:
  - `GEMINI_API_KEY`: absent.
  - `google-genai` SDK: absent.
- Live commands were not run against Google.
- Guard checks:

```bash
.venv/bin/python -m src.cli theme-benchmark discover-models --provider gemini --config configs/sample_twitter_reply.yml --run-id gemini-smoke
```

failed before client creation with:

```text
Theme benchmark failed: Gemini model discovery requires --allow-live.
```

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id offline-smoke --providers gemini:gemini-3.5-flash --keyword-modes general
```

failed before client creation with:

```text
Theme benchmark failed: Gemini benchmark provider requires --allow-live.
```

```bash
.venv/bin/python -m src.cli theme-benchmark discover-models --provider gemini --config configs/sample_twitter_reply.yml --run-id gemini-smoke --allow-live
```

failed before network access with:

```text
Theme benchmark failed: GEMINI_API_KEY must be set for live Gemini benchmark commands.
```

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id offline-smoke --providers gemini:gemini-3.5-flash --allow-live --keyword-modes general --max-examples 1 --max-outbound-requests 1
```

failed before network access with:

```text
Theme benchmark failed: GEMINI_API_KEY must be set for live Gemini benchmark commands.
```

Safe live entry point for a future environment:

```bash
.venv/bin/python -m pip install -e '.[benchmark-gemini]'
.venv/bin/python -m src.cli theme-benchmark discover-models --provider gemini --config configs/sample_twitter_reply.yml --run-id gemini-smoke --allow-live
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id gemini-smoke --providers gemini:<EXACT_MODEL_ID> --allow-live --keyword-modes general --max-examples 1 --max-concurrency 1 --max-retries 2 --max-outbound-requests 50
```

Plan 016B limitation:

- No live model IDs were discovered or selected in this environment because
  live Gemini prerequisites are unavailable.
- The sample dataset still contains one valid example, so any live run from the
  sample config should be labeled an integration smoke, not a compatibility
  screen.

Exact next entry point for Plan 016C:

- Start LLM7 implementation only after a future Gemini live smoke or explicitly
  documented Gemini-live blocker review.
- Do not modify production provider defaults.
- Reuse the benchmark cache/statistics/request-cap pattern from 016B.

## 16. Plan 016B Live Closeout Review And 016C LLM7 Progress

Status:

- Plan 016B remains code-complete and offline-validated.
- Plan 016B live Gemini validation is still externally blocked in this
  environment.
- Plan 016C LLM7 benchmark integration is implemented and offline-validated.
- Plan 016D pilot comparison, human evaluation, champion selection, MLflow, and
  production-provider replacement are not started.

Dirty worktree preservation:

- Existing uncommitted Plan 016 work was preserved.
- Unrelated `.DS_Store` changes were not edited intentionally.
- No commits or tags were created.

Gemini live closeout review:

- Current process environment check:
  - `GEMINI_API_KEY`: absent.
  - `google-genai` SDK: absent.
- A repository `.env` file exists, but benchmark live providers read process
  environment directly and do not call `load_dotenv()`. Secret values were not
  printed or persisted.
- Live Gemini discovery/generation was not run against Google.
- Remaining unverified Gemini live items:
  - accessible live model catalog
  - exact selected Gemini model IDs
  - real structured-output response
  - live usage/latency metadata
  - live cache replay with zero outbound calls

Gemini guard results:

```bash
.venv/bin/python -m src.cli theme-benchmark discover-models --provider gemini --config configs/sample_twitter_reply.yml --run-id gemini-guard
```

failed before client creation with:

```text
Theme benchmark failed: Gemini model discovery requires --allow-live.
```

```bash
.venv/bin/python -m src.cli theme-benchmark discover-models --provider gemini --config configs/sample_twitter_reply.yml --run-id gemini-guard --allow-live
```

failed before network access with:

```text
Theme benchmark failed: GEMINI_API_KEY must be set for live Gemini benchmark commands.
```

```bash
GEMINI_API_KEY=dummy-not-persisted .venv/bin/python -m src.cli theme-benchmark discover-models --provider gemini --config configs/sample_twitter_reply.yml --run-id gemini-guard --allow-live
```

failed before network access with:

```text
Theme benchmark failed: Gemini benchmark support requires the optional dependency. Install it with: .venv/bin/python -m pip install -e '.[benchmark-gemini]'
```

Safe pending Gemini live commands:

```bash
.venv/bin/python -m pip install -e '.[benchmark-gemini]'
.venv/bin/python -m src.cli theme-benchmark discover-models --provider gemini --config configs/sample_twitter_reply.yml --run-id gemini-smoke --allow-live
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id gemini-smoke --providers gemini:<EXACT_MODEL_ID> --allow-live --keyword-modes general --max-examples 1 --max-concurrency 1 --max-retries 2 --max-outbound-requests 50
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id gemini-smoke --providers gemini:<EXACT_MODEL_ID> --allow-live --keyword-modes general --max-examples 1 --max-concurrency 1 --max-retries 2 --max-outbound-requests 50
```

The second identical run should report `Provider executions: 0`.

Plan 016C LLM7 files changed:

- `src/themes/benchmark/live.py`
- `src/themes/benchmark/llm7_provider.py`
- `src/themes/benchmark/gemini_provider.py`
- `src/themes/benchmark/providers.py`
- `src/themes/benchmark/runner.py`
- `src/cli.py`
- `tests/unit/test_theme_benchmark_llm7.py`
- `docs/exec-plans/active/016-theme-generation-alternatives-benchmark.md`

LLM7 design decisions:

- LLM7 is benchmark-only and does not modify production `LLMProvider`,
  `run-theme-analysis`, public outputs, API contracts, dashboard behavior, or
  network/community/LDA stages.
- LLM7 uses the existing OpenAI SDK dependency with
  `base_url="https://api.llm7.io/v1"`, matching the current LLM7 quickstart.
- CLI provider spec is `llm7:<exact_model_id>`.
- Benchmark runs reject LLM7 selectors `default`, `fast`, and `pro`; exact
  model IDs must come from discovery or explicit user selection.
- `LLM7_API_KEY` is required for live LLM7 commands and is read only from the
  process environment.
- LLM7 benchmark requests preserve prompt roles:
  - production system prompt -> chat `system` message
  - rendered production user prompt -> chat `user` message
- LLM7 generation uses `temperature=0.0`, non-streaming chat completions, and
  `response_format={"type": "json_object"}`.
- Live providers now default to `general` keyword mode unless
  `--keyword-modes` is supplied; offline providers still default to all modes.
- A shared live request-budget helper is used by Gemini and LLM7 while keeping
  provider-specific error text.
- LLM7 cache keys include provider ID, exact model ID, prompt hash, input hash,
  schema versions, keyword mode, OpenAI SDK version, base URL, response format,
  timeout, retry/cap settings, temperature, and optional catalog-record hash.
- Failed LLM7 results are written as generation failures but are not inserted
  as successful cache records.
- LLM7 estimated cost is populated only when usage and pricing metadata are
  available; otherwise it remains `null`.
- LLM7 raw metadata is reduced/redacted before persistence.

LLM7 CLI additions:

```bash
.venv/bin/python -m src.cli theme-benchmark discover-models --provider llm7 --config CONFIG --run-id RUN_ID --allow-live
.venv/bin/python -m src.cli theme-benchmark run --config CONFIG --run-id RUN_ID --providers llm7:<EXACT_MODEL_ID> --allow-live --keyword-modes general --max-examples 1 --max-concurrency 1 --max-retries 2 --max-outbound-requests 50
```

LLM7 model discovery behavior:

- Writes:

```text
<output_base_path>/_experiments/theme_model_benchmark/<run_id>/model_catalogs/llm7_models.json
```

- Catalog records exact IDs, tiers, pricing, modalities, context windows,
  JSON-mode support, streaming/reasoning/tools flags, rate-limit notes,
  selection/rejection reasons, OpenAI SDK version, base URL, and
  `contains_secrets: false`.
- Shortlisting allows at most one `turbo` text+JSON model and one `pro`
  text+JSON model.
- Ambiguous shortlists are written to the catalog and fail clearly rather than
  silently selecting a model.

LLM7 live status:

- Current process environment check:
  - `LLM7_API_KEY`: absent.
  - OpenAI SDK: installed, version `2.44.0`.
- Live LLM7 discovery/generation was not run against LLM7.
- Remaining unverified LLM7 live items:
  - accessible live model catalog
  - exact selected LLM7 model IDs
  - real JSON-mode response
  - live usage/latency metadata
  - live estimated-cost metadata from catalog pricing
  - live cache replay with zero outbound calls

LLM7 guard results:

```bash
.venv/bin/python -m src.cli theme-benchmark discover-models --provider llm7 --config configs/sample_twitter_reply.yml --run-id llm7-guard
```

failed before client creation with:

```text
Theme benchmark failed: LLM7 model discovery requires --allow-live.
```

```bash
.venv/bin/python -m src.cli theme-benchmark discover-models --provider llm7 --config configs/sample_twitter_reply.yml --run-id llm7-guard --allow-live
```

failed before network access with:

```text
Theme benchmark failed: LLM7_API_KEY must be set for live LLM7 benchmark commands.
```

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id offline-smoke --providers llm7:llm7-turbo-json --keyword-modes general
```

failed before client creation with:

```text
Theme benchmark failed: LLM7 benchmark provider requires --allow-live.
```

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id offline-smoke --providers llm7:default --allow-live --keyword-modes general
```

failed before network access with:

```text
Theme benchmark failed: LLM7 benchmark provider requires an exact model ID from model discovery, not default, fast, or pro.
```

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id offline-smoke --providers llm7:llm7-turbo-json --allow-live --keyword-modes general --max-examples 1 --max-outbound-requests 1
```

failed before network access with:

```text
Theme benchmark failed: LLM7_API_KEY must be set for live LLM7 benchmark commands.
```

Validation results:

- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark.py tests/unit/test_theme_benchmark_gemini.py tests/unit/test_theme_benchmark_llm7.py tests/unit/test_release_hygiene.py`
  - Passed: 48 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_llm7.py`
  - Passed: 18 tests.
- `.venv/bin/python -m pytest tests/unit`
  - Passed: 162 tests.
  - Known warnings: existing FastAPI TestClient warning and tiny-fixture
    Gensim/SciPy/Kneed/NumPy warnings.
- `.venv/bin/python -m src.cli theme-benchmark build-dataset --config configs/sample_twitter_reply.yml --run-id llm7-offline-smoke --limit 10`
  - Passed.
  - Wrote 1 available valid example for requested limit 10.
  - Dataset hash:
    `9b483daad08abb900d38685ba6526ecd8738342e5c60307295645f7d9a794fc8`.
- `make demo`
  - Passed.
  - API smoke tests inside demo passed: 12 tests.
- `make api-smoke-test`
  - Passed: 12 tests.
- `make frontend-lint`
  - Passed.
- `make frontend-build`
  - Passed.

Generated/checked artifact path:

```text
/tmp/community-analysis-sample/_experiments/theme_model_benchmark/llm7-offline-smoke/
```

Known limitations:

- Gemini and LLM7 live validation are both blocked by missing API keys in the
  current process environment.
- Gemini also lacks the optional `google-genai` SDK in this environment.
- The sample benchmark has one valid example, useful for integration smoke,
  cache, schema, and failure handling only; it is not a meaningful model
  comparison set.
- LLM7 discovery records pricing metadata and can estimate cost when usage is
  returned, but no live LLM7 pricing/usage was observed locally.

Exact next entry point for Plan 016D:

- After the user supplies live Gemini and LLM7 prerequisites and runs the
  pending live smoke/cache commands, start Plan 016D by using discovered exact
  model IDs and the frozen benchmark artifacts to design a small pilot
  comparison.
- Do not replace the production provider, alter public thesis outputs, or add
  MLflow/champion-selection behavior until a later explicitly approved plan.

## 17. Dotenv Bootstrap Correction For Benchmark Live Providers

> **Superseded configuration note (2026-08-12):** The implementation record below
> describes the earlier CLI-specific dotenv bootstrap. The current provider layer
> now reads `.env` and exported environment values through centralized
> `ProviderSettings` in `src/config/settings.py`; benchmark providers consume those
> settings directly. Exported environment values retain precedence, and settings
> loading does not require mutating `os.environ`. The historical record below is
> preserved for traceability.

Status:

- Benchmark CLI dotenv loading is fixed.
- Project-root `.env` keys are now available to `python -m src.cli
  theme-benchmark ...` commands launched from the repository root.
- Existing exported process environment values still take precedence over
  `.env` values.
- No provider keys were added to YAML configs, CLI arguments, manifests, caches,
  raw responses, tests, or logs.

Root cause:

- Production theme analysis already calls `load_dotenv()` in
  `src/pipelines/theme_pipeline.py`.
- Benchmark providers correctly read only `os.environ`, but the benchmark CLI
  path did not load the project-root `.env` before Gemini/LLM7 key guards.
- As a result, previous benchmark guard checks saw missing keys even though the
  ignored project-root `.env` contained `GEMINI_API_KEY` and `LLM7_API_KEY`.

Implementation:

- Added a benchmark CLI bootstrap in `src/cli.py` that calls the existing
  `python-dotenv` loader before benchmark config validation and provider
  construction.
- The loader resolves `.env` from the current working directory with
  `find_dotenv(usecwd=True)` and calls `load_dotenv(..., override=False)`.
- Provider modules still read only `os.environ`.
- Missing-key errors remain unchanged and safe.
- Gemini and LLM7 model-discovery network/provider exceptions now normalize to
  `Theme benchmark failed: ...` instead of leaking SDK tracebacks.

Tests added/updated:

- `tests/unit/test_release_hygiene.py` now verifies benchmark dotenv loading
  from a temporary `.env` and verifies that exported values are not overwritten.
- `tests/unit/test_theme_benchmark_gemini.py` no longer depends on whether
  `google-genai` is installed on the developer machine; the missing-SDK case is
  simulated explicitly.

Safe dotenv validation:

```bash
test -f .env
grep -E '^(GEMINI_API_KEY|LLM7_API_KEY)=' .env | sed 's/=.*/=<redacted>/'
.venv/bin/python -c "from dotenv import load_dotenv
import os
load_dotenv(override=False)
print('GEMINI_API_KEY available' if os.getenv('GEMINI_API_KEY') else 'GEMINI_API_KEY missing')
print('LLM7_API_KEY available' if os.getenv('LLM7_API_KEY') else 'LLM7_API_KEY missing')"
```

Observed safe output:

```text
GEMINI_API_KEY=<redacted>
LLM7_API_KEY=<redacted>
GEMINI_API_KEY available
LLM7_API_KEY available
```

Live discovery checks:

- Gemini discovery succeeded with the project-root `.env` key after network
  access was approved:

```text
/tmp/community-analysis-sample/_experiments/theme_model_benchmark/dotenv-gemini-guard/model_catalogs/gemini_models.json
```

- Gemini catalog summary:
  - `contains_secrets`: `False`
  - model count: 54
  - selected candidates: 2
  - ambiguous candidates: 0
  - no obvious key/bearer secret markers detected

- LLM7 discovery loaded the project-root `.env` key and reached provider model
  discovery. It wrote the catalog and failed safely because candidate selection
  is intentionally ambiguous:

```text
/tmp/community-analysis-sample/_experiments/theme_model_benchmark/dotenv-llm7-guard/model_catalogs/llm7_models.json
```

- LLM7 catalog summary:
  - `contains_secrets`: `False`
  - model count: 12
  - selected candidates: 0
  - ambiguous candidates: 2
  - no obvious key/bearer secret markers detected

Validation results:

- `.venv/bin/python -m pytest tests/unit/test_release_hygiene.py`
  - Passed: 6 tests.
- `.venv/bin/python -m pytest tests/unit/test_release_hygiene.py tests/unit/test_theme_benchmark_gemini.py tests/unit/test_theme_benchmark_llm7.py`
  - Passed: 38 tests.
- `.venv/bin/python -m pytest tests/unit`
  - Passed: 163 tests.
  - Known warnings only: existing FastAPI TestClient warning and tiny-fixture
    Gensim/SciPy/Kneed/NumPy warnings.
- `make demo`
  - Passed.
  - Demo theme stages still use `LLM_PROVIDER=mock`.

Known limitations:

- Gemini live generation/cache replay was not run in this correction step.
- LLM7 live generation/cache replay was not run because discovery returned
  ambiguous `turbo` and `pro` candidate classes; an exact model ID must be
  selected from the catalog before generation.

## 18. Live Smoke Validation And Dataset-Readiness Assessment

Status:

- Gemini one-example live smoke is complete.
- Gemini cache replay is complete and proved zero outbound requests.
- LLM7 live generation remains blocked by provider catalog ambiguity and now
  requires an explicit approved selection artifact before generation.
- Dataset readiness is integration-smoke only; fewer than 15 valid saved
  theme-input examples are currently available.
- Plan 016D is not started.

Preflight state:

- Branch: `experiment/theme-model-benchmark`.
- `GEMINI_API_KEY`: available via dotenv without printing value.
- `LLM7_API_KEY`: available via dotenv without printing value.
- Installed clients:
  - `google-genai=2.10.0`
  - `openai=2.44.0`
  - `python-dotenv=1.2.2`
- Existing unrelated `.DS_Store` dirty files were preserved.
- `.env` was not edited.

### Gemini Catalog Review

Catalog:

```text
/tmp/community-analysis-sample/_experiments/theme_model_benchmark/dotenv-gemini-guard/model_catalogs/gemini_models.json
```

Catalog summary:

- Models API accessible: `true`.
- `contains_secrets`: `false`.
- Model count: 54.
- Selected candidates: 2.
- Ambiguous candidates: 0.

Candidate table:

| Exact model ID | Display name | Classification | Models API | Text generation | Interactions support | Candidate class | Decision |
|---|---|---:|---:|---:|---|---|---|
| `gemini-3.1-flash-lite` | Gemini 3.1 Flash Lite | stable | accessible | yes | documented | economical | selected: stable documented Interactions-capable Flash-Lite candidate |
| `gemini-3.5-flash` | Gemini 3.5 Flash | stable | accessible | yes | documented | stronger | selected: stable documented Interactions-capable Flash candidate |
| `gemini-2.5-flash-lite` | Gemini 2.5 Flash-Lite | stable | accessible | yes | unknown | rejected | rejected: Interactions support unknown |
| `gemini-2.5-flash` | Gemini 2.5 Flash | stable | accessible | yes | unknown | rejected | rejected: Interactions support unknown |
| `gemini-flash-latest` | Gemini Flash Latest | latest alias | accessible | yes | unknown | rejected | rejected: moving latest alias and unknown Interactions support |
| `gemini-3-flash-preview` | Gemini 3 Flash Preview | preview | accessible | yes | unknown | rejected | rejected: preview model and unknown Interactions support |

Selected exact Gemini models:

- `gemini-3.1-flash-lite`
- `gemini-3.5-flash`

### Gemini Live Smoke

Dataset command:

```bash
.venv/bin/python -m src.cli theme-benchmark build-dataset --config configs/sample_twitter_reply.yml --run-id gemini-live-smoke --limit 1
```

Result:

- Examples: 1.
- Dataset hash:
  `9b483daad08abb900d38685ba6526ecd8738342e5c60307295645f7d9a794fc8`.

Smoke command:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id gemini-live-smoke --providers gemini:gemini-3.1-flash-lite,gemini:gemini-3.5-flash --allow-live --keyword-modes general --max-examples 1 --max-concurrency 1 --max-retries 2 --max-outbound-requests 6
```

Safe preflight printed:

```text
Selected model IDs: gemini-3.1-flash-lite, gemini-3.5-flash
Example count: 1
Keyword modes: general
Normal request count: 2
Max outbound requests: 6
Max retries: 2
Timeout: None
Concurrency: 1
Gemini store=False
```

Implementation note:

- The installed Google GenAI SDK accepts Gemini Interactions generation
  settings through `generation_config`.
- Gemini live calls preserve:
  - system/user prompt separation
  - `store=False`
  - `generation_config={"temperature": 0.0}`
  - structured JSON response format

Initial sandboxed attempts:

- First failed with SDK argument compatibility:
  `create() got unexpected keyword argument(s): temperature`.
- Fixed by using Interactions `generation_config`.
- Subsequent sandboxed run failed with DNS:
  `[Errno 8] nodename nor servname provided, or not known`.
- Escalated live smoke then succeeded.

First successful live smoke result:

```text
Requests: 2
Results: 2
Cache hits: 0
Cache misses: 2
Provider executions: 2
Outbound requests: 2
Failures: 0
Provider gemini__gemini-3.1-flash-lite: requests=1, results=1, cache_hits=0, cache_misses=1, provider_executions=1, outbound_requests=1, failures=0
Provider gemini__gemini-3.5-flash: requests=1, results=1, cache_hits=0, cache_misses=1, provider_executions=1, outbound_requests=1, failures=0
```

Exact cache replay command:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/sample_twitter_reply.yml --run-id gemini-live-smoke --providers gemini:gemini-3.1-flash-lite,gemini:gemini-3.5-flash --allow-live --keyword-modes general --max-examples 1 --max-concurrency 1 --max-retries 2 --max-outbound-requests 6
```

Cache replay result:

```text
Requests: 2
Results: 2
Cache hits: 2
Cache misses: 0
Provider executions: 0
Outbound requests: 0
Failures: 0
Provider gemini__gemini-3.1-flash-lite: requests=1, results=1, cache_hits=1, cache_misses=0, provider_executions=0, outbound_requests=0, failures=0
Provider gemini__gemini-3.5-flash: requests=1, results=1, cache_hits=1, cache_misses=0, provider_executions=0, outbound_requests=0, failures=0
```

Gemini live result checks:

| Model ID | Parsed | Schema valid | Keyword coverage | Unsupported keywords | Usage returned | Latency from successful call | Retries | Finish/safety metadata |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `gemini-3.1-flash-lite` | true | true | 1.0 | none | yes | 946.922 ms | 0 | not returned |
| `gemini-3.5-flash` | true | true | 1.0 | none | yes | 2467.837 ms | 0 | not returned |

Observed usage:

- `gemini-3.1-flash-lite`: 98 input tokens, 48 output tokens, 146 total tokens.
- `gemini-3.5-flash`: 98 input tokens, 48 output tokens, 551 total tokens
  including 405 thought tokens.

Secret hygiene:

- Scanned `manifest.json`, `generations/`, `raw/`, and `cache/`.
- No obvious `GEMINI_API_KEY`, `LLM7_API_KEY`, or bearer-token markers found.

Artifacts:

```text
/tmp/community-analysis-sample/_experiments/theme_model_benchmark/gemini-live-smoke/
```

### LLM7 Catalog Review

Catalog:

```text
/tmp/community-analysis-sample/_experiments/theme_model_benchmark/dotenv-llm7-guard/model_catalogs/llm7_models.json
```

Catalog summary:

- Models API accessible: `true`.
- `contains_secrets`: `false`.
- Model count: 12.
- Selected candidates: 0.
- Ambiguous candidate classes: 2 (`turbo`, `pro`).

Viable candidate table:

| Exact model ID | Identity status | Tier | Text I/O | JSON mode | Context tokens | Input/output price | Currency/unit | Minimum request price | Access/pricing notes | Decision |
|---|---|---|---:|---:|---:|---|---|---|---|---|
| `codestral-latest` | routing alias | turbo | yes | yes | 32,000 | 0.01 / 0.01 | USD / 1M tokens | none | not usage-based only | rejected: `latest` alias |
| `devstral-small-2:24b` | exact or not classified by API | turbo | yes | yes | 255,000 | 0.05 / 0.09 | USD / 1M tokens | none | not usage-based only | viable but ambiguous with other turbo candidates |
| `claude-fable-5` | exact or not classified by API | pro | yes | yes | 1,000,000 | 4.5 / 30.0 | USD / 1M tokens | none | usage-based only | viable but ambiguous with other pro candidates |
| `claude-opus-4-8` | exact or not classified by API | pro | yes | yes | 1,000,000 | 2.25 / 12.19 | USD / 1M tokens | 0.002 | usage-based only | viable but ambiguous with other pro candidates |
| `claude-sonnet-5` | exact or not classified by API | pro | yes | yes | 1,000,000 | 0.4 / 2.0 | USD / 1M tokens | 0.000784 | usage-based only | viable but ambiguous with other pro candidates |
| `glm-5.2` | exact or not classified by API | pro | yes | yes | 1,000,000 | 0.45 / 1.57 | USD / 1M tokens | none | usage-based only | viable but ambiguous with other pro candidates |
| `gpt-5.4` | exact or not classified by API | pro | yes | yes | 1,050,000 | 0.5 / 3.31 | USD / 1M tokens | 0.0001 | usage-based only | viable but ambiguous with other pro candidates |
| `gpt-5.4-mini` | exact or not classified by API | pro | yes | yes | 400,000 | 0.16 / 0.9 | USD / 1M tokens | none | usage-based only | viable but ambiguous with other pro candidates |
| `gpt-5.5` | exact or not classified by API | pro | yes | yes | 1,050,000 | 1.0 / 6.0 | USD / 1M tokens | 0.0001 | usage-based only | viable but ambiguous with other pro candidates |
| `minimax-m2.7` | exact or not classified by API | pro | yes | yes | 180,000 | 0.04 / 0.07 | USD / 1M tokens | none | not usage-based only | viable but ambiguous with other pro candidates |

Rejected non-viable entries:

- `deepseek-v4-flash`: rejected because JSON mode is not advertised.
- `kimi-k2.6`: rejected because JSON mode is not advertised.

LLM7 generation status:

- No LLM7 generation was run.
- LLM7 generation now requires:
  - exact non-alias model ID
  - saved `model_catalogs/llm7_models.json`
  - saved user-approved `model_catalogs/llm7_selection.json`
  - source catalog hash match
  - `user_approved=true`
  - text input/output support
  - JSON-mode support
- If upstream provider/model identity is not exposed by the catalog, the
  normalized record uses:
  - `upstream_provider: null`
  - `upstream_model: null`
  - `upstream_identity_status: "not_exposed"`

### Dataset Readiness

Saved theme-input roots inspected:

| Root | Data type | Content type | Year | Months | Source rows | Valid examples | Rejected rows |
|---|---|---|---:|---|---:|---:|---:|
| `/tmp/community-analysis-sample/twitter/_intermediate/theme_inputs/reply/2017` | twitter | reply | 2017 | 03 | 2 | 2 | 0 |
| `/tmp/community-analysis-longitudinal-sample/twitter/_intermediate/theme_inputs/reply/2017` | twitter | reply | 2017 | 03, 04 | 4 | 4 | 0 |

Source hashes:

| Source file | SHA256 |
|---|---|
| `/tmp/community-analysis-sample/twitter/_intermediate/theme_inputs/reply/2017/03_2017.csv` | `37aa6a7a21c45dcc6fbb26ac012805d0658cbd9cf65cd45c530fc8688ef4ae7e` |
| `/tmp/community-analysis-longitudinal-sample/twitter/_intermediate/theme_inputs/reply/2017/03_2017.csv` | `aeea02404ce431896c204f6ec4faa0e62a29ea2d47b9ba90414edfe4e2764eae` |
| `/tmp/community-analysis-longitudinal-sample/twitter/_intermediate/theme_inputs/reply/2017/04_2017.csv` | `d38dc5d3dc93597e658e4765cd849be785528bdde81c8d950ad74856111edd68` |

Readiness assessment:

- Fewer than 15 valid examples are available.
- `theme-benchmark-v1` was not frozen.
- Current live runs must be classified as integration smoke only.
- Compatibility-screen readiness requires additional saved theme-input
  artifacts, preferably enough month/content/data-type coverage to provide at
  least 15 valid examples without duplication or synthesis.

Validation results:

- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark.py`
  - Passed: 11 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_gemini.py`
  - Passed: 15 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_llm7.py`
  - Passed: 22 tests.
- `.venv/bin/python -m pytest tests/unit`
  - Passed: 168 tests.
  - Known warnings only: existing FastAPI TestClient warning and tiny-fixture
    Gensim/SciPy/Kneed/NumPy warnings.
- `make demo`
  - Passed.
  - Demo theme stages still use `LLM_PROVIDER=mock`.
  - API smoke inside demo passed: 12 tests.
- `make api-smoke-test`
  - Passed: 12 tests.
- `make frontend-lint`
  - Passed.
- `make frontend-build`
  - Passed.

Next safe entry point:

- Present the LLM7 candidate table to the user and wait for explicit approval of
  one or two exact non-alias LLM7 model IDs before creating
  `model_catalogs/llm7_selection.json` and running an LLM7 smoke.
- Do not begin Plan 016D until both provider smoke status and dataset readiness
  are explicitly accepted for the next stage.

## 016D Phase 1: Frozen Real Benchmark Dataset

Status: complete for artifact inventory and frozen dataset creation only.

Scope completed:

- Added a saved-artifact inventory path for benchmark readiness.
- Added deterministic frozen dataset construction from saved theme-input
  artifacts.
- Preserved the existing production-equivalent benchmark request contract.
- Preserved the four original LDA keyword fields in every frozen row:
  `absolute_unigram_keywords`, `absolute_bigram_keywords`,
  `weighted_unigram_keywords`, `weighted_bigram_keywords`.
- Did not run Gemini, LLM7, OpenAI, MLflow, CI/CD, human evaluation,
  champion selection, or production-provider replacement.

Files changed:

- `src/themes/benchmark/freeze.py`
  - New benchmark inventory and freeze-dataset implementation.
- `src/cli.py`
  - Added:
    - `theme-benchmark inventory-artifacts`
    - `theme-benchmark freeze-dataset`
- `src/themes/benchmark/review.py`
  - Strengthened review import validation for duplicates, score ranges, and
    provider-identity leakage.
- `tests/unit/test_theme_benchmark_freeze.py`
  - Added focused offline tests for inventory, freezing, split integrity, path
    safety, reproducibility, and review-import validation.
- `docs/exec-plans/active/016-theme-generation-alternatives-benchmark.md`
  - Added this Phase 1 closeout entry.

Design decisions:

- `inventory-artifacts` writes under the fixed benchmark run ID
  `artifact-inventory` because the approved CLI shape has no `--run-id` while
  benchmark outputs must remain under `_experiments/theme_model_benchmark/`.
- `freeze-dataset` writes under the caller-provided run ID; the real v1 dataset
  was frozen as `theme-benchmark-v1`.
- Source configs are deduplicated by resolved saved theme-input root, so the
  four monthly retweet configs point to one real artifact root and do not
  duplicate rows.
- Frozen selection is deterministic and stratified by month, member-count bin,
  keyword-richness bin, and absolute/weighted keyword availability.
- Split assignment is deterministic and independent of row ordering:
  20 development, 30 pilot, and remaining heldout examples for the 100-example
  v1 dataset.
- Benchmark inventory and freezing consume saved theme-input artifacts only and
  never recompute network, community, or LDA stages.

Real artifact inventory:

```bash
.venv/bin/python -m src.cli theme-benchmark inventory-artifacts --config configs/my_retweet_january_2017.yml --source-configs configs/my_retweet_january_2017.yml,configs/my_retweet_february_2017.yml,configs/my_retweet_march_2017.yml,configs/my_retweet_april_2017.yml
```

Result:

```text
Sources: 1
Rows: 400
Valid examples: 400
Rejected rows: 0
Inventory hash: e0666ba7253f647001f4d93a98a4e51811acdcaec8f41a4c4eab18180100105c
```

Inventory artifact:

```text
outputs/my-retweet-2017/_experiments/theme_model_benchmark/artifact-inventory/inventory.json
```

Saved retweet theme-input root:

```text
outputs/my-retweet-2017/twitter/_intermediate/theme_inputs/retweet_quote/2017/
```

Monthly source counts:

| File | Rows | Valid examples | SHA256 |
|---|---:|---:|---|
| `01_2017.csv` | 112 | 112 | `0cc9da57ef2ebe386b693f29e242f2819afda3ab7ff3c5eadf2549141b71cf6a` |
| `02_2017.csv` | 184 | 184 | `863501dfbc7b13daf2e184285f71881536c6389b0f5b97b9136764bc8754eeda` |
| `03_2017.csv` | 86 | 86 | `eea0f9b574a76a0bbc5e7bec4763ddf64640936cc1ab44d8bd96b59acb7c4457` |
| `04_2017.csv` | 18 | 18 | `da4f6ba827891af9f3cf57d6c85c6bf69dca39bfc1fa78f23787cc8868f729a5` |

Frozen dataset command:

```bash
.venv/bin/python -m src.cli theme-benchmark freeze-dataset --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --source-configs configs/my_retweet_january_2017.yml,configs/my_retweet_february_2017.yml,configs/my_retweet_march_2017.yml,configs/my_retweet_april_2017.yml --target-examples 100 --min-examples 40
```

Result, confirmed by an identical rerun:

```text
Available valid examples: 400
Frozen examples: 100
Requests: 300
Split counts: {'development': 20, 'pilot': 30, 'heldout': 50}
Dataset hash: 6b553bc95a601620d752b7763a5f7caea82b50ac2329279da4f22b17e9278951
Split hash: 5065183328ace9fddd39df8d588e8f065c1b99d34373f905ec1f97d857424200
```

Frozen artifacts:

```text
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/manifest.json
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/dataset.jsonl
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/requests.jsonl
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/inventory.json
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/reference/gpt4o_config.json
```

Validation results for this phase:

- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_freeze.py`
  - Passed: 5 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark.py`
  - Passed: 11 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_gemini.py tests/unit/test_theme_benchmark_llm7.py`
  - Passed: 37 tests.

Known limitations:

- Phase 1 does not run candidate providers on the frozen dataset.
- Review import validation is now stricter, but full human-review import and
  scoring summaries remain future 016D work.
- Downstream similarity/transition scoring remains future 016D work and must
  avoid SentenceTransformer downloads in normal tests.
- LLM7 generation remains blocked until an approved exact-model selection
  artifact is created.

Next safe entry point:

- Plan 016D Phase 2 can run offline baseline/mock compatibility checks and
  optionally Gemini candidate evaluation on the `development` and `pilot`
  splits of `theme-benchmark-v1` with strict request caps.
- Do not use the `heldout` split for prompt/model tuning.
- Do not begin champion selection, MLflow, CI/CD, or production-provider
  replacement.

## 016D Phase 2: Development And Pilot Automated Evaluation

Status: complete for split-aware development/pilot automated evaluation.
Heldout evaluation was not started.

Scope completed:

- Added frozen dataset integrity validation and split-distribution reporting.
- Added split-aware benchmark execution for `development`, `pilot`, and
  `heldout`; Phase 2 used only `development` and `pilot`.
- Added an overwrite guard for `freeze-dataset`; differing existing frozen runs
  now require `--overwrite-existing-frozen-run`.
- Added split-scoped generation and score artifacts so development and pilot
  outputs do not overwrite each other.
- Kept provider cache shared by exact cache keys, including provider/model,
  prompt/input hashes, schema versions, keyword mode, and generation settings.
- Did not change production theme generation, public thesis outputs, API
  contracts, dashboard behavior, or normal provider defaults.
- Did not run LLM7 generation.

Files changed in this phase:

- `src/themes/benchmark/integrity.py`
  - New frozen dataset validator and split-distribution report writer.
- `src/themes/benchmark/freeze.py`
  - Added existing-run overwrite guard.
- `src/themes/benchmark/runner.py`
  - Added split filtering, split-scoped outputs, split stats, and aggregate
    split summaries across all provider generation files.
- `src/cli.py`
  - Added:
    - `theme-benchmark validate-dataset`
    - `theme-benchmark run --split development|pilot|heldout`
    - `theme-benchmark freeze-dataset --overwrite-existing-frozen-run`
- `tests/unit/test_theme_benchmark_freeze.py`
  - Added tests for integrity validation, split execution, cache replay, and
    overwrite protection.

Frozen dataset integrity command:

```bash
.venv/bin/python -m src.cli theme-benchmark validate-dataset --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --expected-dataset-hash 6b553bc95a601620d752b7763a5f7caea82b50ac2329279da4f22b17e9278951 --expected-split-hash 5065183328ace9fddd39df8d588e8f065c1b99d34373f905ec1f97d857424200
```

Integrity result:

```text
Examples: 100
Split counts: {'development': 20, 'pilot': 30, 'heldout': 50}
Dataset hash: 6b553bc95a601620d752b7763a5f7caea82b50ac2329279da4f22b17e9278951
Split hash: 5065183328ace9fddd39df8d588e8f065c1b99d34373f905ec1f97d857424200
Limited source scope: data_type=True, content_type=True, year=True
```

Validated protections:

- Dataset hash matched the Phase 1 hash.
- Split hash matched the Phase 1 hash.
- No duplicate example IDs were found.
- Split counts were exactly 20 development, 30 pilot, and 50 heldout.
- Source CSV hashes and source row references were valid.
- Theme-input manifest hash remained valid.
- All four original LDA keyword fields remained present.
- Every example had a production-equivalent `general` request.
- No non-standard JSON values were found.

Split-distribution report:

```text
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/reports/split_distribution.json
```

Distribution summary:

| Dimension | Development | Pilot | Heldout |
|---|---|---|---|
| Month | 01: 5, 02: 5, 03: 6, 04: 4 | 01: 12, 02: 8, 03: 6, 04: 4 | 01: 12, 02: 15, 03: 15, 04: 8 |
| Community size | large: 2, medium: 6, small: 12 | large: 1, medium: 9, small: 20 | large: 1, medium: 17, small: 32 |
| Keyword richness | high: 5, medium: 13, low: 2 | high: 13, medium: 16, low: 1 | high: 17, medium: 32, low: 1 |
| Absolute community coverage | present: 20 | present: 30 | present: 50 |
| Weighted community coverage | present: 20 | present: 30 | present: 50 |

Rejected rows:

- `outputs/my-retweet-2017/twitter/_intermediate/theme_inputs/retweet_quote/2017`: 0.

Dataset scope:

- Limited to one data type: `twitter`.
- Limited to one content type: `retweet_quote`.
- Limited to one year: `2017`.

Offline automated evaluation:

Development command:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --split development --keyword-modes general --providers keyword_baseline,mock
```

Final development cache replay result:

```text
Requests: 40
Results: 40
Cache hits: 40
Cache misses: 0
Provider executions: 0
Outbound requests: 0
Failures: 0
```

Pilot command:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --split pilot --keyword-modes general --providers keyword_baseline,mock
```

Final pilot cache replay result:

```text
Requests: 60
Results: 60
Cache hits: 60
Cache misses: 0
Provider executions: 0
Outbound requests: 0
Failures: 0
```

Gemini development evaluation:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --split development --keyword-modes general --providers gemini:gemini-3.1-flash-lite,gemini:gemini-3.5-flash --allow-live --max-concurrency 1 --max-retries 2 --max-outbound-requests 120
```

Initial sandboxed attempt failed with DNS:

```text
Gemini provider_error: [Errno 8] nodename nor servname provided, or not known
```

Escalated development run succeeded after one transient/provider quota retry
was later filled by exact replay:

```text
Requests: 40
Results: 40
Cache hits: 40
Cache misses: 0
Provider executions: 0
Outbound requests: 0
Failures: 0
```

Provider-level development replay:

```text
gemini__gemini-3.1-flash-lite: requests=20, cache_hits=20, failures=0
gemini__gemini-3.5-flash: requests=20, cache_hits=20, failures=0
```

Gemini pilot evaluation:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --split pilot --keyword-modes general --providers gemini:gemini-3.1-flash-lite,gemini:gemini-3.5-flash --allow-live --max-concurrency 1 --max-retries 2 --max-outbound-requests 180
```

Pilot result:

```text
Requests: 60
Results: 60
Cache hits: 0
Cache misses: 60
Provider executions: 60
Outbound requests: 119
Failures: 29
```

Provider-level pilot result:

```text
gemini__gemini-3.1-flash-lite: requests=30, results=30, failures=0, outbound_requests=31
gemini__gemini-3.5-flash: requests=30, results=30, failures=29, outbound_requests=88
```

Pilot blocker:

- All 29 `gemini-3.5-flash` pilot failures were provider quota responses:
  `Error code: 429` with `code: too_many_requests`.
- `gemini-3.1-flash-lite` completed all 30 pilot requests successfully.
- Live Gemini was stopped after this quota blocker; no heldout live requests
  were run.

Score artifacts:

```text
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/development_summary.csv
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/pilot_summary.csv
```

Automatic metric snapshot:

| Split | Provider | Requests | Error rate | Cache hit rate | Avg keyword coverage |
|---|---|---:|---:|---:|---:|
| development | `keyword_baseline` | 20 | 0.0 | 1.0 | 1.0 |
| development | `mock` | 20 | 0.0 | 1.0 | 0.1996 |
| development | `gemini__gemini-3.1-flash-lite` | 20 | 0.0 | 1.0 | 0.9913 |
| development | `gemini__gemini-3.5-flash` | 20 | 0.0 | 1.0 | 0.9944 |
| pilot | `keyword_baseline` | 30 | 0.0 | 1.0 | 1.0 |
| pilot | `mock` | 30 | 0.0 | 1.0 | 0.1479 |
| pilot | `gemini__gemini-3.1-flash-lite` | 30 | 0.0 | 0.0 | 0.9844 |
| pilot | `gemini__gemini-3.5-flash` | 30 | 0.9667 | 0.0 | 0.0333 |

Secret hygiene:

- Scanned the frozen benchmark run for `GEMINI_API_KEY`, `LLM7_API_KEY`,
  `Bearer `, and `AIza`.
- No matches were found.

Validation results after Phase 2 implementation:

- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark.py tests/unit/test_theme_benchmark_freeze.py tests/unit/test_theme_benchmark_gemini.py tests/unit/test_theme_benchmark_llm7.py`
  - Passed: 56 tests.
- `.venv/bin/python -m pytest tests/unit`
  - Passed: 176 tests.
  - Known warnings only: existing FastAPI TestClient warning and tiny-fixture
    Gensim/SciPy/Kneed/NumPy warnings.
- `make api-smoke-test`
  - Passed: 12 tests.
- `make frontend-lint`
  - Passed.
- `make frontend-build`
  - Passed.
- `make demo`
  - Passed.
  - Demo theme stages still use `LLM_PROVIDER=mock`.

Known limitations:

- Pilot evaluation is incomplete for `gemini-3.5-flash` due provider quota.
- No heldout generation, human evaluation, stability evaluation, champion
  selection, MLflow, CI/CD, or production-provider replacement was performed.
- LLM7 remains blocked pending an approved exact model ID and selection
  artifact.

Next safe entry point:

- Resolve the Gemini 3.5 pilot quota blocker or rerun only the missing pilot
  `gemini-3.5-flash` requests with the exact same generation settings and
  strict caps.
- Keep heldout sealed until development/pilot evaluation is complete and the
  evaluation protocol is accepted.
- Do not promote any provider to production.

### 016D Phase 2 Quota-Recovery Closeout

Status: complete under acceptance path B:

- `gemini-3.5-flash` pilot remains incomplete due external provider quota.
- Partial metrics are documented separately.
- Incomplete `gemini-3.5-flash` pilot metrics are not valid for ranking against
  complete candidates.
- No further safe retry was available after quota returned again in a capped
  recovery batch.

Frozen dataset revalidation:

```bash
.venv/bin/python -m src.cli theme-benchmark validate-dataset --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --expected-dataset-hash 6b553bc95a601620d752b7763a5f7caea82b50ac2329279da4f22b17e9278951 --expected-split-hash 5065183328ace9fddd39df8d588e8f065c1b99d34373f905ec1f97d857424200
```

Result:

```text
Examples: 100
Split counts: {'development': 20, 'pilot': 30, 'heldout': 50}
Dataset hash: 6b553bc95a601620d752b7763a5f7caea82b50ac2329279da4f22b17e9278951
Split hash: 5065183328ace9fddd39df8d588e8f065c1b99d34373f905ec1f97d857424200
```

Original pilot reconciliation before quota recovery:

| Provider | Expected requests | Successful generation results | Schema-valid results | Failed results | Quota failures | Non-quota failures | Successful cache entries for pilot | Unresolved requests |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `gemini__gemini-3.1-flash-lite` | 30 | 30 | 30 | 0 | 0 | 0 | 30 | 0 |
| `gemini__gemini-3.5-flash` | 30 | 1 | 1 | 29 | 29 | 0 | 1 | 29 |

Clarification:

- The previous `29/30 failed` statement for `gemini-3.5-flash` pilot meant
  exactly: 1 successful schema-valid pilot result and 29 quota-failed pilot
  results.
- The 429 failures were not inserted into the successful cache.
- Duplicate result records did not inflate counts.

Flash-Lite pilot replay:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --split pilot --keyword-modes general --providers gemini:gemini-3.1-flash-lite --allow-live --max-concurrency 1 --max-retries 2 --max-outbound-requests 180
```

Result:

```text
Requests: 30
Results: 30
Cache hits: 30
Cache misses: 0
Provider executions: 0
Outbound requests: 0
Failures: 0
```

Generic recovery mechanism added:

- `theme-benchmark run --resume-unresolved`
- `theme-benchmark run --max-unresolved-examples N`
- The filter is provider-neutral and selects only requests without successful
  cache entries for the selected provider/model/settings.
- It does not delete successful cache entries and does not touch heldout.

Recovery command shape:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --split pilot --keyword-modes general --providers gemini:gemini-3.5-flash --allow-live --max-concurrency 1 --max-retries 2 --max-outbound-requests 180 --resume-unresolved --max-unresolved-examples 3
```

Recovery batches:

| Batch | Unresolved before | New successes | Quota failures | Other failures | Cache hits | Provider executions | Outbound attempts | Unresolved after |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 29 | 3 | 0 | 0 | 0 | 3 | 3 | 26 |
| 2 | 26 | 3 | 0 | 0 | 0 | 3 | 3 | 23 |
| 3 | 23 | 3 | 0 | 0 | 0 | 3 | 3 | 20 |
| 4 | 20 | 3 | 0 | 0 | 0 | 3 | 3 | 17 |
| 5 | 17 | 3 | 0 | 0 | 0 | 3 | 3 | 14 |
| 6 | 14 | 3 | 0 | 0 | 0 | 3 | 3 | 11 |
| 7 | 11 | 3 | 0 | 0 | 0 | 3 | 3 | 8 |
| 8 | 8 | 2 | 1 | 0 | 0 | 3 | 7 | 6 |

Stopping reason:

- Batch 8 returned a provider quota response again:
  `Error code: 429` with `code: too_many_requests`.
- Recovery stopped after that capped invocation.
- No loop-until-success behavior was used.

Final Flash pilot state:

| Provider | Expected pilot requests | Successful cached pilot results | Missing pilot requests | Current quota-blocked requests | Completion |
|---|---:|---:|---:|---:|---|
| `gemini__gemini-3.1-flash-lite` | 30 | 30 | 0 | 0 | complete |
| `gemini__gemini-3.5-flash` | 30 | 24 | 6 | 6 | incomplete/provider-blocked |

Reports regenerated:

```bash
.venv/bin/python -m src.cli theme-benchmark summarize --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1
```

Artifacts:

```text
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/development_summary.csv
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/pilot_summary.csv
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/preliminary_model_scorecard.csv
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/phase2_evaluation_report.json
```

Report status:

```text
Completion status: incomplete_provider_blocked
```

The regenerated scorecard includes `comparison_eligible=false` for incomplete
`gemini__gemini-3.5-flash` rows, so partial Flash metrics are descriptive only
and are not rankable against complete candidates.

Scorecard candidate policy:

- Included as quality candidates:
  - `keyword_baseline`
  - `gemini__gemini-3.1-flash-lite`
  - `gemini__gemini-3.5-flash`
- Excluded from model-quality candidate comparisons:
  - `mock`

Final scorecard counts:

| Scope | Provider | Requests | Successful cached results | Missing requests | Provider failure rate |
|---|---|---:|---:|---:|---:|
| development | `keyword_baseline` | 20 | 20 | 0 | 0.00 |
| development | `gemini__gemini-3.1-flash-lite` | 20 | 20 | 0 | 0.00 |
| development | `gemini__gemini-3.5-flash` | 20 | 20 | 0 | 0.00 |
| pilot | `keyword_baseline` | 30 | 30 | 0 | 0.00 |
| pilot | `gemini__gemini-3.1-flash-lite` | 30 | 30 | 0 | 0.00 |
| pilot | `gemini__gemini-3.5-flash` | 30 | 24 | 6 | 0.20 |
| combined development+pilot | `keyword_baseline` | 50 | 50 | 0 | 0.00 |
| combined development+pilot | `gemini__gemini-3.1-flash-lite` | 50 | 50 | 0 | 0.00 |
| combined development+pilot | `gemini__gemini-3.5-flash` | 50 | 44 | 6 | 0.12 |

Heldout seal audit:

- No `generations/heldout` path exists.
- No heldout raw-response paths exist.
- No heldout score path exists.
- No heldout review export exists.
- Heldout request IDs were not present in Phase 2 scorecard/report artifacts.
- Heldout provider executions: 0.

Secret hygiene:

- Scanned frozen experiment root for:
  - `GEMINI_API_KEY`
  - `LLM7_API_KEY`
  - `Bearer `
  - `AIza`
- No matches found.

Validation results:

- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_freeze.py`
  - Passed: 9 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark.py`
  - Passed: 11 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_gemini.py`
  - Passed: 15 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_llm7.py`
  - Passed: 22 tests.
- `.venv/bin/python -m pytest tests/unit`
  - Passed: 177 tests.
  - Known warnings only: existing FastAPI TestClient warning and tiny-fixture
    Gensim/SciPy/Kneed/NumPy warnings.
- `make demo`
  - Passed.
- `make api-smoke-test`
  - Passed: 12 tests.
- `make frontend-lint`
  - Passed.
- `make frontend-build`
  - Passed.

Next safe entry point:

- Phase 2 remains closed as incomplete/provider-blocked for
  `gemini-3.5-flash` pilot unless the user explicitly asks for another small
  quota-recovery attempt later.
- Do not begin Phase 3 until the user explicitly authorizes it.
- Do not run heldout, stability, human review, downstream evaluation, final
  model selection, MLflow, CI/CD, or production-provider replacement.

## 016D Phase 3: Paired Review Preparation And Small Stability Evaluation

Status: complete for Phase 3 framework and capped stability attempt. No heldout
evaluation, final human scoring, model selection, or production-provider change
was performed.

Files changed:

- `src/themes/benchmark/phase3.py`
  - Added paired cohort creation, blinded review package generation, review
    import validation/summaries, stability subset selection, and stability
    summary generation.
- `src/themes/benchmark/runner.py`
  - Added explicit example-ID filtering and repetition-index-aware cache
    identity.
- `src/cli.py`
  - Added:
    - `theme-benchmark prepare-phase3-review`
    - `theme-benchmark import-phase3-review`
    - `theme-benchmark prepare-stability-subset`
    - `theme-benchmark summarize-stability`
    - `theme-benchmark run --example-ids-file`
    - `theme-benchmark run --repetition-index`
- `tests/unit/test_theme_benchmark_phase3.py`
  - Added offline tests for paired cohort creation, blinding, review import,
    single-reviewer summary behavior, stability subset creation, and
    repetition-aware stability summaries.

### Paired Review Cohort

Command:

```bash
.venv/bin/python -m src.cli theme-benchmark prepare-phase3-review --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1
```

Result:

```text
Phase 3 review cohort examples: 40
Cohort hash: e5aac028d968aac163df6d7377d267a27f8b2b2695f73cf9548d065634e24e1d
Review package written to outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/review/phase3
```

Cohort composition:

- Development examples: 20.
- Pilot examples: 20.
- Heldout examples: 0.
- Providers required for inclusion:
  - `keyword_baseline`
  - `gemini__gemini-3.1-flash-lite`
  - `gemini__gemini-3.5-flash`
- Mock, LLM7, failed outputs, unresolved Flash pilot outputs, and heldout
  examples were excluded.

Selection policy:

- Include all shared-complete development examples.
- Select pilot examples only from the shared-complete intersection.
- Use deterministic hash-stratified selection by member-count bin,
  keyword-richness bin, and month.
- Selection does not inspect provider output quality.

Artifacts:

```text
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/review/phase3/cohort_manifest.json
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/review/phase3/review_items.csv
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/review/phase3/review_instructions.md
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/review/phase3/blinding_key.json
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/review/phase3/review_manifest.json
```

Blinding strategy:

- Reviewer-facing file uses `Output A`, `Output B`, and `Output C`.
- Provider/model IDs, raw paths, latency, token, and cost fields are not present
  in `review_items.csv`.
- Provider-to-alias mapping is stored only in private `blinding_key.json`.
- Alias positions are deterministic and balanced by cycling provider
  permutations across review items.
- Reviewer-facing leakage check passed:
  `contains_provider_names_in_reviewer_file: false`.

Rubric:

- Scores are 1-5 where 5 is better for all criteria.
- `unsupported_content_absence` uses 1 for severe unsupported content and 5 for
  no unsupported content.
- Preferred output values: `A`, `B`, `C`, `tie`, or `none`.
- Reviewer confidence values: `low`, `medium`, or `high`.
- Codex did not fill or fabricate human scores.

Review import support:

- Validates known review item IDs.
- Requires reviewer IDs.
- Rejects duplicate reviewer/item submissions.
- Rejects invalid score ranges.
- Rejects invalid preferred-output or confidence values.
- Rejects provider/model identity leakage.
- Rejects partial reviews in this importer.
- Unblinds through the private mapping only after validation.
- Generates per-provider summaries and reports
  `inter_rater_reliability: unavailable_single_reviewer` for one reviewer.

Actual human review remains pending until the user supplies completed scores.

### Stability Subset

Command:

```bash
.venv/bin/python -m src.cli theme-benchmark prepare-stability-subset --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1
```

Result:

```text
Stability subset examples: 10
Subset hash: 1bf94dc2872fb948f6183bde9822ca853206f3f59607185bbd2dc4bad45a0eb0
```

Artifact:

```text
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/stability_subset.json
```

Selection policy:

- Development split only.
- 10 examples.
- Both Gemini models must have successful Phase 2 outputs for repetition 0.
- Deterministic hash-stratified selection by member-count bin,
  keyword-richness bin, and month.
- No pilot or heldout examples.
- No output-quality-based selection.

Repetition semantics:

- Repetition 0 reuses existing Phase 2 cached development outputs.
- Repetition 1 and 2 add `repetition_index` to cache identity.
- Repetition index does not alter prompt text, keyword order, schema,
  temperature, model ID, or Gemini `store=false`.
- Replaying repetition 1 for Flash-Lite reused its own cache with zero outbound
  requests.

### Stability Live Runs

Flash-Lite repetition 1:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --split development --example-ids-file outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/stability_subset.json --keyword-modes general --providers gemini:gemini-3.1-flash-lite --allow-live --max-concurrency 1 --max-retries 1 --max-outbound-requests 25 --repetition-index 1
```

Result:

```text
Requests: 10
Results: 10
Cache hits: 0
Cache misses: 10
Provider executions: 10
Outbound requests: 10
Failures: 0
```

Flash-Lite repetition 2:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --split development --example-ids-file outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/stability_subset.json --keyword-modes general --providers gemini:gemini-3.1-flash-lite --allow-live --max-concurrency 1 --max-retries 1 --max-outbound-requests 25 --repetition-index 2
```

Result:

```text
Requests: 10
Results: 10
Cache hits: 0
Cache misses: 10
Provider executions: 10
Outbound requests: 11
Failures: 1
```

Flash-Lite repetition 1 cache replay:

```text
Requests: 10
Results: 10
Cache hits: 10
Cache misses: 0
Provider executions: 0
Outbound requests: 0
Failures: 0
```

Gemini Flash repetition 1:

```bash
.venv/bin/python -m src.cli theme-benchmark run --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1 --split development --example-ids-file outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/stability_subset.json --keyword-modes general --providers gemini:gemini-3.5-flash --allow-live --max-concurrency 1 --max-retries 1 --max-outbound-requests 25 --repetition-index 1
```

Result:

```text
Requests: 10
Results: 10
Cache hits: 0
Cache misses: 10
Provider executions: 10
Outbound requests: 17
Failures: 7
```

Stopping reason:

- Gemini Flash returned quota/provider failures during repetition 1.
- Flash repetition 2 was not attempted.
- No retry loop or cap increase was performed.

### Stability Metrics

Command:

```bash
.venv/bin/python -m src.cli theme-benchmark summarize-stability --config configs/my_retweet_january_2017.yml --run-id theme-benchmark-v1
```

Artifacts:

```text
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/stability_results.csv
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/stability_summary.csv
outputs/my-retweet-2017/_experiments/theme_model_benchmark/theme-benchmark-v1/scores/phase3_stability_report.json
```

Report status:

```text
Completion status: partial
```

Summary:

| Provider | Examples | Complete examples | Mean exact JSON agreement | Mean keyword Jaccard | Status |
|---|---:|---:|---:|---:|---|
| `gemini__gemini-3.1-flash-lite` | 10 | 9 | 1.0 | 1.0 | partial |
| `gemini__gemini-3.5-flash` | 10 | 0 | unavailable | unavailable | partial |

Unequal coverage is explicitly labeled partial. No provider comparison, winner,
or recommendation is made from these stability metrics.

### Heldout And Secret Audits

- No `heldout` paths were found under the frozen benchmark root.
- No heldout request IDs were included in review cohort, review package, or
  stability files.
- Heldout provider executions: 0.
- Secret-marker scan over the frozen benchmark root found no matches for:
  - `GEMINI_API_KEY`
  - `LLM7_API_KEY`
  - `Bearer `
  - `AIza`

### Validation

- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_freeze.py`
  - Passed: 9 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark.py`
  - Passed: 11 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_gemini.py`
  - Passed: 15 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_llm7.py`
  - Passed: 22 tests.
- `.venv/bin/python -m pytest tests/unit/test_theme_benchmark_phase3.py`
  - Passed: 3 tests.
- `.venv/bin/python -m pytest tests/unit`
  - Passed: 180 tests.
  - Known warnings only: existing FastAPI TestClient warning and tiny-fixture
    Gensim/SciPy/Kneed/NumPy warnings.
- `make demo`
  - Passed.
- `make api-smoke-test`
  - Passed: 12 tests.
- `make frontend-lint`
  - Passed.
- `make frontend-build`
  - Passed.

### Phase 3 Limitations And Next Entry Point

Pending:

- Actual human review completion.
- Heldout evaluation.
- Final statistical comparison.
- Final recommendation.
- Production-provider promotion.
- Plan 017.

Next safe entry point:

- Import completed human-review scores with
  `theme-benchmark import-phase3-review --scores <completed_review.csv>`, or
  explicitly authorize a later small stability-recovery pass.
- Do not begin heldout evaluation or final selection without explicit user
  approval.
