import { expect, test } from '@playwright/test';
import { PRIMARY_RUN, openVerifiedRoute } from './helpers';

test('Research Data & Reports is thesis-oriented, period-correct, and scopes affinity only to structural evidence', async ({ page }) => {
  await openVerifiedRoute(page, '/data-reports?view=communities');
  await expect(page).toHaveURL(/view=communities/);
  await expect(page).toHaveURL(/period=/);
  await expect(page.getByRole('button', { name: /Structural · RQ1/ })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: /Semantic · RQ2/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /Temporal · RQ3 \/ RQ4/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /Run Outputs/ })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Communities' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Matched LDA' })).toHaveCount(0);
  await expect(page.getByLabel('Data affinity')).toBeVisible();
  await expect(page.getByLabel('Affinity metric')).toHaveCount(0);

  const navigatorBox = await page.getByLabel('Research data navigation').boundingBox();
  const recordsBox = await page.getByLabel('Analytical records').boundingBox();
  expect(navigatorBox).not.toBeNull();
  expect(recordsBox).not.toBeNull();
  expect(navigatorBox!.y).toBeLessThan(recordsBox!.y);
  expect(Math.abs(navigatorBox!.x - recordsBox!.x)).toBeLessThanOrEqual(2);

  await page.getByRole('button', { name: /Semantic · RQ2/ }).click();
  await expect(page.getByRole('button', { name: 'Matched LDA' })).toBeVisible();
  await page.getByRole('button', { name: 'Matched LDA' }).click();
  await expect(page).toHaveURL(/view=matched-lda/);
  await expect(page.getByLabel('Exact community ID')).toBeVisible();
  await expect(page.getByLabel('Data affinity')).toHaveCount(0);

  await page.getByRole('button', { name: /Temporal · RQ3 \/ RQ4/ }).click();
  await expect(page.getByRole('button', { name: 'Community Transitions' })).toBeVisible();
  await page.getByRole('button', { name: 'Community Transitions' }).click();
  await expect(page).toHaveURL(/view=transitions/);
  await expect(page.getByLabel('Data period')).toHaveCount(0);
});

test('Data & Reports outputs preserve report and manifest download behavior', async ({ page }) => {
  await openVerifiedRoute(page, '/data-reports?view=outputs');
  await expect(page.getByRole('link', { name: 'Open report' })).toHaveAttribute(
    'href',
    `/api/v1/runs/${PRIMARY_RUN}/report`,
  );
  await expect(page.getByText('Published outputs')).toBeVisible();
  await expect(page.getByText('Advanced provenance')).toBeVisible();
  await expect(page.getByText('Not downloadable')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Download' }).first()).toHaveAttribute(
    'href',
    new RegExp(`/api/v1/runs/${PRIMARY_RUN}/downloads/`),
  );
});
