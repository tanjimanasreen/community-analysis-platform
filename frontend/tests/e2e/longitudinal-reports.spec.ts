import { expect, test } from '@playwright/test';
import { PRIMARY_RUN, TELEGRAM_RUN, openVerifiedRoute } from './helpers';

test('transition, persistence, and membership records render independently', async ({ page }) => {
  await openVerifiedRoute(page, '/transitions');
  await expect(page.getByRole('heading', { name: 'Transition records' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Persistent community sets' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Membership changes' })).toBeVisible();
  await expect(page.getByText('03 / 1')).toBeVisible();
  await expect(page.getByText('03:1 → 04:1')).toBeVisible();
});

test('cross-platform comparison requires and uses two explicit runs', async ({ page }) => {
  await openVerifiedRoute(page, '/comparative');
  await expect(page.getByRole('heading', { name: 'Select both platform runs' })).toBeVisible();
  await page.getByLabel('Twitter/X run').selectOption(PRIMARY_RUN);
  await page.getByLabel('Telegram run').selectOption(TELEGRAM_RUN);
  await expect(page).toHaveURL(new RegExp(`twitterRun=${PRIMARY_RUN}`));
  await expect(page).toHaveURL(new RegExp(`telegramRun=${TELEGRAM_RUN}`));
  await expect(page.getByRole('heading', { name: 'Supported overview fields' })).toBeVisible();
  await expect(page.getByText(/not message-volume overlap or semantic similarity/i)).toBeVisible();
});

test('report and artifact links use canonical backend URLs and intermediate artifacts are suppressed', async ({ page }) => {
  await openVerifiedRoute(page, '/reports');
  await expect(page.getByRole('link', { name: 'Open report' })).toHaveAttribute(
    'href',
    `/api/v1/runs/${PRIMARY_RUN}/report`,
  );
  const downloads = page.getByRole('link', { name: 'Download' });
  await expect(downloads.first()).toHaveAttribute('href', new RegExp(`/api/v1/runs/${PRIMARY_RUN}/downloads/`));
  await expect(page.getByText('Not downloadable')).toBeVisible();
});
