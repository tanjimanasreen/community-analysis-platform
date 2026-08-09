import { describe, expect, it } from 'vitest';
import type { ThemeTimelineResponse, TransitionRecord, TransitionsResponse } from '../../../types/api';
import { buildThemeProgressionPaths } from '../themeProgressionModel';

function transition(overrides: Partial<TransitionRecord>): TransitionRecord {
  return {
    start_month: '01',
    end_month: '02',
    start_month_community: 1,
    end_month_community: 2,
    jaccard_score: 0.5,
    common_members: ['u1'],
    uncommon_members: [],
    start_month_members: ['u1', 'u2'],
    total_start_month_members: 2,
    end_month_members: ['u1', 'u3'],
    total_end_month_members: 2,
    start_month_absolute_theme: null,
    end_month_absolute_theme: null,
    start_month_weighted_theme: null,
    end_month_weighted_theme: null,
    start_month_general_theme: 'Policy',
    end_month_general_theme: 'Policy',
    ...overrides,
  };
}

const timeline: ThemeTimelineResponse = {
  run_id: 'run-1',
  scope: 'matched',
  available_periods: ['2017-01', '2017-02', '2017-03', '2017-04'],
  periods: ['2017-01', '2017-02', '2017-03', '2017-04'],
  complete: true,
  source_record_count: 4,
  excluded_records_without_pair: 0,
  monthly_summaries: [
    {
      period: '2017-01', source_record_count: 1, excluded_records_without_pair: 0,
      total_themed_community_pairs: 1, distinct_exact_theme_count: 1,
      themes: [{
        name: 'Policy', community_count: 1, percentage: 100, keywords: ['ban'],
        community_pairs: [{ absolute_community: '1', weighted_community: '11', keywords: ['court'] }],
      }],
    },
    {
      period: '2017-02', source_record_count: 1, excluded_records_without_pair: 0,
      total_themed_community_pairs: 1, distinct_exact_theme_count: 1,
      themes: [{
        name: 'Legal challenge', community_count: 1, percentage: 100, keywords: ['judge'],
        community_pairs: [{ absolute_community: '2', weighted_community: '12', keywords: ['appeal'] }],
      }],
    },
    {
      period: '2017-03', source_record_count: 1, excluded_records_without_pair: 0,
      total_themed_community_pairs: 1, distinct_exact_theme_count: 1,
      themes: [{
        name: 'Activism', community_count: 1, percentage: 100, keywords: ['protest'],
        community_pairs: [{ absolute_community: '3', weighted_community: '13', keywords: ['rally'] }],
      }],
    },
    {
      period: '2017-04', source_record_count: 1, excluded_records_without_pair: 0,
      total_themed_community_pairs: 1, distinct_exact_theme_count: 1,
      themes: [{
        name: 'Institutions', community_count: 1, percentage: 100, keywords: ['court'],
        community_pairs: [{ absolute_community: '4', weighted_community: '14', keywords: ['university'] }],
      }],
    },
  ],
  most_discussed_theme: null,
};

function response(records: TransitionRecord[], total = records.length): TransitionsResponse {
  return { run_id: 'run-1', records, total, limit: 1000, offset: 0 };
}

describe('theme progression model', () => {
  it('builds and ranks canonical four-month paths and joins unambiguous theme evidence', () => {
    const result = buildThemeProgressionPaths(response([
      transition({ start_month_community: 1, end_month_community: 2, common_members: ['u1', 'u2'], jaccard_score: 0.8 }),
      transition({ start_month: '02', end_month: '03', start_month_community: 2, end_month_community: 3, common_members: ['u1'], jaccard_score: 0.7, start_month_general_theme: 'Legal challenge', end_month_general_theme: 'Activism' }),
      transition({ start_month: '03', end_month: '04', start_month_community: 3, end_month_community: 4, common_members: [], jaccard_score: 0.6, start_month_general_theme: 'Activism', end_month_general_theme: 'Institutions' }),
      transition({ start_month_community: 20, end_month_community: 21, common_members: ['x'], jaccard_score: 0.9 }),
    ]), timeline, '2017-01', '2017-04');

    expect(result.complete).toBe(true);
    expect(result.paths[0].distinctMonthCount).toBe(4);
    expect(result.paths[0].nodes.map((node) => node.period)).toEqual(['2017-01', '2017-02', '2017-03', '2017-04']);
    expect(result.paths[0].nodes[0]).toMatchObject({ absoluteCommunityId: '1', weightedCommunityId: '11' });
    expect(result.paths[0].nodes[0].keywords).toEqual(expect.arrayContaining(['court', 'ban']));
    expect(result.paths[0].links[2].retainedCount).toBe(0);
    expect(result.paths[0].totalRetainedMembers).toBe(3);
  });

  it('resolves canonical month names against the selected timeline year', () => {
    const result = buildThemeProgressionPaths(response([
      transition({ start_month: 'January', end_month: 'February' }),
    ]), timeline, null, null);
    expect(result.paths[0].nodes.map((node) => node.period)).toEqual(['2017-01', '2017-02']);
  });

  it('fails closed when transition pagination is incomplete', () => {
    const result = buildThemeProgressionPaths(response([transition({})], 2), timeline, null, null);
    expect(result).toMatchObject({ complete: false, paths: [], returnedRecords: 1, totalRecords: 2 });
  });

  it('does not guess a theme-pair join when one community ID maps to multiple pairs', () => {
    const ambiguousTimeline: ThemeTimelineResponse = {
      ...timeline,
      monthly_summaries: [{
        ...timeline.monthly_summaries[0],
        themes: [
          timeline.monthly_summaries[0].themes[0],
          {
            name: 'Other', community_count: 1, percentage: 100, keywords: ['other'],
            community_pairs: [{ absolute_community: '1', weighted_community: '99', keywords: ['ambiguous'] }],
          },
        ],
      }, ...timeline.monthly_summaries.slice(1)],
    };
    const result = buildThemeProgressionPaths(response([transition({})]), ambiguousTimeline, null, null);
    expect(result.paths[0].nodes[0]).toMatchObject({ absoluteCommunityId: null, weightedCommunityId: null });
    expect(result.paths[0].nodes[0].keywords).toEqual([]);
    expect(result.paths[0].nodes[0].labels).toEqual(['Policy']);
  });

  it('marks retained totals unavailable when any link lacks member evidence', () => {
    const result = buildThemeProgressionPaths(response([
      transition({ common_members: ['u1'] }),
      transition({ start_month: '02', end_month: '03', start_month_community: 2, end_month_community: 3, common_members: null }),
    ]), timeline, null, null);
    expect(result.paths[0].totalRetainedMembers).toBeNull();
  });
});
