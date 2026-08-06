import type {
  CentralityLeadersResponse,
  CommunitiesResponse,
  CommunityDetail,
  MetricName,
  NetworkResponse,
  NetworkView,
  SamplingStrategy,
  TablePage,
} from '../types/api';
import { getJson } from './client';
import { API_ROUTES, fillRoute } from './routes';

export interface NetworkParams {
  metric?: MetricName;
  period?: string;
  view?: NetworkView;
  sampling?: SamplingStrategy;
  community_id?: string;
  max_nodes?: number;
  max_edges?: number;
  min_weight?: number;
}

export interface PageParams {
  limit?: number;
  offset?: number;
}

export const getNetwork = (
  runId: string,
  params: NetworkParams = {},
  signal?: AbortSignal,
) =>
  getJson<NetworkResponse>(fillRoute(API_ROUTES.network, { run_id: runId }), {
    params,
    signal,
  });

export const getCentrality = (
  runId: string,
  params: PageParams = {},
  signal?: AbortSignal,
) =>
  getJson<TablePage>(fillRoute(API_ROUTES.centrality, { run_id: runId }), {
    params,
    signal,
  });

export const getCentralityLeaders = (
  runId: string,
  params: { metric?: MetricName; period?: string } = {},
  signal?: AbortSignal,
) =>
  getJson<CentralityLeadersResponse>(
    fillRoute(API_ROUTES.centralityLeaders, { run_id: runId }),
    { params, signal },
  );

export const getCommunities = (
  runId: string,
  params: PageParams & { metric?: MetricName; period?: string } = {},
  signal?: AbortSignal,
) =>
  getJson<CommunitiesResponse>(
    fillRoute(API_ROUTES.communities, { run_id: runId }),
    { params, signal },
  );

export const getCommunity = (
  runId: string,
  communityId: string,
  params: Omit<NetworkParams, 'community_id'> = {},
  signal?: AbortSignal,
) =>
  getJson<CommunityDetail>(
    fillRoute(API_ROUTES.communityDetail, {
      run_id: runId,
      community_id: communityId,
    }),
    { params, signal },
  );
