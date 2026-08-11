import { expect, test } from '@playwright/test';
import { PRIMARY_RUN, TELEGRAM_RUN, openVerifiedRoute } from './helpers';

test('persistent-path structure, mobility, and themes render on one Community Evolution page', async ({ page }) => {
  await openVerifiedRoute(page, '/evolution');
  await expect(page.getByRole('heading', { name: 'Community Similarity over Time' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Member Mobility' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Thematic Similarity' })).toBeVisible();
  await expect(page.getByText('Reappeared').first()).toBeVisible();
  await expect(page.getByText(/paraphrase-MiniLM-L6-v2/i).first()).toBeVisible();
});


test('Community Evolution path selection uses the all-path master view and URL-backed detail context', async ({ page }) => {
  await openVerifiedRoute(page, '/evolution');

  const pathSelector = page.getByLabel('Inspect persistent path');
  await expect(pathSelector).toBeVisible();
  await expect(page.getByRole('button', { name: /Select Path 1/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /Select Path 2/ })).toBeVisible();

  const secondPathValue = await pathSelector.locator('option').nth(1).getAttribute('value');
  expect(secondPathValue).toBeTruthy();
  await pathSelector.selectOption(secondPathValue!);

  await expect(page).toHaveURL(new RegExp(`path=${secondPathValue}`));
  await expect(page.getByRole('button', { name: /Select Path 2/ })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('heading', { name: 'Member Mobility' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Thematic Similarity' })).toBeVisible();
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
  await openVerifiedRoute(page, '/data-reports?view=outputs');
  await expect(page.getByRole('link', { name: 'Open report' })).toHaveAttribute(
    'href',
    `/api/v1/runs/${PRIMARY_RUN}/report`,
  );
  const downloads = page.getByRole('link', { name: 'Download' });
  await expect(downloads.first()).toHaveAttribute('href', new RegExp(`/api/v1/runs/${PRIMARY_RUN}/downloads/`));
  await expect(page.getByText('Not downloadable')).toBeVisible();
});
