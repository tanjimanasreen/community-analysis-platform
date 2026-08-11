import { existsSync } from 'node:fs';
import { expect, test } from '@playwright/test';
import { TELEGRAM_RUN, openVerifiedRoute } from './helpers';

const routes = [
  ['overview', '/'],
  ['communities', '/communities?community=1'],
  ['thematic', '/thematic'],
  ['evolution', '/evolution'],
  ['comparison', `/comparative?twitterRun=twitter-2017-04&telegramRun=${TELEGRAM_RUN}`],
  ['data-reports', '/data-reports?view=communities'],
  ['data-reports-outputs', '/data-reports?view=outputs'],
  ['methodology', '/methodology'],
] as const;

for (const [name, route] of routes) {
  test(`visual baseline: ${name}`, async ({ page }) => {
    const snapshotPath = test.info().snapshotPath(`${name}.png`);
    const updatingSnapshots = test.info().config.updateSnapshots !== 'none';
    test.skip(!existsSync(snapshotPath) && !updatingSnapshots, 'Generate visual baselines with npm run test:e2e:update.');

    await page.setViewportSize({ width: 1280, height: 800 });
    await openVerifiedRoute(page, route);
    await expect(page.locator('main')).toHaveScreenshot(`${name}.png`, {
      mask: [page.locator('canvas')],
    });
  });
}
