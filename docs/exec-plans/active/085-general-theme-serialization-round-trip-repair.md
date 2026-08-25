# Plan 085 — General Theme Serialization Round-Trip Repair & Clustering Revalidation

Status: implemented; Telegram revalidated; Twitter revalidation pending

Owner: agent

Last updated: 2026-08-23

## 1. Objective

Repair the Stage-A theme-label interpretation bug where scalar `general_theme_names`
values containing semantic commas were passed through the shared generic comma
fallback parser before the existing `general_theme_gpt` round-trip protection could
reconstruct the original generated labels.

This plan changes serialization interpretation only. It does not tune monthly HDBSCAN
or change the Plan-084 Stage-B algorithm.

## 2. Verified failure

A production-shaped saved value such as:

```text
Media content production, metadata, and episodic structure.Online social network and recruitment dynamics
```

with matching `general_theme_gpt` keys was interpreted as fragments such as
`Media content production`, `metadata`, and a composite remainder because
`_general_theme_names()` called the shared `_parse_list()` comma fallback before the
round-trip check.

The Telegram June validation artifact showed the same failure class: valid generated
labels existed upstream, but comma-fragmented observations contaminated the monthly
clustering population. HDBSCAN parameter changes are therefore out of scope until the
serialization boundary is repaired and revalidated on clean labels.

## 3. Production contract

- `general_theme_names` remains the only clustering label source.
- `general_theme_names` is not comma-delimited; commas inside a theme label are semantic text.
- Native list/tuple and JSON/Python serialized list forms remain structured lists.
- For an ordinary scalar string, parse it as one saved label before clustering.
- For the historical dot-joined multi-theme scalar, consult `general_theme_gpt` against
  the raw saved scalar before any generic comma fallback. Use mapping keys only when
  `".".join(mapping.keys())` round-trips exactly after display normalization.
- Preserve per-label mapped LDA keyword evidence when round-trip reconstruction succeeds.
- Missing `general_theme_names` cannot be supplied by `general_theme_gpt`.
- A structurally ambiguous dot-joined scalar with missing/mismatched mapping remains
  excluded and counted as `excluded_records_ambiguous_general_theme_serialization`.
- Legitimate punctuation such as `U.S. Immigration Policy` remains valid.
- Do not modify shared `src/themes/theme_inputs.py::_parse_list()`.

## 4. Versioning and cache invalidation

- Bump `MONTHLY_CLUSTER_CONTRACT_VERSION` from `2.1` to `2.2` because the admitted
  Stage-A observation population changes.
- Keep `CANONICALIZATION_CONTRACT_VERSION=4.0`; Stage B is unchanged.
- Bump `THEME_STAGE_CACHE_VERSION` from `2.2.0` to `2.3.0`.
- Include `MONTHLY_CLUSTER_CONTRACT_VERSION` explicitly in the theme-stage cache key.
- Translation, network/community, and topic-stage cache contracts remain unchanged.

## 5. Frozen analytical behavior

Do not change:

- `shared_post` / `weighted_post`;
- graph thresholds;
- Louvain defaults;
- LDA behavior/defaults;
- translation behavior;
- GPT prompts/provider behavior;
- clustering embedding model/revision;
- monthly HDBSCAN implementation or parameters;
- Stage-B representative-vector representation;
- Stage-B cosine complete linkage or similarity threshold `0.65`;
- community matching/evolution;
- API/frontend analytical behavior;
- output categories.

## 6. Regression coverage

Required tests cover:

- multiple dot-joined labels whose individual labels contain commas;
- one comma-bearing scalar label remaining atomic;
- comma-bearing scalar without a mapping remaining atomic;
- native structured lists preserving commas inside items;
- JSON and Python serialized lists preserving commas inside items;
- recovered labels retaining their own mapped LDA keyword evidence;
- missing-name non-recovery from mapping;
- ambiguous dot-joined mismatched/missing mapping exclusion;
- abbreviation safety;
- monthly clustering contract `2.2` provenance;
- theme-stage cache identity changing across monthly-clustering contract revisions.

## 7. Validation

Run where dependencies are available:

```bash
python -m compileall -q src tests
PYTHONPATH=. pytest -q tests/unit/test_theme_clustering.py
PYTHONPATH=. pytest -q \
  tests/unit/test_theme_clustering.py \
  tests/unit/test_canonical_theme_benchmark.py \
  tests/unit/test_orchestration_hashing.py \
  tests/unit/test_output_artifact_contract.py
python -m src.cli validate-config --config tests/configs/test_single_month.yml
make format
make lint
make test
git diff --check
```

Automated tests must not call OpenAI, translation providers, or TEI.

## 8. Real-run revalidation gate

After patch application in the fully provisioned local environment:

1. Run Telegram translation preflight and confirm cached/no-unexpected-cloud workload.
2. Rerun the Telegram forwarded-message evolution pipeline with unchanged algorithms.
3. Verify June source labels are intact before judging cluster counts/noise.
4. Observe unchanged HDBSCAN behavior on the corrected Stage-A population.
5. Re-run the read-only Stage-B benchmark and confirm production remains equal to the
   Plan-083 representative + complete-linkage cosine-0.65 candidate.
6. Repeat the serialization audit and, if materially affected, production revalidation
   on Twitter Retweet-Quote.

If corrected serialization resolves June, stop; do not tune HDBSCAN. Only if June
remains pathologically noisy on clean labels should a separate read-only Stage-A
clustering benchmark be proposed.

## 9. Progress log

- 2026-08-23: Treated `community-analysis-full-review-20260823-1732.zip` as the source
  of truth (branch `feature/frontend-ui-upgrade`, HEAD
  `c5ee46215b43618ac58c39fd8416f155c3e07bcf`, clean archived working tree).
- 2026-08-23: Read the required repository contracts in the prescribed order plus
  Plans 043 and 084 before editing.
- 2026-08-23: Reproduced the comma-fragmentation bug directly from the source with a
  production-shaped comma-bearing dot-joined mapping fixture.
- 2026-08-23: Added failing regression coverage before modifying production logic.
- 2026-08-23: Repaired only the field-specific `general_theme_names` interpretation
  boundary; shared `_parse_list()` and the theme producer remain unchanged.
- 2026-08-23: Bumped monthly clustering contract `2.1 -> 2.2`, kept Stage-B contract
  `4.0`, bumped theme-stage cache `2.2.0 -> 2.3.0`, and added explicit monthly-contract
  cache-key identity.
- 2026-08-23: Focused regression suite passed: 93 tests across theme clustering,
  Stage-B benchmark parity, orchestration hashing, clustered-theme API service, and
  configuration contracts.
- 2026-08-23: `python -m compileall -q src tests` and direct CLI config validation
  passed.
- 2026-08-23: Parquet-writing output-contract and one theme-pipeline test were
  environment-blocked because the review interpreter has neither `pyarrow` nor
  `fastparquet`; this was not treated as a product failure.
- 2026-08-23: Broader `tests/unit` collection was environment-blocked by missing
  optional/project dependencies (`kneed`, `mlflow`, `prefect`, `demoji`).
- 2026-08-23: `make format` was blocked by the archive-local `.venv` being absent.
  `make lint` and `make test` attempted frozen `uv` dependency resolution and were
  blocked by unavailable network/DNS. No dependencies or analytical defaults were
  changed to bypass those environment boundaries.
- 2026-08-23: Patch scope/static review confirmed only the field-specific parser,
  theme-stage cache identity, focused tests, Plan 085, and directly relevant contract
  docs changed; shared `_parse_list()`, theme generation, HDBSCAN defaults, Stage-B
  algorithm, IF/WIF, Louvain, LDA, translation, API, and frontend code remain untouched.
- 2026-08-23: Real Telegram run `f1d62bc2-88ba-4407-98c1-9c48e2f28f41` revalidated
  Plan 085 on clean artifacts: June contained 55 intended labels, 55 correctly parsed
  Stage-A observations, zero comma-fragment artifacts, seven monthly clusters, and 25
  noise observations. The missing-June symptom is resolved without changing HDBSCAN.
- 2026-08-23: The same clean run revalidated production Stage B: 71 monthly clusters
  grouped into 57 canonical families, and reconstruction with the contract-4.0 monthly
  representative + complete-linkage cosine-0.65 method matched the production partition.
- 2026-08-23: Clean-label review exposed an independent Stage-A robustness question:
  October had 29/29 observations classified as noise, while July contained one
  heterogeneous 76-observation cluster. These findings are isolated into read-only Plan
  086; Plan 085 remains a serialization repair and does not tune HDBSCAN.
