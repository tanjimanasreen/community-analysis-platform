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

test('aggregate matched-community themes and evidence controls are reproducible', async ({ page }) => {
  await openVerifiedRoute(page, '/thematic?topicType=partial&themePath=legacy');
  await expect(page).toHaveURL(/topicType=matched/);
  await expect(page).not.toHaveURL(/themePath=/);
  await expect(page.getByRole('heading', { name: 'Top Themes by Month' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Aggregate Theme Progression' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'How these results are derived' })).toBeVisible();
  await expect(page.getByText('Up to 5 themes per month')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Theme Progression' })).toBeVisible();
  await expect(page.getByText('Jan 2017').first()).toBeVisible();
  await expect(page.getByText('Apr 2017').first()).toBeVisible();
  const progressionScroll = page.getByTestId('aggregate-theme-progression-scroll');
  const overflowState = await progressionScroll.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
    pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }));
  expect(overflowState.scrollWidth).toBeGreaterThanOrEqual(overflowState.clientWidth);
  expect(overflowState.pageOverflow).toBeLessThanOrEqual(2);

  await page.getByRole('button', { name: 'Theme Progression' }).click();
  await expect(page.locator('#thematic-progression')).toBeFocused();

  await expect(page.getByText(/Persistent paths/i)).toHaveCount(0);
  await expect(page.getByText(/Saved theme similarity/i)).toHaveCount(0);

  await page.getByLabel('Token representation').selectOption('bigram');
  await expect(page).toHaveURL(/token=bigram/);
  await expect(page.getByText(/Bigram LDA/).first()).toBeVisible();
});

test('missing optional semantic artifacts render an explicit unavailable state', async ({ page }) => {
  await page.goto(dashboardUrl('/thematic?topicType=matched', MISSING_RUN));
  await expect(page.getByText('Run verified')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Artifact not generated' }).first()).toBeVisible();
  await expect(page.getByText(/was not generated|required pipeline stage|not available/i).first()).toBeVisible();
});
