import { describe, expect, it } from 'vitest';
import type { OverviewResponse, RunSummary } from '../../../types/api';
import { buildEvolutionPoints, trendSummary } from '../evolutionModel';

function run(id: string, date: string): RunSummary {
  return { run_id: id, status: 'completed', platform: 'twitter', content_type: 'reply', date_start: date, date_end: date, year: null, month: null, started_at: null, completed_at: null, artifact_count: 0 };
}
function overview(id: string, users: number | null): OverviewResponse {
  return { run_id: id, platform: 'twitter', content_type: 'reply', date_start: null, date_end: null, total_users: users, total_messages: null, total_interactions: null, if_users: null, wif_users: null, if_messages: null, wif_messages: null, if_community_count: null, wif_community_count: null, matched_community_count: null, matched_percentage: null, persistent_community_count: null, available_periods: [], periods: [], run_summary: { interaction_records: null, persistent_community_count: null, month_count: 0 }, top_themes: [], model_metadata: {}, config_metadata: {} };
}

describe('evolution model', () => {
  it('preserves missing values and excludes them from endpoint trend arithmetic', () => {
    const points = buildEvolutionPoints([
      { run: run('b', '2017-04-01'), overview: overview('b', 20) },
      { run: run('a', '2017-03-01'), overview: overview('a', null) },
      { run: run('c', '2017-05-01'), overview: overview('c', 25) },
    ], 'total_users', 'if');
    expect(points.map((point) => point.value)).toEqual([null, 20, 25]);
    expect(trendSummary(points, 'Total users')).toContain('increased by 5');
  });
});
