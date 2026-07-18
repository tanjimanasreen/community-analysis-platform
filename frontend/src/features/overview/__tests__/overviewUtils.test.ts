import { describe, expect, it } from 'vitest';
import {
  buildThemeMap,
  communitiesCsv,
  compatibleRuns,
  enrichCommunities,
  metricCommunityCount,
} from '../overviewUtils';
import type { OverviewResponse, RunSummary, ThemeRecord } from '../../../types/api';

const overview = {
  if_community_count: 3,
  wif_community_count: 4,
} as OverviewResponse;

const themeBase = {
  month: '03',
  absolute_community: 1,
  weighted_community: 2,
  absolute_theme_names: ['Policy'],
  weighted_theme_names: ['Civic discourse'],
  general_theme_names: ['General'],
} as ThemeRecord;

describe('overview data mapping', () => {
  it('selects the community count for the active thesis metric', () => {
    expect(metricCommunityCount(overview, 'if')).toBe(3);
    expect(metricCommunityCount(overview, 'wif')).toBe(4);
  });

  it('enriches themes only when the metric/community match is unambiguous', () => {
    expect(buildThemeMap([themeBase], 'if').get('1')).toBe('Policy');
    const ambiguous = {
      ...themeBase,
      absolute_theme_names: ['Another theme'],
    } as ThemeRecord;
    expect(buildThemeMap([themeBase, ambiguous], 'if').has('1')).toBe(false);
  });

  it('exports only canonical visible community fields and the selected metric', () => {
    const rows = enrichCommunities(
      [{ community_id: '1', node_count: 3, edge_count: 2, total_weight: 17 }],
      [themeBase],
      'if',
    );
    const csv = communitiesCsv(rows, 'if');
    expect(csv).toContain('metric,community_id,node_count,edge_count,total_weight,theme');
    expect(csv).toContain('if,1,3,2,17,Policy');
    expect(csv).not.toContain('persistence');
    expect(csv).not.toContain('platform');
  });

  it('keeps only compatible completed runs in chronological order', () => {
    const base = {
      status: 'completed',
      platform: 'twitter',
      content_type: 'reply',
      date_end: null,
      year: null,
      month: null,
      started_at: null,
      completed_at: null,
      artifact_count: 1,
    } satisfies Omit<RunSummary, 'run_id' | 'date_start'>;
    const runs: RunSummary[] = [
      { ...base, run_id: 'march', date_start: '2017-03-01' },
      { ...base, run_id: 'january', date_start: '2017-01-01' },
      { ...base, run_id: 'telegram', platform: 'telegram', date_start: '2017-02-01' },
      { ...base, run_id: 'failed', status: 'failed', date_start: '2017-02-01' },
    ];
    expect(compatibleRuns(runs, runs[0]).map((run) => run.run_id)).toEqual([
      'january',
      'march',
    ]);
  });
});
