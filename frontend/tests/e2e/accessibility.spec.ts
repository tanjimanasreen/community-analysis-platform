import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { TELEGRAM_RUN, openVerifiedRoute } from './helpers';

const representativeRoutes = [
  '/',
  '/network?community=1',
  '/thematic',
  '/evolution',
  `/comparative?twitterRun=twitter-2017-04&telegramRun=${TELEGRAM_RUN}`,
  '/reports',
  '/methodology',
];

for (const route of representativeRoutes) {
  test(`has no serious or critical axe violations on ${route}`, async ({ page }) => {
    await openVerifiedRoute(page, route);
    const results = await new AxeBuilder({ page }).analyze();
    const blocking = results.violations.filter((item) => ['serious', 'critical'].includes(item.impact ?? ''));
    expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
  });
}

test('keyboard controls remain usable at 200% zoom and 320 CSS pixels', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await openVerifiedRoute(page);
  await page.evaluate(() => { document.body.style.zoom = '2'; });
  await page.getByLabel('Analysis run').focus();
  await page.keyboard.press('End');
  await page.keyboard.press('Enter');
  await expect(page.getByLabel('Analysis run')).toBeFocused();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(2);
});


test('methodology network tabs support keyboard selection', async ({ page }) => {
  await openVerifiedRoute(page, '/methodology');
  const telegramTab = page.getByRole('tab', { name: 'Telegram' });
  await telegramTab.focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Twitter · Retweet/Quote' })).toHaveAttribute('aria-selected', 'true');
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Twitter · Reply' })).toHaveAttribute('aria-selected', 'true');
});
