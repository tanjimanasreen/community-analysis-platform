import { expect, test } from '@playwright/test';
import { MISSING_RUN, dashboardUrl, openVerifiedRoute } from './helpers';

test('selected community deep link survives reload and metric changes update graph metadata', async ({ page }) => {
  await openVerifiedRoute(page, '/network?community=1');
  await expect(page).toHaveURL(/community=1/);
  await expect(page.getByRole('heading', { name: '1' })).toBeVisible();
  await expect(page.getByText('Sampled graph')).toBeVisible();

  await page.reload();
  await expect(page).toHaveURL(/community=1/);
  await expect(page.getByRole('heading', { name: '1' })).toBeVisible();

  await page.getByLabel('Affinity metric').selectOption('wif');
  await expect(page.getByText('Weighted Interaction Frequency (WIF)', { exact: true })).toBeVisible();
});

test('matched/partial and unigram/bigram semantic controls are reproducible', async ({ page }) => {
  await openVerifiedRoute(page, '/thematic');
  await page.getByLabel('Topic record type').selectOption('partial');
  await page.getByLabel('Token representation').selectOption('bigram');
  await expect(page).toHaveURL(/topicType=partial/);
  await expect(page).toHaveURL(/token=bigram/);
  await expect(page.getByText('Partially matched communities')).toBeVisible();
  await expect(page.getByText(/Bigram LDA/).first()).toBeVisible();
});

test('missing optional semantic artifacts render an explicit unavailable state', async ({ page }) => {
  await page.goto(dashboardUrl('/thematic?topicType=partial', MISSING_RUN));
  await expect(page.getByText('Run verified')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Artifact not generated' }).first()).toBeVisible();
  await expect(page.getByText(/was not generated|required pipeline stage|not available/i).first()).toBeVisible();
});
