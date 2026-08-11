import { expect, test } from '@playwright/test';
import { MISSING_RUN, dashboardUrl, openVerifiedRoute } from './helpers';

test('selected monthly community deep link survives reload and partition changes clear month-local identity', async ({ page }) => {
  await openVerifiedRoute(page, '/communities?community=1');
  await expect(page).toHaveURL(/period=/);
  await expect(page).toHaveURL(/community=1/);
  await expect(page.getByRole('heading', { name: 'C1' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Member Interaction Network' })).toBeVisible();

  await page.reload();
  await expect(page).toHaveURL(/community=1/);
  await expect(page.getByRole('heading', { name: 'C1' })).toBeVisible();

  await page.getByLabel('Affinity metric').selectOption('wif');
  await expect(page).toHaveURL(/metric=wif/);
  await expect(page).not.toHaveURL(/community=1/);
  await expect(page.getByRole('heading', { name: 'Select a community' })).toBeVisible();
});

test('legacy community routes redirect to the unified workspace with query state preserved', async ({ page }) => {
  await openVerifiedRoute(page, '/network?community=1&minWeight=2');
  await expect(page).toHaveURL(/\/communities\?/);
  await expect(page).toHaveURL(/community=1/);
  await expect(page).toHaveURL(/minWeight=2/);

  await openVerifiedRoute(page, '/top-communities?community=1');
  await expect(page).toHaveURL(/\/communities\?/);
  await expect(page).toHaveURL(/community=1/);
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
  await expect(page.getByRole('heading', { name: 'Selected Canonical Theme · Cluster Evidence' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Source Evidence Explorer' })).toBeVisible();
  const evidenceOrder = await page.evaluate(() => {
    const canonical = document.getElementById('thematic-canonical-evidence');
    const explorer = document.getElementById('thematic-evidence-explorer');
    return canonical && explorer
      ? canonical.compareDocumentPosition(explorer) & Node.DOCUMENT_POSITION_FOLLOWING
      : 0;
  });
  expect(evidenceOrder).toBeTruthy();

  const rail = page.locator('aside[aria-label="Page section navigation"]');
  const main = page.locator('#main-content');
  const [railBox, mainBox] = await Promise.all([rail.boundingBox(), main.boundingBox()]);
  expect(railBox).not.toBeNull();
  expect(mainBox).not.toBeNull();
  if (railBox && mainBox) {
    expect(railBox.y).toBeGreaterThanOrEqual(mainBox.y);
    expect(railBox.y + railBox.height).toBeLessThanOrEqual(mainBox.y + mainBox.height + 2);
  }

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
