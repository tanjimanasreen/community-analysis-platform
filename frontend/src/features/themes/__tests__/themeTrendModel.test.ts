import { describe, expect, it } from 'vitest';
import type { ClusteredThemeTimelineResponse, MonthlyClusteredThemeSummary } from '../../../types/api';
import {
  buildAggregateThemeProgression,
  monthlySummaryForPeriod,
  monthlyTopFive,
  periodLabel,
  timelineSummaryMetrics,
  topThemes,
} from '../themeTrendModel';

function summary(
  period: string,
  themes: Array<{ id: string; name: string; count: number; keywords?: string[] }>,
  denominator = 4,
): MonthlyClusteredThemeSummary {
  return {
    period,
    source_observation_count: denominator,
    excluded_records_missing_general_theme: 0,
    excluded_records_ambiguous_general_theme_serialization: 0,
    monthly_noise_observation_count: 1,
    total_themed_community_pairs: denominator,
    distinct_clustered_theme_count: themes.length,
    themes: themes.map((theme) => ({
      theme_id: theme.id,
      name: theme.name,
      community_count: theme.count,
      percentage: denominator > 0 ? (theme.count * 100) / denominator : 0,
      keywords: theme.keywords ?? [],
      monthly_cluster_ids: [],
      monthly_representative_themes: [theme.name],
      source_theme_labels: [theme.name],
      community_pairs: [],
      mean_membership_probability: 0.9,
    })),
    embedding_provider: 'tei',
    embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
    monthly_cluster_contract_version: '1.0',
    canonicalization_contract_version: '1.0',
  };
}

function timeline(monthly: MonthlyClusteredThemeSummary[]): ClusteredThemeTimelineResponse {
  return {
    run_id: 'run-1',
    scope: 'matched',
    available_periods: monthly.map((item) => item.period),
    periods: monthly.map((item) => item.period),
    complete: true,
    source_observation_count: monthly.reduce((total, item) => total + item.source_observation_count, 0),
    excluded_records_missing_general_theme: 0,
    excluded_records_ambiguous_general_theme_serialization: 0,
    monthly_noise_observation_count: monthly.reduce((total, item) => total + item.monthly_noise_observation_count, 0),
    distinct_canonical_theme_count: 3,
    monthly_summaries: monthly,
    most_discussed_theme: {
      theme_id: 'ct_policy',
      name: 'US Immigration Policy',
      total_community_month_count: 7,
      months_present: 3,
      peak_period: monthly[0]?.period ?? '2017-01',
      peak_month_count: 3,
      series: [],
      keywords: ['court'],
    },
  };
}

const response = timeline([
  summary('2016-12', [
    { id: 'ct_policy', name: 'US Immigration Policy', count: 3, keywords: ['court'] },
    { id: 'ct_culture', name: 'Culture', count: 1 },
  ]),
  summary('2017-01', [
    { id: 'ct_policy', name: 'US Immigration Policy', count: 2, keywords: ['ban'] },
    { id: 'ct_activism', name: 'Activism', count: 2, keywords: ['protest'] },
    { id: 'ct_culture', name: 'Culture', count: 1 },
  ]),
  summary('2017-02', [
    { id: 'ct_activism', name: 'Activism', count: 3, keywords: ['rally'] },
    { id: 'ct_culture', name: 'Culture', count: 1 },
  ]),
  summary('2017-03', [
    { id: 'ct_policy', name: 'Immigration Policy', count: 2, keywords: ['judge'] },
    { id: 'ct_activism', name: 'Activism', count: 1, keywords: ['rights'] },
  ]),
]);

describe('clustered theme trend models', () => {
  it('selects monthly summaries and formats year boundaries', () => {
    const selected = monthlySummaryForPeriod(response, '2017-01');
    expect(selected?.period).toBe('2017-01');
    expect(topThemes(selected, 2).map((theme) => theme.name)).toEqual(['US Immigration Policy', 'Activism']);
    expect(periodLabel('2016-12')).toBe('Dec 2016');
    expect(periodLabel('2017-01')).toBe('Jan 2017');
  });

  it('uses canonical theme counts from the upstream API', () => {
    expect(timelineSummaryMetrics(response)).toEqual({
      monthsAnalyzed: 4,
      themedCommunityMonths: 16,
      distinctCanonicalThemes: 3,
      mostPrevalentTheme: 'US Immigration Policy',
      mostPrevalentThemeCommunityMonths: 7,
      monthlyNoiseObservations: 4,
    });
  });

  it('computes previous-month rank using canonical theme identity', () => {
    const monthly = monthlyTopFive(response);
    expect(monthly[1].themes[0]).toMatchObject({ themeId: 'ct_policy', previousRank: 1, rankMovement: 0 });
    expect(monthly[2].themes[0]).toMatchObject({ themeId: 'ct_activism', previousRank: 2, rankMovement: 1 });
  });

  it('connects canonical identities across adjacent months and breaks on gaps', () => {
    const progression = buildAggregateThemeProgression(response);
    const policy = progression.series.find((series) => series.themeId === 'ct_policy');
    expect(policy?.segments.map((segment) => segment.map((point) => point.period))).toEqual([
      ['2016-12', '2017-01'],
      ['2017-03'],
    ]);
    const reEntry = progression.rows.find((point) => point.themeId === 'ct_policy' && point.period === '2017-03');
    expect(reEntry?.statuses).toEqual(['re-entered', 'exited']);
  });

  it('does not depend on display-label equality for canonical progression', () => {
    const progression = buildAggregateThemeProgression(response);
    const policy = progression.series.find((series) => series.themeId === 'ct_policy');
    expect(policy?.points.map((point) => point.name)).toEqual([
      'US Immigration Policy',
      'US Immigration Policy',
      'Immigration Policy',
    ]);
  });

  it('returns safe empty models', () => {
    expect(monthlyTopFive(null)).toEqual([]);
    expect(buildAggregateThemeProgression(undefined)).toEqual({ periods: [], monthly: [], series: [], rows: [] });
    expect(timelineSummaryMetrics(null).monthsAnalyzed).toBe(0);
  });
});
