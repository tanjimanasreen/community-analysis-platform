import { expect, type Page } from '@playwright/test';

export const PRIMARY_RUN = 'twitter-2017-04';
export const TWITTER_HISTORY_RUN = 'twitter-2017-03';
export const TELEGRAM_RUN = 'telegram-2017-03';
export const MISSING_RUN = 'twitter-2017-05-missing';
export const TAMPERED_RUN = 'twitter-2017-07-tampered';

export function dashboardUrl(path = '/', runId = PRIMARY_RUN, metric = 'if'): string {
  const separator = path.includes('?') ? '&' : '?';
  return `${path}${separator}run=${encodeURIComponent(runId)}&metric=${metric}`;
}

export async function openVerifiedRoute(page: Page, path = '/', runId = PRIMARY_RUN, metric = 'if') {
  await page.goto(dashboardUrl(path, runId, metric));
  await expect(page.getByText('Run verified')).toBeVisible();
  await expect(page.locator(`header span[title="${runId}"]`)).toBeVisible();
}
