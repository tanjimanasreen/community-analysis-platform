import { describe, expect, it } from 'vitest';
import type { OverviewResponse, RunSummary } from '../../../types/api';
import {
  comparisonWarnings,
  completedRunsByPlatformAndContent,
  historyConfigurationWarnings,
} from '../runCompatibility';

const run = (overrides: Partial<RunSummary>): RunSummary => ({
  run_id: 'run', status: 'completed', platform: 'twitter', content_type: 'reply',
  date_start: '2017-03-01', date_end: '2017-03-31', year: 2017, month: 3,
  started_at: null, completed_at: null, artifact_count: 1, ...overrides,
});
const overview = (config: Record<string, unknown>): OverviewResponse => ({
  run_id: 'run', platform: 'twitter', content_type: 'reply', date_start: null, date_end: null,
  total_users: null, total_messages: null, total_interactions: null, if_users: null,
  wif_users: null, if_messages: null, wif_messages: null, if_community_count: null,
  wif_community_count: null, matched_community_count: null, matched_percentage: null,
  persistent_community_count: null, top_themes: [], model_metadata: {}, config_metadata: config,
});

describe('run compatibility', () => {
  it('groups only completed runs and sorts by date', () => {
    const groups = completedRunsByPlatformAndContent([
      run({ run_id: 'late', date_start: '2017-04-01' }),
      run({ run_id: 'failed', status: 'failed' }),
      run({ run_id: 'early', date_start: '2017-02-01' }),
    ]);
    expect(groups.get('twitter::reply')?.map((item) => item.run_id)).toEqual(['early', 'late']);
  });

  it('warns about configuration and cross-platform definition differences', () => {
    const historyWarnings = historyConfigurationWarnings([
      { run: run({ run_id: 'a' }), overview: overview({ louvain: { seed: 123 } }) },
      { run: run({ run_id: 'b' }), overview: overview({ louvain: { seed: 999 } }) },
    ]);
    expect(historyWarnings.map((item) => item.code)).toContain('DIFFERENT_LOUVAIN');

    const warnings = comparisonWarnings({
      leftRun: run({ content_type: 'reply' }),
      rightRun: run({ platform: 'telegram', content_type: 'forward', date_start: '2019-01-01' }),
      leftOverview: overview({ graph_thresholds: { min_total_post: 10 } }),
      rightOverview: overview({ graph_thresholds: { min_total_post: 1 } }),
    });
    expect(warnings.map((item) => item.code)).toEqual(expect.arrayContaining([
      'DIFFERENT_CONTENT_TYPE', 'DIFFERENT_DATE_WINDOW', 'DIFFERENT_GRAPH_THRESHOLDS',
    ]));
  });
});
