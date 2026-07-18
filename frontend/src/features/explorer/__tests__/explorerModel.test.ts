import { describe, expect, it } from 'vitest';
import {
  adaptCentrality,
  filterLoadedPage,
  isArtifactDownloadable,
  navigationCommunityId,
  safeDisplayValue,
} from '../explorerModel';

describe('explorer model', () => {
  it('safely displays arrays, mappings, nulls, and strings', () => {
    expect(safeDisplayValue(null)).toBe('Unavailable');
    expect(safeDisplayValue(['alpha', 'beta'])).toBe('alpha, beta');
    expect(safeDisplayValue({ score: 1 })).toContain('"score": 1');
    expect(safeDisplayValue('plain text')).toBe('plain text');
  });

  it('allowlists centrality columns and filters only the loaded page', () => {
    expect(adaptCentrality([{ month: '03', absolute: { u1: 0.5 }, weighted: { u1: 0.4 }, secret: 'x' }])[0]).toEqual({
      month: '03', absolute: { u1: 0.5 }, weighted: { u1: 0.4 },
    });
    expect(filterLoadedPage([{ community_id: '1' }, { community_id: '2' }], '2')).toHaveLength(1);
  });

  it('uses the selected metric for matched records and blocks intermediate downloads', () => {
    const record = { absolute_community: 1, weighted_community: 2 };
    expect(navigationCommunityId(record, 'if')).toBe('1');
    expect(navigationCommunityId(record, 'wif')).toBe('2');
    expect(isArtifactDownloadable({ key: 'x', category: 'data' })).toBe(true);
    expect(isArtifactDownloadable({ key: 'x', category: 'intermediate' })).toBe(false);
  });
});
