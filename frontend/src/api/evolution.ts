import type {
  EvolutionPathsResponse,
  EvolutionThemeType,
  MembershipChangesResponse,
  PathMembershipResponse,
  PathThemeSimilarityResponse,
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


export const getEvolutionPaths = (runId: string, signal?: AbortSignal) =>
  getJson<EvolutionPathsResponse>(
    fillRoute(API_ROUTES.evolutionPaths, { run_id: runId }),
    { signal },
  );

export const getEvolutionPathMobility = (
  runId: string,
  pathId: string,
  signal?: AbortSignal,
) => getJson<PathMembershipResponse>(
  fillRoute(API_ROUTES.evolutionPathMobility, { run_id: runId, path_id: pathId }),
  { signal },
);

export const getEvolutionPathThemeSimilarity = (
  runId: string,
  pathId: string,
  themeType: EvolutionThemeType = 'general',
  signal?: AbortSignal,
) => getJson<PathThemeSimilarityResponse>(
  fillRoute(API_ROUTES.evolutionPathThemeSimilarity, { run_id: runId, path_id: pathId }),
  { params: { theme_type: themeType }, signal },
);
