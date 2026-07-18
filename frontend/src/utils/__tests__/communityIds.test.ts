import { describe, expect, it } from 'vitest';
import {
  communityIdForMetric,
  communityIdsMatch,
  extractCommunityIdentifiers,
  normalizeCommunityId,
} from '../communityIds';

describe('community identifiers', () => {
  it('normalizes numeric and string IDs without fabricated prefixes', () => {
    expect(normalizeCommunityId(12)).toBe('12');
    expect(normalizeCommunityId(' 009 ')).toBe('009');
    expect(normalizeCommunityId(null)).toBeNull();
    expect(normalizeCommunityId({ id: 1 })).toBeNull();
  });

  it('keeps IF and WIF IDs distinct and selects by metric', () => {
    const record = { absolute_community: 1, weighted_community: '2' };
    expect(extractCommunityIdentifiers(record)).toMatchObject({ ifId: '1', wifId: '2' });
    expect(communityIdForMetric(record, 'if')).toBe('1');
    expect(communityIdForMetric(record, 'wif')).toBe('2');
    expect(communityIdsMatch(1, '1')).toBe(true);
    expect(communityIdsMatch('1', '2')).toBe(false);
  });

  it('handles missing and transition-only records', () => {
    expect(communityIdForMetric({}, 'if')).toBeNull();
    expect(communityIdForMetric({ start_month_community: 4, end_month_community: 5 }, 'wif')).toBe('4');
  });
});
