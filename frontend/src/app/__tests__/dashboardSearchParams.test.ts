import { describe, expect, it } from 'vitest';
import type { RunSummary } from '../../types/api';
import {
  deriveRunFacets,
  resolveMetric,
  selectDefaultRunId,
  updateDashboardSearchParams,
} from '../dashboardSearchParams';

const runs: RunSummary[] = [
  {
    run_id: 'running-run',
    status: 'running',
    platform: 'telegram',
    content_type: 'forward',
    date_start: '2019-01-01',
    date_end: '2019-01-31',
    year: 2019,
    month: 1,
    started_at: null,
    completed_at: null,
    artifact_count: 0,
  },
  {
    run_id: 'completed-run',
    status: 'completed',
    platform: 'twitter',
    content_type: 'reply',
    date_start: '2017-03-01',
    date_end: '2017-03-31',
    year: 2017,
    month: 3,
    started_at: null,
    completed_at: null,
    artifact_count: 8,
  },
];

describe('dashboard URL state', () => {
  it('keeps a valid requested run', () => {
    expect(selectDefaultRunId(runs, 'running-run')).toBe('running-run');
  });

  it('falls back to the first completed run in API order', () => {
    expect(selectDefaultRunId(runs, 'missing')).toBe('completed-run');
  });

  it('uses the first run when no completed run exists', () => {
    expect(selectDefaultRunId([runs[0]], null)).toBe('running-run');
  });

  it('normalizes unsupported metrics to IF', () => {
    expect(resolveMetric('wif')).toBe('wif');
    expect(resolveMetric('absolute')).toBe('if');
  });

  it('preserves unrelated search parameters', () => {
    const current = new URLSearchParams('tab=themes&run=old&metric=wif');
    expect(
      updateDashboardSearchParams(current, {
        runId: 'completed-run',
        metric: 'if',
      }).toString(),
    ).toContain('tab=themes');
  });

  it('derives supported facets from the run catalog', () => {
    expect(deriveRunFacets(runs)).toEqual({
      platforms: ['telegram', 'twitter'],
      contentTypes: ['forward', 'reply'],
      years: [2017, 2019],
      months: [1, 3],
    });
  });
});
