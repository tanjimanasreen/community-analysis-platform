import { describe, expect, it } from 'vitest';
import { clampPageOffset, nextPageOffset, pageRange, previousPageOffset } from '../pagination';

describe('pagination utilities', () => {
  it('keeps offsets within stable server pages', () => {
    expect(clampPageOffset(100, 42, 10)).toBe(40);
    expect(previousPageOffset(20, 10)).toBe(10);
    expect(nextPageOffset(30, 42, 10)).toBe(40);
    expect(pageRange(40, 10, 42)).toBe('41–42 of 42');
    expect(pageRange(0, 10, 0)).toBe('0 records');
  });
});
