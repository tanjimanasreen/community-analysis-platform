import type { ArtifactMetadata, OverviewResponse, RunDetail, RunSummary } from '../../types/api';

export const THESIS_BASELINE = {
  graph_thresholds: {
    min_total_post: 10,
    min_shared_post: 5,
  },
  louvain: {
    resolution: 1,
    seed: 123,
  },
  lda: {
    num_topics: 15,
    random_state: 100,
    iterations: 100,
    chunksize: 20,
    passes: 80,
    alpha: 'auto',
    eta: 'auto',
  },
  temporal: {
    reply_transition_threshold: 0,
    default_transition_threshold: 0.5,
    similarity_model: 'paraphrase-MiniLM-L6-v2',
  },
} as const;

export interface MethodologyRunView {
  run: Array<[string, unknown]>;
  configuration: Array<[string, unknown]>;
  models: Array<[string, unknown]>;
  artifactCategories: string[];
  metadataAvailable: boolean;
}

export function methodologyRunView(
  run: RunSummary | null,
  detail: RunDetail | null,
  overview: OverviewResponse | null,
  artifacts: ArtifactMetadata[],
): MethodologyRunView {
  const candidates: Array<[string, unknown]> = [
    ['Run ID', run?.run_id],
    ['Status', run?.status],
    ['Platform', run?.platform],
    ['Content type', run?.content_type],
    ['Date start', run?.date_start],
    ['Date end', run?.date_end],
    ['Artifact count', detail?.artifact_count ?? run?.artifact_count],
  ];
  const runEntries = candidates.filter(([, value]) => value !== null && value !== undefined);

  const configuration = flattenSections(overview?.config_metadata ?? {});
  const models = Object.entries(overview?.model_metadata ?? {}).filter(
    ([, value]) => value !== null && value !== undefined && value !== '',
  );
  const artifactCategories = [...new Set(artifacts.map((artifact) => artifact.category))].sort();
  return {
    run: runEntries,
    configuration,
    models,
    artifactCategories,
    metadataAvailable: configuration.length > 0 || models.length > 0,
  };
}

export function flattenSections(metadata: Record<string, unknown>): Array<[string, unknown]> {
  const entries: Array<[string, unknown]> = [];
  for (const [section, value] of Object.entries(metadata)) {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
        entries.push([`${section}.${key}`, item]);
      }
    } else {
      entries.push([section, value]);
    }
  }
  return entries;
}
