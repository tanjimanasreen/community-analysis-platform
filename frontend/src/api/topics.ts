import type {
  ClusteredThemeEvidenceResponse,
  ClusteredThemeTimelineResponse,
  MonthlyClusteredThemeResponse,
  MonthlyThemeTrendResponse,
  ThemeTimelineResponse,
  ThemesResponse,
  TopicType,
  TopicsResponse,
} from '../types/api';
import { getJson } from './client';
import { API_ROUTES, fillRoute } from './routes';

export interface TopicParams {
  type?: TopicType;
  community_id?: string;
  period?: string;
  limit?: number;
  offset?: number;
}

export interface ThemeParams {
  month?: string;
  period?: string;
  community_id?: string;
  exact_theme?: string;
  limit?: number;
  offset?: number;
}

export interface MonthlyThemeTrendParams {
  period: string;
  scope?: 'matched';
}

export interface ThemeTimelineParams {
  period_start?: string;
  period_end?: string;
  scope?: 'matched';
}

export const getTopics = (
  runId: string,
  params: TopicParams = {},
  signal?: AbortSignal,
) =>
  getJson<TopicsResponse>(fillRoute(API_ROUTES.topics, { run_id: runId }), {
    params,
    signal,
  });

export const getCommunityTopics = (
  runId: string,
  communityId: string,
  params: Omit<TopicParams, 'community_id'> = {},
  signal?: AbortSignal,
) =>
  getJson<TopicsResponse>(
    fillRoute(API_ROUTES.communityTopics, {
      run_id: runId,
      community_id: communityId,
    }),
    { params, signal },
  );

export const getThemes = (
  runId: string,
  params: ThemeParams = {},
  signal?: AbortSignal,
) =>
  getJson<ThemesResponse>(fillRoute(API_ROUTES.themes, { run_id: runId }), {
    params,
    signal,
  });

export const getCommunityThemes = (
  runId: string,
  communityId: string,
  params: Omit<ThemeParams, 'community_id'> = {},
  signal?: AbortSignal,
) =>
  getJson<ThemesResponse>(
    fillRoute(API_ROUTES.communityThemes, {
      run_id: runId,
      community_id: communityId,
    }),
    { params, signal },
  );

export const getMonthlyThemeTrends = (
  runId: string,
  params: MonthlyThemeTrendParams,
  signal?: AbortSignal,
) =>
  getJson<MonthlyThemeTrendResponse>(
    fillRoute(API_ROUTES.monthlyThemeTrends, { run_id: runId }),
    { params, signal },
  );

export const getThemeTimeline = (
  runId: string,
  params: ThemeTimelineParams = {},
  signal?: AbortSignal,
) =>
  getJson<ThemeTimelineResponse>(
    fillRoute(API_ROUTES.themeTimeline, { run_id: runId }),
    { params, signal },
  );


export interface ClusteredThemeEvidenceParams {
  period: string;
  canonical_theme_id: string;
  limit?: number;
  offset?: number;
}

export const getMonthlyThemeClusters = (
  runId: string,
  params: MonthlyThemeTrendParams,
  signal?: AbortSignal,
) =>
  getJson<MonthlyClusteredThemeResponse>(
    fillRoute(API_ROUTES.monthlyThemeClusters, { run_id: runId }),
    { params, signal },
  );

export const getClusteredThemeTimeline = (
  runId: string,
  params: ThemeTimelineParams = {},
  signal?: AbortSignal,
) =>
  getJson<ClusteredThemeTimelineResponse>(
    fillRoute(API_ROUTES.clusteredThemeTimeline, { run_id: runId }),
    { params, signal },
  );

export const getClusteredThemeEvidence = (
  runId: string,
  params: ClusteredThemeEvidenceParams,
  signal?: AbortSignal,
) =>
  getJson<ClusteredThemeEvidenceResponse>(
    fillRoute(API_ROUTES.clusteredThemeEvidence, { run_id: runId }),
    { params, signal },
  );
