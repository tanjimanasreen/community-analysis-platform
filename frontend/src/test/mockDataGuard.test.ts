import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const SOURCE_ROOT = resolve(process.cwd(), 'src');
const FORBIDDEN = [
  /C-1124/i,
  /May\s+'?24/i,
  /\bReddit\b/i,
  /\bFacebook\b/i,
  /\bDiscord\b/i,
  /Math\.random/,
  /\/facets\b/,
  /\/community-summary\b/,
  /\/files\b/,
];

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    const metadata = statSync(path);
    if (metadata.isDirectory()) {
      if (name === '__tests__' || name === 'test') return [];
      return sourceFiles(path);
    }
    return /\.(?:js|jsx|ts|tsx)$/.test(name) ? [path] : [];
  });
}

describe('analytical source guard', () => {
  it('contains no obsolete API paths or known analytical mock values', () => {
    const failures: string[] = [];
    for (const path of sourceFiles(SOURCE_ROOT)) {
      const text = readFileSync(path, 'utf8');
      for (const pattern of FORBIDDEN) {
        if (pattern.test(text)) {
          failures.push(`${relative(SOURCE_ROOT, path)} matched ${pattern}`);
        }
      }
    }
    expect(failures).toEqual([]);
  });
});
