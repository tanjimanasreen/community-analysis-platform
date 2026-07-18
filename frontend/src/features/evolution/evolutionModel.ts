import type { MetricName, OverviewResponse, RunSummary } from '../../types/api';
import type { RunOverviewRecord } from './runCompatibility';
import { runSortValue } from './runCompatibility';

export type EvolutionMetricKey =
  | 'total_users'
  | 'total_messages'
  | 'total_interactions'
  | 'community_count'
  | 'matched_percentage'
  | 'persistent_community_count';

export const EVOLUTION_METRICS: Array<{
  key: EvolutionMetricKey;
  label: string;
  unit: 'count' | 'percent';
}> = [
  { key: 'total_users', label: 'Total users', unit: 'count' },
  { key: 'total_messages', label: 'Total messages', unit: 'count' },
  { key: 'total_interactions', label: 'Total interactions', unit: 'count' },
  { key: 'community_count', label: 'Community count', unit: 'count' },
  { key: 'matched_percentage', label: 'Matched communities', unit: 'percent' },
  { key: 'persistent_community_count', label: 'Persistent communities', unit: 'count' },
];

export interface EvolutionPoint {
  runId: string;
  date: string;
  label: string;
  value: number | null;
}

export function evolutionValue(
  overview: OverviewResponse,
  key: EvolutionMetricKey,
  metric: MetricName,
): number | null {
  if (key === 'community_count') {
    return metric === 'if' ? overview.if_community_count : overview.wif_community_count;
  }
  return overview[key];
}

export function buildEvolutionPoints(
  history: RunOverviewRecord[],
  key: EvolutionMetricKey,
  metric: MetricName,
): EvolutionPoint[] {
  return [...history]
    .sort((left, right) => runSortValue(left.run).localeCompare(runSortValue(right.run)))
    .map(({ run, overview }) => ({
      runId: run.run_id,
      date: runSortValue(run),
      label: formatRunDate(run),
      value: evolutionValue(overview, key, metric),
    }));
}

export function trendSummary(
  points: EvolutionPoint[],
  label: string,
): string | null {
  const available = points.filter((point): point is EvolutionPoint & { value: number } => point.value !== null);
  if (available.length < 2) return null;
  const first = available[0];
  const last = available[available.length - 1];
  const difference = last.value - first.value;
  const direction = difference > 0 ? 'increased' : difference < 0 ? 'decreased' : 'did not change';
  const magnitude = Math.abs(difference);
  return `${label} ${direction}${difference === 0 ? '' : ` by ${formatNumber(magnitude)}`} from ${formatNumber(first.value)} on ${first.label} to ${formatNumber(last.value)} on ${last.label}.`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
}

function formatRunDate(run: RunSummary): string {
  const value = runSortValue(run);
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: run.date_start ? 'numeric' : undefined,
    timeZone: 'UTC',
  }).format(parsed);
}
