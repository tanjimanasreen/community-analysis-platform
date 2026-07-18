import { describe, expect, it } from 'vitest';
import type { OverviewResponse, RunSummary } from '../../../types/api';
import { compareThemeLabels, comparisonMetricRows, platformRuns } from '../comparisonModel';

const runs: RunSummary[] = [
  { run_id: 'telegram', status: 'completed', platform: 'telegram', content_type: 'forward', date_start: '2019-01-01', date_end: '2019-01-31', year: 2019, month: 1, started_at: null, completed_at: null, artifact_count: 0 },
  { run_id: 'twitter', status: 'completed', platform: 'twitter', content_type: 'reply', date_start: '2017-01-01', date_end: '2017-01-31', year: 2017, month: 1, started_at: null, completed_at: null, artifact_count: 0 },
];
const overview = (id: string): OverviewResponse => ({ run_id: id, platform: null, content_type: null, date_start: null, date_end: null, total_users: 10, total_messages: 20, total_interactions: 30, if_users: null, wif_users: null, if_messages: null, wif_messages: null, if_community_count: 4, wif_community_count: 5, matched_community_count: 3, matched_percentage: 75, persistent_community_count: null, top_themes: [], model_metadata: {}, config_metadata: {} });

describe('comparison model', () => {
  it('limits selectors to the requested platform and compares supported fields', () => {
    expect(platformRuns(runs, 'twitter').map((run) => run.run_id)).toEqual(['twitter']);
    const rows = comparisonMetricRows(overview('a'), overview('b'), 'wif');
    expect(rows.find((row) => row.key === 'community_count')?.left).toBe(5);
    expect(rows.some((row) => row.key === 'persistence_score')).toBe(false);
  });

  it('labels only exact normalized theme-name overlap', () => {
    const result = compareThemeLabels([{ name: 'Policy', count: 2 }], [{ name: ' policy ', count: 3 }, { name: 'Other', count: 1 }]);
    expect(result.sharedNames).toEqual(['Policy']);
  });
});
