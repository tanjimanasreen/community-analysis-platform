import type { MetricName, OverviewResponse, RunSummary, TopTheme } from '../../types/api';
import { runSortValue } from '../evolution/runCompatibility';

export interface ComparisonMetricRow {
  key: string;
  label: string;
  left: number | null;
  right: number | null;
  format: 'count' | 'percent';
}

export interface ThemeLabelComparison {
  left: TopTheme[];
  right: TopTheme[];
  sharedNames: string[];
}

export function platformRuns(runs: RunSummary[], platform: 'twitter' | 'telegram'): RunSummary[] {
  return runs
    .filter((run) => {
      if (run.status !== 'completed' || !run.platform) return false;
      const normalized = run.platform.toLowerCase();
      return platform === 'twitter'
        ? normalized === 'twitter' || normalized === 'x' || normalized === 'twitter/x'
        : normalized === 'telegram';
    })
    .sort((left, right) => runSortValue(left).localeCompare(runSortValue(right)));
}

export function comparisonMetricRows(
  left: OverviewResponse,
  right: OverviewResponse,
  metric: MetricName,
): ComparisonMetricRow[] {
  return [
    ['total_users', 'Total users', left.total_users, right.total_users, 'count'],
    ['total_messages', 'Total messages', left.total_messages, right.total_messages, 'count'],
    ['total_interactions', 'Total interactions', left.total_interactions, right.total_interactions, 'count'],
    [
      'community_count',
      `${metric.toUpperCase()} community count`,
      metric === 'if' ? left.if_community_count : left.wif_community_count,
      metric === 'if' ? right.if_community_count : right.wif_community_count,
      'count',
    ],
    [
      'matched_community_count',
      'Matched community count',
      left.matched_community_count,
      right.matched_community_count,
      'count',
    ],
    [
      'matched_percentage',
      'Matched community percentage',
      left.matched_percentage,
      right.matched_percentage,
      'percent',
    ],
    [
      'persistent_community_count',
      'Persistent community count',
      left.persistent_community_count,
      right.persistent_community_count,
      'count',
    ],
  ].map(([key, label, leftValue, rightValue, format]) => ({
    key: String(key),
    label: String(label),
    left: leftValue as number | null,
    right: rightValue as number | null,
    format: format as 'count' | 'percent',
  }));
}

export function compareThemeLabels(
  leftThemes: TopTheme[],
  rightThemes: TopTheme[],
): ThemeLabelComparison {
  const rightByNormalized = new Map(
    rightThemes.map((theme) => [normalizeThemeName(theme.name), theme.name]),
  );
  const sharedNames = leftThemes
    .filter((theme) => rightByNormalized.has(normalizeThemeName(theme.name)))
    .map((theme) => theme.name);
  return { left: leftThemes, right: rightThemes, sharedNames };
}

export function deterministicComparisonFindings(
  rows: ComparisonMetricRow[],
  leftLabel: string,
  rightLabel: string,
): string[] {
  const findings: string[] = [];
  for (const row of rows) {
    if (row.left === null || row.right === null || row.left === row.right) continue;
    const larger = row.left > row.right ? leftLabel : rightLabel;
    const smaller = row.left > row.right ? rightLabel : leftLabel;
    const difference = Math.abs(row.left - row.right);
    findings.push(
      `${larger} is higher than ${smaller} for ${row.label.toLowerCase()} by ${formatMetric(difference, row.format)} (${formatMetric(row.left, row.format)} vs ${formatMetric(row.right, row.format)}).`,
    );
  }
  return findings.slice(0, 4);
}

export function formatMetric(value: number | null, format: 'count' | 'percent'): string {
  if (value === null) return 'Unavailable';
  return format === 'percent'
    ? `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)}%`
    : new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
}

function normalizeThemeName(name: string): string {
  return name.trim().toLocaleLowerCase();
}
