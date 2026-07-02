# Community Analysis Dashboard

This Vite/React app is a read-only dashboard for generated community-analysis
artifacts. It consumes the backend `/api/v1` artifact API and does not run any
pipeline stages.

## Setup

```bash
npm ci
```

If `package-lock.json` is not available, use `npm install`.

## Development

Generate sample artifacts and start the backend API from the project root:

```bash
make run-pipeline-sample
make run-longitudinal-sample
make run-api
```

Then start the dashboard:

```bash
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000` during local development, so
the default dashboard API base is:

```text
VITE_API_BASE_URL=/api/v1
```

Override it in a local `.env` file only when needed.

## Checks

```bash
npm run lint
npm run build
```

The build is static and does not require the backend API to be running.
