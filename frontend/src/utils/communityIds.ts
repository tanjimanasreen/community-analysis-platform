import type { MetricName } from '../types/api';

export interface CommunityIdentifiers {
  ifId: string | null;
  wifId: string | null;
  genericId: string | null;
  startId: string | null;
  endId: string | null;
}

export function normalizeCommunityId(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : null;
  if (typeof value === 'string') {
    const normalized = value.trim();
    return normalized.length > 0 ? normalized : null;
  }
  return null;
}

export function extractCommunityIdentifiers(
  record: Record<string, unknown> | null | undefined,
): CommunityIdentifiers {
  return {
    ifId: normalizeCommunityId(record?.absolute_community),
    wifId: normalizeCommunityId(record?.weighted_community),
    genericId: normalizeCommunityId(record?.community_id ?? record?.community_number),
    startId: normalizeCommunityId(
      record?.start_month_community ?? record?.start_community,
    ),
    endId: normalizeCommunityId(record?.end_month_community ?? record?.end_community),
  };
}

export function communityIdForMetric(
  record: Record<string, unknown> | null | undefined,
  metric: MetricName,
): string | null {
  const identifiers = extractCommunityIdentifiers(record);
  return (
    (metric === 'if' ? identifiers.ifId : identifiers.wifId) ??
    identifiers.genericId ??
    identifiers.startId ??
    identifiers.endId
  );
}

export function communityIdsMatch(
  left: unknown,
  right: unknown,
): boolean {
  const leftId = normalizeCommunityId(left);
  const rightId = normalizeCommunityId(right);
  return leftId !== null && leftId === rightId;
}
