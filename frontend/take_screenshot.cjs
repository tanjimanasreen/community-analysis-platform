const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Set viewport to a good desktop size
  await page.setViewportSize({ width: 1400, height: 900 });

  console.log("Navigating to frontend...");
  // Go to the dashboard, specific period and network view
  await page.goto('http://localhost:5173/?period=2017-04&networkView=communities', { waitUntil: 'networkidle' });

  // Wait a few seconds for the graph physics to settle and any animations to finish
  console.log("Waiting for graph to render and settle...");
  await page.waitForTimeout(4000);

  const screenshotPath = path.resolve(
    process.env.SCREENSHOT_PATH ||
      path.join(__dirname, '..', 'local_output', 'frontend_screenshot_latest.png'),
  );
  await fs.mkdir(path.dirname(screenshotPath), { recursive: true });
  await page.screenshot({ path: screenshotPath, fullPage: true });

  console.log("Screenshot saved to", screenshotPath);
  await browser.close();
})();
