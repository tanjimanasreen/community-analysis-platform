import type {
  MembershipChangesResponse,
  PersistentCommunitiesResponse,
  ThemeSimilarityResponse,
  TransitionsResponse,
} from '../types/api';
import { getJson } from './client';
import { API_ROUTES, fillRoute } from './routes';

export interface TransitionParams {
  limit?: number;
  offset?: number;
}

export const getTransitions = (
  runId: string,
  params: TransitionParams = {},
  signal?: AbortSignal,
) =>
  getJson<TransitionsResponse>(fillRoute(API_ROUTES.transitions, { run_id: runId }), {
    params,
    signal,
  });

export const getPersistentCommunities = (runId: string, signal?: AbortSignal) =>
  getJson<PersistentCommunitiesResponse>(
    fillRoute(API_ROUTES.persistentCommunities, { run_id: runId }),
    { signal },
  );

export const getMembershipChanges = (runId: string, signal?: AbortSignal) =>
  getJson<MembershipChangesResponse>(
    fillRoute(API_ROUTES.membershipChanges, { run_id: runId }),
    { signal },
  );

export const getThemeSimilarity = (runId: string, signal?: AbortSignal) =>
  getJson<ThemeSimilarityResponse>(
    fillRoute(API_ROUTES.themeSimilarity, { run_id: runId }),
    { signal },
  );
