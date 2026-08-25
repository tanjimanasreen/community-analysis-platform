# Theme Intelligence Contract

This contract covers the implemented features in `theme-analysis.py`.

## Inputs

Theme analysis starts from monthly matched LDA outputs:

```text
<data_type>/LDA/matched/<content_type>/<month>_<year>.parquet
```

Required columns:

- `members`
- `absolute_community`
- `weighted_community`
- `absolute_unigram_keywords`
- `absolute_bigram_keywords`
- `weighted_unigram_keywords`
- `weighted_bigram_keywords`

## Keyword Preparation

The current implementation creates:

- `all_keywords`
- `absolute_keywords`
- `weighted_keywords`

Rules:

- Parse stringified list columns with `ast.literal_eval`.
- Combine unigram and bigram keywords.
- De-duplicate keywords while preserving order.
- Convert keyword lists to comma-separated strings for GPT prompting.

## GPT Theme Generation

Current generated theme types:

- `general_theme_gpt`
- `general_theme_names`
- `absolute_theme_gpt`
- `absolute_theme_names`
- `weighted_theme_gpt`
- `weighted_theme_names`

Current generated-theme provider behavior:

- `theme` is reserved for analytical theme-processing settings such as rendering,
  similarity, and worker controls.
- `theme_provider` is the canonical provider-routing namespace for `primary`,
  `fallback`, `fallback_chain`, cache, timeout, and retry settings.
- Legacy `theme.fallback` and `theme.fallback_chain` settings are rejected during
  run-config validation so provider routing cannot be silently accepted and ignored.
- Provider routing is configured through `theme_provider` in `configs/providers.yml`.
- Current production primary: `openai:gpt-5-nano`.
- OpenAI generation uses the Responses API with strict JSON Schema structured output.
- Theme prompt contract `v3` is defined centrally in code (not repeated in dataset YAML).
  It requires faithful, descriptive, non-endorsing, severity-preserving labels: supported
  sensitive/extreme subject matter must not be euphemized or softened, and labels must not
  introduce claims stronger than the LDA evidence supports.
- Provider wire output returns theme names plus zero-based `keyword_indices`; Python
  reconstructs supporting keyword strings from the exact ordered input, so providers do not
  reproduce or rewrite the analytical keyword evidence. Prompt V3 presents each unchanged
  keyword with an explicit bracketed zero-based ID, and each structured-output request derives
  an independent schema bounded to `0..N-1` for that request's `N` keywords. The canonical
  shared schema is never mutated, so concurrent requests with different keyword counts remain
  isolated.
- The benchmark/request layer preserves the current packaged Jinja prompt templates and
  records prompt-contract/output-schema versions plus prompt hashes for reproducibility.
- Prompt input remains ordered LDA keyword evidence; generated themes stay downstream of LDA.
- A persistent typed provider safety outcome (`content_filter` or policy refusal) is scoped to
  that unique payload. The community/LDA evidence remains present, the generated theme is
  unavailable, provenance is recorded, and processing continues for other payloads. Unexpected
  provider/software failures remain fail-fast.
- Theme similarity never embeds a missing generated label; comparisons involving a missing
  interpretation are persisted as unavailable/null rather than as an empty-string similarity.

Production requirements:

- Wrap GPT calls behind a provider interface.
- Support cached responses.
- Support offline mocked responses for tests.
- Do not require OpenAI for network/LDA pipeline tests.

## Community Transition

Current behavior:

- Compares consecutive months.
- Uses Jaccard similarity over `members`.
- Requires at least one shared member (`Jaccard > 0`) for every transition.
- For `reply`, threshold is `0.0`, so every positive-overlap pair qualifies.
- For all other content types, threshold is `0.5` and the boundary is inclusive.
- Explicit threshold overrides remain an additional lower bound; a zero-overlap
  pair is never a transition.
- Writes `community_transition.parquet`.

Output columns include:

- `start_month`
- `end_month`
- `start_month_community`
- `end_month_community`
- `jaccard_score`
- `common_members`
- `uncommon_members`
- `start_month_members`
- `total_start_month_members`
- `end_month_members`
- `total_end_month_members`
- theme fields for absolute, weighted, and general themes

Serialization requirement:

- Transition member-list fields (`common_members`, `uncommon_members`,
  `start_month_members`, and `end_month_members`) must serialize member IDs as
  native Python scalar values. NumPy scalar representations such as
  `np.int64(...)` or `np.str_(...)` are not valid persisted member-list
  representations because downstream path/mobility readers must be able to
  parse the saved lists deterministically. This normalization does not change
  Jaccard membership semantics or transition thresholds.

## Sankey Transition Diagram

Current behavior:

- Builds source and target indices from transition rows.
- Uses month-specific node colors.
- Uses link intensity based on Jaccard score.
- Saves:
  - `community_transition.png`
  - `community_transition.html`

Production requirements:

- Keep static image export optional because Plotly image export may require Kaleido.
- Always save HTML when visualization succeeds.

## Path Detection

Current behavior:

- Builds a directed graph from Sankey source/target links.
- Finds start nodes with zero in-degree.
- Finds end nodes with zero out-degree.
- Uses DFS to find all start-to-end paths.

This feature must be preserved because membership-change and theme-similarity visualizations depend on it.

Production persistence contract:

- The existing `get_path_info` + `find_all_sankey_paths` DFS behavior remains the
  authority for persistent path identity.
- Paths are assigned deterministic content-derived internal IDs plus a deterministic
  display order; dashboard path counts are read from the saved artifact and are never hard-coded.
- API request handlers must not reconstruct paths or substitute connected components.

## Membership-Change Visualization

Current behavior:

- Calculates existing, new, lost, and reappearing members over each detected path.
- Draws per-path diagrams.
- Saves `community_changes_<n>.png`.

Production requirements:

- Preserve the existing/new/lost/reappearing set semantics exactly.
- Persist the per-path member states as analytical data even when visual report
  rendering is disabled.
- Dashboard presentation may use different accessible labels/encodings, but must
  not redefine the underlying categories. Reappearing members remain the subset
  `(current ∩ seen) - previous` from the thesis function.
- Add tests for membership-change calculations, including a leave-and-return case.
- Do not require rendering tests to inspect image pixels in the first production version.

## Theme Similarity

Current behavior:

- Uses SentenceTransformer `paraphrase-MiniLM-L6-v2`.
- Computes cosine similarity between theme sentences.
- Draws upper-triangle heatmaps for:
  - absolute themes
  - weighted themes
  - general themes

Production requirements:

- Keep the Community Evolution embedding profile separate from theme clustering
  and revision-pin `paraphrase-MiniLM-L6-v2` in production configuration.
- Persist path-scoped general/absolute/weighted cosine records and immutable
  float32 similarity embeddings before optional visualization rendering.
- `evolution_similarity_enabled` controls semantic computation independently from
  `render_visuals`; rendering must not be required for analytical artifacts.
- Cache/deduplicate exact strings through the shared embedding recorder where possible.
- Add deterministic tests for sentence similarity shape/diagonal behavior and
  path-scoped similarity publication.

## Dashboard Exact-Theme Trend Read Model

The dashboard publishes additive, read-only aggregations over saved monthly
matched-theme artifacts. These aggregations do not run LDA, providers,
embeddings, community detection, transitions, or similarity calculations.

### Exact label and matched-pair semantics

- Pair identity is the normalized `absolute_community` plus normalized
  `weighted_community`.
- Rows with neither ID are excluded and counted in response metadata.
- `general_theme_names` is authoritative when present. General provider mapping
  keys may supply names when the names field is absent. IF/WIF labels are used
  only when no general label is available.
- Exact labels are case- and punctuation-sensitive and are never merged by
  synonym, topic identity, fuzzy matching, embeddings, or GPT.
- Repeated occurrences of one label for one pair count once. A pair carrying
  multiple labels contributes once to each label.
- Monthly percentage uses total themed matched pairs as its denominator; labels
  may therefore sum beyond 100 percent.
- LDA keyword evidence is drawn only from rows carrying that exact label and is
  ranked by distinct pair coverage, source order, then lexical order.

### Timeline semantics

The most-discussed exact label ranks by:

1. total distinct community-pair/month count;
2. months present;
3. peak monthly pair count;
4. exact label ascending.

Its series is zero-filled across the selected available periods.

### Dashboard aggregate progression semantics

The Thematic Analysis route answers RQ2 over all matched IF/WIF community pairs.
Its progression view consumes only the monthly top-five summaries from the
exact-theme timeline read model. An identical saved label may connect across
adjacent months; a missing month breaks the segment and a later occurrence is
marked as a re-entry. The browser does not merge labels, infer community
continuity, read transition rows, or calculate thematic similarity.

Persisted-community paths, Jaccard continuity, member mobility, and
SentenceTransformer theme-similarity outputs remain part of Community
Evolution (RQ3/RQ4). Their generation and API contracts are unchanged and must
not be presented as aggregate thematic analysis.


## Canonical General-Theme Clustering

Production reporting adds an upstream semantic consolidation stage over saved
matched-community **general** themes. Raw GPT/LDA theme artifacts remain
authoritative evidence and are never overwritten.

### Monthly clustering

- The only clustering label source is `general_theme_names`; missing general
  labels are reported as exclusions and never replaced by IF/WIF labels.
- `general_theme_names` is not a comma-delimited field. Commas inside a generated
  theme label are semantic text and must remain inside that label. Native list/
  tuple values and JSON/Python serialized list values are parsed as structured
  lists; an ordinary scalar string remains one saved label unless the exact
  legacy dot-joined reconstruction rule below applies.
- When the theme generator has serialized multiple saved general labels as its
  dot-joined `general_theme_names` value, the corresponding `general_theme_gpt`
  mapping is consulted against the raw saved scalar before generic list parsing.
  Its keys are used only when `".".join(mapping.keys())` round-trips exactly to
  the saved value after display normalization, retaining each label's mapped LDA
  keyword evidence. `general_theme_gpt` never supplies labels when
  `general_theme_names` is missing.
- Theme list-like evidence is normalized at the shared input boundary; Python
  tuples are treated as ordered sequences rather than one stringified keyword.
- Legacy dot-joined multi-theme values are decomposed only when the companion
  `general_theme_gpt` mapping round-trips exactly. If the value structurally
  matches the historical multi-theme serialization but the mapping is absent or
  inconsistent, the source record is excluded from semantic observations rather
  than admitted as one composite label. The matched-pair denominator is preserved
  and the exclusion is persisted separately as
  `excluded_records_ambiguous_general_theme_serialization`. Legitimate punctuation
  such as `U.S. Immigration Policy` is not blindly split.
- Theme observations are embedded through the clustering TEI profile using
  `sentence-transformers/all-MiniLM-L6-v2`. The clustering client continues to
  request and persist raw/unnormalized float32 embeddings. Production Stage A
  creates an in-memory float64 L2-normalized copy solely for monthly HDBSCAN;
  semantic-medoid and Stage-B representative calculations continue to use the
  recorded raw vectors. The existing similarity TEI client retains its separate
  normalized embedding profile.
- Monthly observations are clustered with scikit-learn's first-party
  `sklearn.cluster.HDBSCAN` over the L2-normalized copy (`min_cluster_size=2`,
  Euclidean distance, `cluster_selection_method="leaf"`,
  `allow_single_cluster=false`, no UMAP).
  `min_samples` is set to `min_cluster_size + 1` because scikit-learn counts the
  point itself whereas the legacy scikit-contrib implementation did not; this
  preserves the prior effective density threshold during the implementation
  migration. Membership probabilities and the exact scikit-learn version are
  persisted as diagnostics/provenance. `prediction_data` is not used because
  this batch pipeline never performs approximate prediction on new points.
- Monthly HDBSCAN noise (`-1`) remains in evidence artifacts but is excluded
  from clustered top-theme rankings.
- Each non-noise monthly cluster receives a stable hash ID and an existing
  source label chosen as the semantic medoid: highest mean pairwise cosine
  similarity, with deterministic tie-breaking.

### Cross-month canonicalization

- Stage B reuses the exact observation embeddings already produced for monthly
  clustering; monthly representative labels are not re-embedded.
- Each non-noise monthly cluster is represented by the existing embedding of its
  deterministic monthly semantic medoid/representative, and that vector is
  L2-normalized. Constituent embeddings are not averaged for production Stage B.
- Normalized monthly representative embeddings are grouped within one run only
  using `sklearn.cluster.AgglomerativeClustering` with cosine distance, complete
  linkage, and similarity threshold `0.65` (distance threshold `0.35`). A size-one
  group is retained as a valid singleton canonical theme; it is not HDBSCAN noise.
- Canonical labels are existing monthly representative labels selected by the same
  deterministic semantic-medoid rule, evaluated over the normalized monthly
  representative vectors; no GPT relabeling or manual standardization is required.
- Canonical IDs, labels, source labels, matched-pair evidence, keywords, model
  metadata, Stage-B representation/grouping/threshold provenance, contract
  versions, and source hashes are persisted in additive artifacts. Canonical-family
  artifacts expose a generic `stage_b_cluster_label`; the legacy
  `stage_b_hdbscan_label` column remains present but is null under this contract.
- The monthly clustering contract is `3.0`. Plan 085 contract `2.2` repaired the
  admitted observation interpretation; Plan 087 then promotes the cross-platform
  Plan-086 `unit_euclidean_leaf_ms3` candidate by L2-normalizing only the in-memory
  Stage-A clustering matrix and switching HDBSCAN selection from EOM to leaf. The
  approved production cross-month canonicalization contract remains `4.0`.

### Stage-A monthly clustering robustness benchmark

- `src/themes/monthly_cluster_benchmark.py` is a read-only diagnostic boundary over
  persisted clean Stage-A evidence and the exact recorded clustering vectors. It never
  calls TEI, OpenAI, translation providers, LDA, network analysis, or the production
  pipeline.
- The benchmark is intentionally frozen to clean contract-`2.2` evidence and first
  reconstructs that historical raw-Euclidean/EOM/`min_samples=3` production partition
  period-by-period. It aborts unless noise membership, non-noise partition, persisted
  probabilities, stable cluster IDs, and representatives match. Contract-`3.0`
  production artifacts are not reinterpreted as the Plan-086 baseline.
- The controlled promotion grid keeps `min_cluster_size=2` fixed and crosses raw
  Euclidean, L2-normalized Euclidean, and cosine geometry with EOM/leaf selection and
  sklearn-inclusive `min_samples` values 3/2. A separate
  `allow_single_cluster=true` production-geometry variant is diagnostic-only.
- Candidate quality is audited with occurrence-preserving cluster/noise/concentration
  metrics plus independent cosine cohesion, semantic-medoid representative-to-member
  cohesion, nearest-neighbour geometry, fragmentation, and full observation membership.
  Exact recorded-vector fingerprints are persisted in benchmark membership output. Within
  one period, observations with an identical recorded embedding must not be assigned to
  more than one non-noise cluster for a candidate to pass the promotion consistency gate;
  noise/non-noise boundary ties are reported separately rather than conflated with this
  failure mode.
- Every candidate is also passed read-only through the fixed production Stage-B
  representative + cosine complete-linkage `0.65` contract so downstream concentration
  and representative-space cohesion are visible without retuning Stage B.
- The benchmark writes four CSVs (summary, periods, clusters, membership), has no
  automatic winner, and cannot by itself alter production defaults. A production Stage-A
  proposal requires manual semantic review and clean cross-platform evidence.

### Stage-B canonicalization benchmark

- `src/themes/canonical_benchmark.py` is a read-only diagnostic boundary over
  persisted monthly-cluster evidence and the exact recorded clustering vectors.
- The benchmark always includes the current representative-label/raw-embedding/
  Euclidean Stage-B contract as a baseline and retains the small Plan-079 set of
  normalized-Euclidean and brute-force cosine candidates.
- Plan 080 adds representation-only candidates that replace each monthly
  representative embedding with the arithmetic mean of all persisted constituent
  general-theme observation embeddings, preserving duplicate observation
  multiplicity. The centroid is evaluated both raw and L2-normalized while the
  existing Euclidean Stage-B density settings remain fixed.
- Plan 081 keeps the L2-normalized constituent centroid fixed and adds
  benchmark-only grouping candidates: HDBSCAN with `min_samples` varied
  independently at 1 and 2, plus cosine-distance agglomerative clustering with
  average and complete linkage at similarity thresholds 0.60, 0.65, 0.70, 0.75,
  and 0.80. Singleton agglomerative groups are reported as benchmark noise so
  family/noise diagnostics remain comparable with the production Stage-B contract.
- Plan 083 keeps cosine complete-linkage grouping fixed and adds a controlled
  representation grid at similarity thresholds 0.60, 0.65, 0.70, 0.75, and 0.80:
  the recorded monthly semantic representative/medoid embedding, the production
  occurrence-weighted constituent mean, the mean of individually L2-normalized
  constituents, the monthly-HDBSCAN membership-probability-weighted mean, and the
  exact-unique-label constituent mean. All vectors are reconstructed from persisted
  evidence and recorded clustering embeddings; no inference is permitted.
- Plan 083 also reports monthly-cluster internal cohesion, representative-to-centroid
  agreement, representative-space within-family cohesion, and observation-weighted
  largest-family concentration. These diagnostics are specifically intended to
  expose false recurrence caused by averaging internally heterogeneous monthly
  clusters into generic centroids.
- The benchmark reports representation, cluster/noise counts, largest-family
  concentration, within-family cosine cohesion, constituent observation/unique-label
  counts, and full monthly-cluster memberships for manual semantic review. It does
  not run TEI or modify canonical artifacts. Plan 082 previously promoted the
  normalized-constituent-centroid + complete-linkage cosine `0.65` candidate as
  contract `3.0`; Plan 083 cross-corpus validation showed representative-space
  drift from centroid averaging, so Plan 084 promotes the recorded monthly semantic
  representative + complete-linkage cosine `0.65` candidate as contract `4.0`. The
  benchmark remains read-only.

### Embedding persistence and reuse

- TEI remains the inference service; it is not treated as an embedding database.
- Embeddings produced by either production semantic profile are persisted as
  immutable run artifacts under `data/themes/embeddings/`: clustering uses
  `clustering_general_themes.parquet`, while Community Evolution similarity
  analysis uses `similarity_themes.parquet`.
- Inference is deduplicated by an exact content-addressed key containing the
  embedding contract version, profile, provider, model ID, pinned model
  revision, normalization flag, preprocessing version, and exact input text.
  Duplicate theme observations are then expanded back before HDBSCAN, so
  occurrence density and therefore the analytical clustering population are
  unchanged.
- Persisted production MiniLM vectors use `float32` and a fixed-size 384-value
  Parquet list. Each profile stores text/vector SHA-256 hashes and full
  model-contract provenance. Exact-text inference is deduplicated within a run;
  callers still receive vectors in their original order and multiplicity.
- No vector database and no Memgraph vector properties are required for this
  batch analytical workload. A future vector index is a separate product
  decision only if interactive nearest-neighbor retrieval becomes a requirement.
- The clustering model and Community Evolution similarity model remain separate
  TEI profiles and pin independent Hugging Face revisions.

### Reporting semantics

- The reporting unit is the distinct normalized
  `(absolute_community, weighted_community)` matched pair.
- A pair contributes at most once to a canonical theme in one month, even when
  multiple source labels from that pair resolve to the same canonical family.
- Prominent LDA keywords are ranked by distinct matched-pair support, then source
  order and lexical tie-breaks.
- Thematic Analysis and Overview -> Top Themes consume the same saved clustered
  monthly artifacts. The dashboard/API never run embeddings or HDBSCAN.
- Exact-label trend endpoints remain available as an audit/compatibility read
  model; they are no longer the primary Top Themes reporting source.

This is thesis-aligned rather than a bit-for-bit reconstruction of the historical
manual standardization step. Historical thesis tables remain reference results,
not golden outputs for future runs.
