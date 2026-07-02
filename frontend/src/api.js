import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

export const api = {
  getHealth: () => client.get('/health').then((response) => response.data),
  getRuns: () => client.get('/runs').then((response) => response.data),
  getFacets: (runId) => client.get(`/runs/${runId}/facets`).then((response) => response.data),
  getVerification: (runId) => client.get(`/runs/${runId}/verification`).then((response) => response.data),
  getArtifacts: (runId) => client.get(`/runs/${runId}/artifacts`).then((response) => response.data),
  getCommunitySummary: (runId, month) =>
    client.get(`/runs/${runId}/community-summary`, { params: { month } }).then((response) => response.data),
  getCommunities: (runId, { month, matchType, limit, offset }) =>
    client
      .get(`/runs/${runId}/communities`, {
        params: { month, match_type: matchType, limit, offset },
      })
      .then((response) => response.data),
  getTopics: (runId, { month, type, limit, offset }) =>
    client
      .get(`/runs/${runId}/topics`, {
        params: { month, type, limit, offset },
      })
      .then((response) => response.data),
  getThemes: (runId, { month, limit, offset }) =>
    client
      .get(`/runs/${runId}/themes`, {
        params: { month, limit, offset },
      })
      .then((response) => response.data),
  getTransitions: (runId, { limit, offset }) =>
    client
      .get(`/runs/${runId}/transitions`, {
        params: { limit, offset },
      })
      .then((response) => response.data),
  getFiles: (runId) => client.get(`/runs/${runId}/files`).then((response) => response.data),
};

export { API_BASE_URL };
