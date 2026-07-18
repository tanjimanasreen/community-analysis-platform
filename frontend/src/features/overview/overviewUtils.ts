import Papa from 'papaparse';
import type {
  CommunitySummary,
  MetricName,
  OverviewResponse,
  RunSummary,
  ThemeRecord,
} from '../../types/api';

export interface CommunityRow extends CommunitySummary {
  theme: string | null;
}

export type CommunitySortKey = 'total_weight' | 'node_count' | 'edge_count' | 'community_id';
export type SortDirection = 'asc' | 'desc';

export function formatCount(value: number | string): string {
  const numeric = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(numeric);
}

export function metricCommunityCount(
  overview: OverviewResponse,
  metric: MetricName,
): number | null {
  return metric === 'if' ? overview.if_community_count : overview.wif_community_count;
}

export function buildThemeMap(
  records: ThemeRecord[],
  metric: MetricName,
): Map<string, string> {
  const candidates = new Map<string, Set<string>>();
  for (const record of records) {
    const rawCommunity = metric === 'if' ? record.absolute_community : record.weighted_community;
    if (rawCommunity === null || rawCommunity === undefined) continue;
    const names = metric === 'if' ? record.absolute_theme_names : record.weighted_theme_names;
    const theme = firstString(names) ?? firstString(record.general_theme_names);
    if (!theme) continue;
    const key = String(rawCommunity);
    if (!candidates.has(key)) candidates.set(key, new Set());
    candidates.get(key)?.add(theme);
  }

  const result = new Map<string, string>();
  for (const [communityId, themes] of candidates) {
    if (themes.size === 1) result.set(communityId, [...themes][0]);
  }
  return result;
}

export function enrichCommunities(
  communities: CommunitySummary[],
  themes: ThemeRecord[],
  metric: MetricName,
): CommunityRow[] {
  const themeMap = buildThemeMap(themes, metric);
  return communities.map((community) => ({
    ...community,
    theme: themeMap.get(String(community.community_id)) ?? null,
  }));
}

export function sortCommunities(
  rows: CommunityRow[],
  key: CommunitySortKey,
  direction: SortDirection,
): CommunityRow[] {
  const multiplier = direction === 'asc' ? 1 : -1;
  return [...rows].sort((left, right) => {
    if (key === 'community_id') {
      return left.community_id.localeCompare(right.community_id, undefined, { numeric: true }) * multiplier;
    }
    return (left[key] - right[key]) * multiplier;
  });
}

export function communitiesCsv(rows: CommunityRow[], metric: MetricName): string {
  return Papa.unparse(
    rows.map((row) => ({
      metric,
      community_id: row.community_id,
      node_count: row.node_count,
      edge_count: row.edge_count,
      total_weight: row.total_weight,
      theme: row.theme ?? '',
    })),
  );
}

export function compatibleRuns(runs: RunSummary[], selected: RunSummary | null): RunSummary[] {
  if (!selected) return [];
  return runs
    .filter(
      (run) =>
        run.status === 'completed' &&
        run.platform === selected.platform &&
        run.content_type === selected.content_type,
    )
    .sort((left, right) => runDate(left).localeCompare(runDate(right)))
    .slice(-12);
}

export function runDate(run: RunSummary): string {
  if (run.date_start) return run.date_start;
  if (run.year && run.month) return `${run.year}-${String(run.month).padStart(2, '0')}-01`;
  return run.completed_at ?? run.started_at ?? run.run_id;
}

export function conciseRunId(runId: string): string {
  return runId.length > 12 ? `${runId.slice(0, 8)}…${runId.slice(-3)}` : runId;
}

export function metadataValue(
  metadata: Record<string, unknown> | null | undefined,
  keys: string[],
): string | null {
  if (!metadata) return null;
  for (const key of keys) {
    const value = metadata[key];
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      return String(value);
    }
  }
  return null;
}

function firstString(value: unknown): string | null {
  if (typeof value === 'string') return value.trim() || null;
  if (Array.isArray(value)) {
    const first = value.find((item) => typeof item === 'string' && item.trim());
    return typeof first === 'string' ? first : null;
  }
  return null;
}
