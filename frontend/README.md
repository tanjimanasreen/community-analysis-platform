# Community Analysis Dashboard

This Vite/React app is a read-only dashboard for generated community-analysis
artifacts. It consumes the backend `/api/v1` artifact API and does not run any
pipeline stages.

## Setup

From the project root:

```bash
make frontend-install
```

This uses `npm ci` against the checked-in `package-lock.json`.

## Development

Generate sample artifacts and start the backend API from the project root:

```bash
make demo
make demo-api
```

Then start the dashboard:

```bash
make demo-frontend
```

The direct frontend command is:

```bash
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000` during local development. The
client defaults to:

```text
VITE_API_BASE_URL=/api/v1
```

Override it in a local `.env` file only when needed. Do not commit secrets or
machine-specific absolute paths.

## State and API ownership

Global dashboard state is limited to the selected canonical run and affinity
metric (`if` or `wif`). Both are stored in the URL as `run` and `metric` search
parameters and are managed by `DashboardProvider`.

Page-specific filters and API queries belong inside their feature/page. The
application shell must not prefetch community, topic, theme, or evolution data
for every route.

The typed API boundary lives under `src/api/` and mirrors the backend Pydantic
schemas in `src/types/api.ts`. The frontend does not use legacy `/facets`,
`/community-summary`, or `/files` routes.

## Checks

From the frontend directory:

```bash
npm run typecheck
npm run lint
npm run test -- --run
npm run build
npm run check
```

Equivalent Make targets are available:

```bash
make frontend-typecheck
make frontend-lint
make frontend-test
make frontend-build
make frontend-check
```

Unit tests run without a backend or internet connection. The build is static
and does not require the API to be running.

Playwright is installed for later end-to-end coverage. Run its current suite
with:

```bash
npm run test:e2e
```
