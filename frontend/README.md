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

The direct frontend command is still available from this directory:

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
make frontend-lint
make frontend-build
```

Or run the frontend scripts directly:

```bash
npm run lint
npm run build
```

The build is static and does not require the backend API to be running.
