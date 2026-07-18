import { describe, expect, it } from 'vitest';
import { sortCommunityPage } from '../communityUtils';

describe('community page sorting', () => {
  const rows = [
    { community_id: '10', node_count: 3, edge_count: 2, total_weight: 4 },
    { community_id: '2', node_count: 5, edge_count: 1, total_weight: 9 },
  ];

  it('supports only canonical structural sort fields', () => {
    expect(sortCommunityPage(rows, 'total_weight', 'desc')[0].community_id).toBe('2');
    expect(sortCommunityPage(rows, 'community_id', 'asc').map((row) => row.community_id)).toEqual(['2', '10']);
  });
});
