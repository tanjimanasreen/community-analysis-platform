import { describe, expect, it } from 'vitest';
import fixture from './openapi-routes.fixture.json';
import { API_QUERY_KEYS, API_ROUTES } from '../routes';

const routeQueryNames: Record<string, readonly string[]> = {
  [API_ROUTES.health]: [],
  [API_ROUTES.runs]: API_QUERY_KEYS.runs,
  [API_ROUTES.runDetail]: [],
  [API_ROUTES.artifacts]: [],
  [API_ROUTES.verification]: [],
  [API_ROUTES.overview]: [],
  [API_ROUTES.network]: API_QUERY_KEYS.network,
  [API_ROUTES.centrality]: API_QUERY_KEYS.centrality,
  [API_ROUTES.communities]: API_QUERY_KEYS.communities,
  [API_ROUTES.communityDetail]: API_QUERY_KEYS.communityDetail,
  [API_ROUTES.topics]: API_QUERY_KEYS.topics,
  [API_ROUTES.communityTopics]: API_QUERY_KEYS.communityTopics,
  [API_ROUTES.themes]: API_QUERY_KEYS.themes,
  [API_ROUTES.communityThemes]: API_QUERY_KEYS.communityThemes,
  [API_ROUTES.transitions]: API_QUERY_KEYS.transitions,
  [API_ROUTES.persistentCommunities]: [],
  [API_ROUTES.membershipChanges]: [],
  [API_ROUTES.themeSimilarity]: [],
  [API_ROUTES.report]: [],
  [API_ROUTES.download]: [],
};

describe('dashboard API contract', () => {
  it('covers every route exposed by the checked-in OpenAPI fixture', () => {
    expect(Object.keys(routeQueryNames).sort()).toEqual(Object.keys(fixture).sort());
  });

  it('uses only the backend query parameter names', () => {
    for (const [route, queryNames] of Object.entries(routeQueryNames)) {
      expect([...queryNames].sort(), route).toEqual(
        [...(fixture as Record<string, string[]>)[route]].sort(),
      );
    }
  });

});
