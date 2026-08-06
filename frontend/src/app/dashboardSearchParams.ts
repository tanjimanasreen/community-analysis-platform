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

export const COMMUNITY_PARAM = 'community';
export const PERIOD_PARAM = 'period';
export const NETWORK_VIEW_PARAM = 'networkView';
export const SAMPLING_PARAM = 'sampling';

export function resolveSamplingStrategy(value: string | null): import('../types/api').SamplingStrategy | null {
  if (value === 'community_balanced' || value === 'strongest_edges' || value === 'full_graph') {
    return value as import('../types/api').SamplingStrategy;
  }
  return null;
}

export function updateDashboardSearchParams(
  current: URLSearchParams,
  update: { 
    runId?: string | null; 
    metric?: MetricName | null;
    period?: string | null;
    communityId?: string | null;
    networkView?: import('../types/api').NetworkView | null;
    sampling?: import('../types/api').SamplingStrategy | null;
  },
): URLSearchParams {
  const next = new URLSearchParams(current);
  if (update.runId !== undefined) {
    if (update.runId) next.set(RUN_PARAM, update.runId);
    else next.delete(RUN_PARAM);
  }
  if (update.metric !== undefined) {
    if (update.metric) next.set(METRIC_PARAM, update.metric);
    else next.delete(METRIC_PARAM);
  }
  if (update.period !== undefined) {
    if (update.period) next.set(PERIOD_PARAM, update.period);
    else next.delete(PERIOD_PARAM);
  }
  if (update.communityId !== undefined) {
    if (update.communityId) next.set(COMMUNITY_PARAM, update.communityId);
    else next.delete(COMMUNITY_PARAM);
  }
  if (update.networkView !== undefined) {
    if (update.networkView) next.set(NETWORK_VIEW_PARAM, update.networkView);
    else next.delete(NETWORK_VIEW_PARAM);
  }
  if (update.sampling !== undefined) {
    if (update.sampling) next.set(SAMPLING_PARAM, update.sampling);
    else next.delete(SAMPLING_PARAM);
  }
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
