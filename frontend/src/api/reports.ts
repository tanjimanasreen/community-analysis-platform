import { absoluteApiUrl, downloadAuthenticatedBlob, openAuthenticatedReport } from './client';
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

export const openRunReport = async (runId: string): Promise<void> => {
  const route = fillRoute(API_ROUTES.report, { run_id: runId });
  await openAuthenticatedReport(route);
};

export const downloadRunArtifact = async (
  runId: string,
  artifactKey: string,
  filename?: string,
): Promise<void> => {
  const route = fillRoute(API_ROUTES.download, {
    run_id: runId,
    artifact_key: artifactKey,
  });
  await downloadAuthenticatedBlob(route, filename);
};
