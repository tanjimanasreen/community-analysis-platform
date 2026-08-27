# Tech Debt Tracker

Use this file to track known cleanup and migration work.

| ID | Area | Debt | Impact | Proposed Fix | Status |
|---|---|---|---|---|---|
| TD-001 | Secrets | Neo4j URI and credentials are hard-coded in `neo4j_data_fetcher.py`. | Security risk and not portable. | Move to environment/config. | resolved — runtime uses `GRAPH_DB_*` env contract; analytical YAML `database:` blocks are rejected |
| TD-002 | Paths | Scripts use hard-coded local paths such as external drive locations. | Pipeline cannot run on another machine. | Move dataset paths to config. | resolved — all paths are config-driven through `output_base_path`, `input_path`, and related config keys |
| TD-003 | Script execution | `neo4j_data_fetcher.py` executes export logic at import time. | Unsafe for tests/imports. | Add `main()` guard and CLI wrapper. | resolved — production entry point is `src/cli.py` with guarded `main()` functions; legacy scripts are provenance only |
| TD-004 | Pandas API | Several modules use deprecated `DataFrame.append`. | Breaks on newer pandas. | Replace with list accumulation and `pd.concat`. | resolved — production code uses `pd.concat` throughout |
| TD-005 | Typo consistency | Existing function names use `promiment`. | Reduces readability. | Keep compatibility aliases while adding correctly spelled names. | resolved — compatibility aliases exist; production API uses corrected names |
| TD-006 | OpenAI calls | Theme generation calls GPT directly and sleeps inline. | Hard to test and slow/fragile. | Add provider abstraction, caching, retries, and mock provider. | resolved — `src/providers/` abstraction with mock, SQLite cache, typed safety outcomes, and configurable retries |
| TD-007 | Model downloads | SentenceTransformer model loads at import time. | Slow imports and brittle tests. | Lazy-load model behind configurable provider. | resolved — TEI embedding service (`src/themes/tei_client.py`) with lazy health-check and offline test injection |
| TD-008 | spaCy model | `en_core_web_sm` loads at import time. | Import failure if model missing. | Lazy-load and document install command. | resolved — lazy spaCy load with offline blank-English fallback in `src/topics/lda.py` |
| TD-009 | Visualization dependencies | Plotly image export may require Kaleido. | PNG export can fail despite valid analysis. | Make PNG optional and always save HTML. | resolved — PNG is optional (`render_visuals` flag); HTML Sankey is always produced when visualization is enabled |
| TD-010 | Naming | `G_percentage` actually means weighted graph. | Confusing terminology. | Add production alias `weighted_graph` while preserving compatibility. | resolved — `weighted_graph` alias present in production `src/network/graphs.py` |
| TD-011 | Unignored Large Data | The 11 GB `dataset/` and 37 MB `twitter/` output directories were completely untracked and NOT in `.gitignore`. | High risk of accidentally staging/committing 11 GB of raw, potentially sensitive data. | Add `dataset/` and `twitter/` to `.gitignore`. | resolved |
| TD-012 | No Remote DVC Backup | DVC is initialized and tracking 11 GB locally, but `DVC_REMOTE_URL` is unset and no remote is configured. | Total data loss if local disk fails. | Configure an external remote (e.g. S3, local external drive) and `dvc push`. | open |
