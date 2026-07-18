import { absoluteApiUrl } from './client';
import { API_ROUTES, fillRoute } from './routes';

export const getReportUrl = (runId: string) =>
  absoluteApiUrl(fillRoute(API_ROUTES.report, { run_id: runId }));

export const getArtifactDownloadUrl = (runId: string, artifactKey: string) =>
  absoluteApiUrl(
    fillRoute(API_ROUTES.download, {
      run_id: runId,
      artifact_key: artifactKey,
    }),
  );
