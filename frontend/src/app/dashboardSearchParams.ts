import type { MetricName, RunSummary } from '../types/api';

export const RUN_PARAM = 'run';
export const METRIC_PARAM = 'metric';
export const DEFAULT_METRIC: MetricName = 'if';

export function isMetricName(value: string | null): value is MetricName {
  return value === 'if' || value === 'wif';
}

export function resolveMetric(value: string | null): MetricName {
  return isMetricName(value) ? value : DEFAULT_METRIC;
}

export function selectDefaultRunId(
  runs: RunSummary[],
  requestedRunId: string | null,
): string {
  if (requestedRunId && runs.some((run) => run.run_id === requestedRunId)) {
    return requestedRunId;
  }
  return (
    runs.find((run) => run.status === 'completed')?.run_id ??
    runs[0]?.run_id ??
    ''
  );
}

export function updateDashboardSearchParams(
  current: URLSearchParams,
  update: { runId?: string; metric?: MetricName },
): URLSearchParams {
  const next = new URLSearchParams(current);
  if (update.runId !== undefined) {
    if (update.runId) next.set(RUN_PARAM, update.runId);
    else next.delete(RUN_PARAM);
  }
  if (update.metric !== undefined) next.set(METRIC_PARAM, update.metric);
  return next;
}

export interface RunFacets {
  platforms: string[];
  contentTypes: string[];
  years: number[];
  months: number[];
}

export function deriveRunFacets(runs: RunSummary[]): RunFacets {
  return {
    platforms: unique(runs.map((run) => run.platform).filter(isString)),
    contentTypes: unique(runs.map((run) => run.content_type).filter(isString)),
    years: unique(runs.map((run) => run.year).filter(isNumber)).sort((a, b) => a - b),
    months: unique(runs.map((run) => run.month).filter(isNumber)).sort((a, b) => a - b),
  };
}

function unique<T>(values: T[]): T[] {
  return [...new Set(values)];
}

function isString(value: string | null): value is string {
  return typeof value === 'string' && value.length > 0;
}

function isNumber(value: number | null): value is number {
  return typeof value === 'number';
}
