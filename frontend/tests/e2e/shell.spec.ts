import { expect, test } from '@playwright/test';
import {
  PRIMARY_RUN,
  TAMPERED_RUN,
  TWITTER_HISTORY_RUN,
  dashboardUrl,
  openVerifiedRoute,
} from './helpers';

test('application selects a completed run and run switching updates overview provenance', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(new RegExp(`run=${PRIMARY_RUN}`));
  await expect(page.locator('[data-run-id]').first()).toHaveAttribute('data-run-id', PRIMARY_RUN);
  await expect(page.getByRole('heading', { name: 'Total Interactions' })).toBeVisible();

  await page.getByLabel('Analysis run').selectOption(TWITTER_HISTORY_RUN);
  await expect(page).toHaveURL(new RegExp(`run=${TWITTER_HISTORY_RUN}`));
  await expect(page.locator('[data-run-id]').first()).toHaveAttribute('data-run-id', TWITTER_HISTORY_RUN);
  await expect(page.locator(`header span[title="${TWITTER_HISTORY_RUN}"]`)).toBeVisible();
});

test('IF/WIF selection, browser history, and route state remain URL-backed', async ({ page }) => {
  await openVerifiedRoute(page, '/network');
  await page.getByLabel('Affinity metric').selectOption('wif');
  await expect(page).toHaveURL(/metric=wif/);
  await expect(page.getByRole('heading', { name: /Community Network · WIF/ })).toBeVisible();

  await page.getByLabel('Affinity metric').selectOption('if');
  await expect(page).toHaveURL(/metric=if/);
  await page.goBack();
  await expect(page).toHaveURL(/metric=wif/);
  await expect(page.getByRole('heading', { name: /Community Network · WIF/ })).toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL(/metric=if/);
});

test('failed verification blocks analytical content', async ({ page }) => {
  await page.goto(dashboardUrl('/', TAMPERED_RUN));
  await expect(page.getByRole('heading', { name: 'Run verification failed' })).toBeVisible();
  await expect(page.getByText('ARTIFACT_CHECKSUM_MISMATCH')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Total Users' })).toHaveCount(0);
});

test('mobile navigation opens, navigates, and dismisses at 320 CSS pixels', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await openVerifiedRoute(page);
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.getByRole('link', { name: 'Methodology' }).click();
  await expect(page).toHaveURL(/\/methodology\?/);
  await expect(page.getByRole('heading', { name: 'Methodology and run provenance' })).toBeVisible();
  await expect(page.locator('aside[aria-label="Primary navigation"]')).toHaveClass(/-left-80/);
});
