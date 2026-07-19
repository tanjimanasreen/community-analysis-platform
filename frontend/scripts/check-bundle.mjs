import { readdir, stat } from 'node:fs/promises';
import { join } from 'node:path';

const assetsDir = new URL('../dist/assets/', import.meta.url);
const APPLICATION_LIMIT = 500 * 1024;
const INITIAL_LIMIT = 300 * 1024;

const files = await readdir(assetsDir);
const jsFiles = files.filter((name) => name.endsWith('.js'));
if (jsFiles.length === 0) {
  throw new Error('No JavaScript bundles were found. Run npm run build first.');
}

const sizes = await Promise.all(
  jsFiles.map(async (name) => ({ name, size: (await stat(join(assetsDir.pathname, name))).size })),
);

const failures = [];
for (const item of sizes) {
  const routeOrVendorChunk = /(?:vendor|page|graph|chart|network|thematic|evolution|comparative|transitions|reports|methodology)/i.test(item.name);
  if (!routeOrVendorChunk && item.size > APPLICATION_LIMIT) {
    failures.push(`${item.name} is ${item.size} bytes; application chunks must stay under ${APPLICATION_LIMIT}.`);
  }
}

const entry = sizes.find((item) => /^index-/.test(item.name));
if (entry && entry.size > INITIAL_LIMIT) {
  failures.push(`${entry.name} is ${entry.size} bytes; initial entry budget is ${INITIAL_LIMIT}.`);
}

console.table(sizes.sort((a, b) => b.size - a.size));
if (failures.length > 0) {
  throw new Error(`Bundle budget failed:\n${failures.join('\n')}`);
}
