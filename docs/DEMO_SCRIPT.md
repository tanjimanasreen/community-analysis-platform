# Demo Script

This walkthrough is local and offline-safe after dependencies and the browser
binary are installed. It demonstrates the canonical artifact contract,
read-only API, and functional dashboard without calling a database, OpenAI,
TEI, model downloads, or analytical pipeline code during the dashboard demo.

## 1. Install

From a fresh checkout:

```bash
make install-dev
make frontend-install
cd frontend && npx playwright install chromium && cd ..
```

Python dependencies come from `pyproject.toml`; frontend dependencies come from
the checked-in lockfile. No credentials are required for the fixture or tests.

## 2. Build and verify the canonical dashboard fixture

```bash
make dashboard-fixture
python -m pytest -q tests/unit/test_dashboard_fixture.py tests/unit/test_backend_api.py
make frontend-check
```

The default fixture root is `/tmp/community-dashboard-fixture`. It contains:

- completed Twitter/X and Telegram runs;
- two compatible Twitter/X monthly snapshots;
- canonical overview, IF/WIF network, community, centrality, topic, theme,
  transition, membership, similarity, report, and artifact records;
- deliberate no-run, optional-artifact-missing, empty-table, sampled-graph, and
  tampered-checksum variants.

The generator uses canonical manifest models and validation. It does not run the
pipeline or contact external services.

## 3. Start the API and dashboard

Terminal 1:

```bash
make run-api API_ARTIFACT_ROOT=/tmp/community-dashboard-fixture/default
```

Terminal 2:

```bash
make demo-frontend
```

Open the Vite URL printed by the command. The dashboard uses `/api/v1` through
the development proxy and remains read-only.

## 4. Walk through the dashboard

1. **Shell and provenance** — show API health, run verification, the concrete
   analysis-run selector, and IF/WIF metric selector. Reload to demonstrate URL
   persistence.
2. **Overview** — show canonical KPIs, top themes, bounded network preview,
   compatible-run history, community table, deterministic insights, and CSV
   export. Point out the sampled-graph badge on `twitter-2017-04`.
3. **Community Network** — select a node/community, adjust minimum weight, toggle
   labels, and show returned-versus-available graph counts. Degree is explicitly
   labelled as a returned-subgraph presentation value.
4. **Top Communities and Data Explorer** — demonstrate server pagination,
   page-local filtering/sorting labels, real structural fields, semantic links,
   and manifest-key downloads.
5. **Thematic Analysis** — switch matched/partial records, unigram/bigram
   evidence, and IF/WIF/side-by-side views. Explain that LDA keywords are the
   analytical output and provider labels are downstream interpretations.
6. **Evolution and Transitions** — show run-history dates, Jaccard-based
   transitions, persistent communities, membership changes, accessible tables,
   and independent unavailable states.
7. **Comparative Analysis** — explicitly choose one Twitter/X and one Telegram
   run. Review only shared overview fields, exact theme-label overlap, and
   compatibility warnings; there is no fabricated message-overlap Venn.
8. **Reports** — open the verified HTML report and show that intermediate
   artifacts cannot be downloaded.
9. **Methodology** — contrast protected thesis defaults with the selected run's
   resolved configuration and provider/model metadata.

For integrity behavior, select `twitter-2017-07-tampered`: verification blocks
analytical panels and exposes the checksum error. Select
`twitter-2017-05-missing` to show optional semantic/longitudinal artifacts
degrading explicitly rather than falling back to mock data.

## 5. Automated browser proof

```bash
make frontend-e2e
```

The suite starts its own fixture-backed API and Vite servers. It covers run and
metric history, deep links, semantic controls, transitions, comparison, report
URLs, tampered verification, missing optional artifacts, mobile navigation,
axe checks, and browser back/forward state.

Refresh reviewed visual baselines only when the UI change is intentional:

```bash
cd frontend
npm run test:e2e:update
```

## 6. Protected analytical behavior

- `shared_post` remains the raw interaction count.
- `weighted_post` remains `shared_post / total_post`.
- Graph thresholds remain `min_total_post=10` and `min_shared_post=5`.
- Louvain remains `resolution=1`, `seed=123`.
- LDA remains 15 topics, random state 100, 100 iterations, chunksize 20,
  80 passes, and automatic alpha/eta.
- Theme labels remain downstream of saved LDA keywords.

## 7. Cleanup

```bash
make clean-generated
make clean-cache
```

These targets remove known fixture/build/test outputs and caches, but retain
`.venv/` and `frontend/node_modules/`.
