import type { CommunitySummary } from '../../types/api';

export type CommunitySortKey = 'total_weight' | 'node_count' | 'edge_count' | 'community_id';
export type SortDirection = 'asc' | 'desc';

export function sortCommunityPage(
  communities: CommunitySummary[],
  key: CommunitySortKey,
  direction: SortDirection,
): CommunitySummary[] {
  const multiplier = direction === 'asc' ? 1 : -1;
  return [...communities].sort((left, right) => {
    if (key === 'community_id') {
      return left.community_id.localeCompare(right.community_id, undefined, { numeric: true }) * multiplier;
    }
    return (left[key] - right[key]) * multiplier;
  });
}
