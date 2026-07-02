# Tech Debt Tracker

Use this file to track known cleanup and migration work.

| ID | Area | Debt | Impact | Proposed Fix | Status |
|---|---|---|---|---|---|
| TD-001 | Secrets | Neo4j URI and credentials are hard-coded in `neo4j_data_fetcher.py`. | Security risk and not portable. | Move to environment/config. | open |
| TD-002 | Paths | Scripts use hard-coded local paths such as external drive locations. | Pipeline cannot run on another machine. | Move dataset paths to config. | open |
| TD-003 | Script execution | `neo4j_data_fetcher.py` executes export logic at import time. | Unsafe for tests/imports. | Add `main()` guard and CLI wrapper. | open |
| TD-004 | Pandas API | Several modules use deprecated `DataFrame.append`. | Breaks on newer pandas. | Replace with list accumulation and `pd.concat`. | open |
| TD-005 | Typo consistency | Existing function names use `promiment`. | Reduces readability. | Keep compatibility aliases while adding correctly spelled names. | open |
| TD-006 | OpenAI calls | Theme generation calls GPT directly and sleeps inline. | Hard to test and slow/fragile. | Add provider abstraction, caching, retries, and mock provider. | open |
| TD-007 | Model downloads | SentenceTransformer model loads at import time. | Slow imports and brittle tests. | Lazy-load model behind configurable provider. | open |
| TD-008 | spaCy model | `en_core_web_sm` loads at import time. | Import failure if model missing. | Lazy-load and document install command. | open |
| TD-009 | Visualization dependencies | Plotly image export may require Kaleido. | PNG export can fail despite valid analysis. | Make PNG optional and always save HTML. | open |
| TD-010 | Naming | `G_percentage` actually means weighted graph. | Confusing terminology. | Add production alias `weighted_graph` while preserving compatibility. | open |

