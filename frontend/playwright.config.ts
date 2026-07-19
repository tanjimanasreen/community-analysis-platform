import { defineConfig, devices } from '@playwright/test';

const python = process.env.DASHBOARD_PYTHON ?? '.venv/bin/python';
const fixtureRoot = process.env.DASHBOARD_FIXTURE_ROOT ?? '/tmp/community-dashboard-fixture';
const host = process.env.PLAYWRIGHT_HOST ?? '127.0.0.1';
const chromiumExecutable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: './test-results',
  fullyParallel: false,
  workers: process.env.CI ? 1 : 2,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: `http://${host}:4173`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: chromiumExecutable
          ? { executablePath: chromiumExecutable, args: ['--no-sandbox'] }
          : undefined,
      },
    },
  ],
  webServer: [
    {
      command: `cd .. && ${python} scripts/build_dashboard_fixture.py --out ${fixtureRoot} && COMMUNITY_ANALYSIS_ARTIFACT_ROOT=${fixtureRoot}/default COMMUNITY_ANALYSIS_API_MAX_GRAPH_NODES=200 COMMUNITY_ANALYSIS_API_MAX_GRAPH_EDGES=500 COMMUNITY_ANALYSIS_API_CATALOG_REFRESH_SECONDS=0 ${python} -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000`,
      url: 'http://127.0.0.1:8000/api/v1/health',
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: `npm run dev -- --host ${host} --port 4173`,
      url: `http://${host}:4173`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
  expect: {
    toHaveScreenshot: {
      animations: 'disabled',
      caret: 'hide',
      maxDiffPixelRatio: 0.01,
    },
  },
});
