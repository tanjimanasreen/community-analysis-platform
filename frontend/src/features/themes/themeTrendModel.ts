import type {
  ClusteredThemeItem,
  ClusteredThemeTimelineResponse,
  MonthlyClusteredThemeSummary,
} from '../../types/api';

export type ThemeProgressionStatus = 'new' | 'continued' | 'exited' | 're-entered';

export interface MonthlyTopThemePoint {
  period: string;
  themeId: string;
  name: string;
  rank: number;
  previousRank: number | null;
  rankMovement: number | null;
  communityCount: number;
  percentage: number;
  keywords: string[];
  sourceThemeLabels: string[];
  monthlyRepresentatives: string[];
  statuses: ThemeProgressionStatus[];
}

export interface MonthlyTopThemeGroup {
  period: string;
  totalThemedCommunityPairs: number;
  excludedRecordsMissingGeneralTheme: number;
  excludedRecordsAmbiguousGeneralThemeSerialization: number;
  monthlyNoiseObservationCount: number;
  themes: MonthlyTopThemePoint[];
}

export interface AggregateThemeSeries {
  themeId: string;
  name: string;
  points: MonthlyTopThemePoint[];
  segments: MonthlyTopThemePoint[][];
}

export interface AggregateThemeProgression {
  periods: string[];
  monthly: MonthlyTopThemeGroup[];
  series: AggregateThemeSeries[];
  rows: MonthlyTopThemePoint[];
}

export interface TimelineSummaryMetrics {
  monthsAnalyzed: number;
  themedCommunityMonths: number;
  distinctCanonicalThemes: number;
  mostPrevalentTheme: string | null;
  mostPrevalentThemeCommunityMonths: number;
  monthlyNoiseObservations: number;
}

export function monthlySummaryForPeriod(
  response: ClusteredThemeTimelineResponse | null | undefined,
  period: string | null,
): MonthlyClusteredThemeSummary | null {
  if (!response || !period) return null;
  return response.monthly_summaries.find((summary) => summary.period === period) ?? null;
}

export function topThemes(
  summary: MonthlyClusteredThemeSummary | null | undefined,
  limit = 5,
): ClusteredThemeItem[] {
  if (!summary) return [];
  return summary.themes.slice(0, Math.max(0, limit));
}

export function timelineSummaryMetrics(
  response: ClusteredThemeTimelineResponse | null | undefined,
): TimelineSummaryMetrics {
  if (!response) {
    return {
      monthsAnalyzed: 0,
      themedCommunityMonths: 0,
      distinctCanonicalThemes: 0,
      mostPrevalentTheme: null,
      mostPrevalentThemeCommunityMonths: 0,
      monthlyNoiseObservations: 0,
    };
  }

  return {
    monthsAnalyzed: response.periods.length,
    themedCommunityMonths: response.monthly_summaries.reduce(
      (total, summary) => total + summary.total_themed_community_pairs,
      0,
    ),
    distinctCanonicalThemes: response.distinct_canonical_theme_count,
    mostPrevalentTheme: response.most_discussed_theme?.name ?? null,
    mostPrevalentThemeCommunityMonths:
      response.most_discussed_theme?.total_community_month_count ?? 0,
    monthlyNoiseObservations: response.monthly_noise_observation_count,
  };
}

export function monthlyTopFive(
  response: ClusteredThemeTimelineResponse | null | undefined,
  limit = 5,
): MonthlyTopThemeGroup[] {
  if (!response) return [];
  const summaries = new Map(response.monthly_summaries.map((summary) => [summary.period, summary]));
  const periods = response.periods.length > 0
    ? response.periods
    : [...summaries.keys()].sort();

  return periods.map((period, periodIndex) => {
    const summary = summaries.get(period);
    const previous = periodIndex > 0 ? summaries.get(periods[periodIndex - 1]) : null;
    const previousRanks = new Map(
      topThemes(previous, limit).map((theme, index) => [theme.theme_id, index + 1]),
    );
    const themes = topThemes(summary, limit).map((theme, index) => {
      const rank = index + 1;
      const previousRank = previousRanks.get(theme.theme_id) ?? null;
      return {
        period,
        themeId: theme.theme_id,
        name: theme.name,
        rank,
        previousRank,
        rankMovement: previousRank === null ? null : previousRank - rank,
        communityCount: theme.community_count,
        percentage: theme.percentage,
        keywords: [...theme.keywords],
        sourceThemeLabels: [...theme.source_theme_labels],
        monthlyRepresentatives: [...theme.monthly_representative_themes],
        statuses: [],
      } satisfies MonthlyTopThemePoint;
    });
    return {
      period,
      totalThemedCommunityPairs: summary?.total_themed_community_pairs ?? 0,
      excludedRecordsMissingGeneralTheme: summary?.excluded_records_missing_general_theme ?? 0,
      excludedRecordsAmbiguousGeneralThemeSerialization:
        summary?.excluded_records_ambiguous_general_theme_serialization ?? 0,
      monthlyNoiseObservationCount: summary?.monthly_noise_observation_count ?? 0,
      themes,
    };
  });
}

export function buildAggregateThemeProgression(
  response: ClusteredThemeTimelineResponse | null | undefined,
  limit = 5,
): AggregateThemeProgression {
  const monthly = monthlyTopFive(response, limit);
  const periods = monthly.map((group) => group.period);
  const seen = new Set<string>();

  const enrichedMonthly = monthly.map((group, index) => {
    const previousIds = new Set(monthly[index - 1]?.themes.map((theme) => theme.themeId) ?? []);
    const nextIds = new Set(monthly[index + 1]?.themes.map((theme) => theme.themeId) ?? []);
    const themes = group.themes.map((theme) => {
      const statuses: ThemeProgressionStatus[] = [];
      if (previousIds.has(theme.themeId)) statuses.push('continued');
      else if (seen.has(theme.themeId)) statuses.push('re-entered');
      else statuses.push('new');
      if (!nextIds.has(theme.themeId)) statuses.push('exited');
      return { ...theme, statuses };
    });
    for (const theme of group.themes) seen.add(theme.themeId);
    return { ...group, themes };
  });

  const byId = new Map<string, MonthlyTopThemePoint[]>();
  for (const group of enrichedMonthly) {
    for (const point of group.themes) {
      const points = byId.get(point.themeId) ?? [];
      points.push(point);
      byId.set(point.themeId, points);
    }
  }

  const periodIndex = new Map(periods.map((period, index) => [period, index]));
  const series = [...byId.entries()]
    .map(([themeId, points]) => {
      const sorted = [...points].sort(
        (left, right) => (periodIndex.get(left.period) ?? 0) - (periodIndex.get(right.period) ?? 0),
      );
      const segments: MonthlyTopThemePoint[][] = [];
      for (const point of sorted) {
        const current = segments[segments.length - 1];
        const previous = current?.[current.length - 1];
        const adjacent = previous
          ? (periodIndex.get(point.period) ?? -1) === (periodIndex.get(previous.period) ?? -1) + 1
          : false;
        if (!current || !adjacent) segments.push([point]);
        else current.push(point);
      }
      return { themeId, name: sorted[0]?.name ?? themeId, points: sorted, segments };
    })
    .sort((left, right) => {
      const leftFirst = periodIndex.get(left.points[0]?.period ?? '') ?? Number.MAX_SAFE_INTEGER;
      const rightFirst = periodIndex.get(right.points[0]?.period ?? '') ?? Number.MAX_SAFE_INTEGER;
      return leftFirst - rightFirst
        || (left.points[0]?.rank ?? 99) - (right.points[0]?.rank ?? 99)
        || left.name.localeCompare(right.name)
        || left.themeId.localeCompare(right.themeId);
    });

  const rows = enrichedMonthly.flatMap((group) => group.themes);
  return { periods, monthly: enrichedMonthly, series, rows };
}

export function periodLabel(period: string | null | undefined): string {
  if (!period) return 'Unavailable';
  const match = /^(\d{4})-(\d{2})$/.exec(period);
  if (!match) return period;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, 1));
  return new Intl.DateTimeFormat('en', { month: 'short', year: 'numeric', timeZone: 'UTC' }).format(date);
}
