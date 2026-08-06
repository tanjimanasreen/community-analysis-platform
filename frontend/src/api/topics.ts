import type { ThemesResponse, TopicType, TopicsResponse } from '../types/api';
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
  community_id?: string;
  limit?: number;
  offset?: number;
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
