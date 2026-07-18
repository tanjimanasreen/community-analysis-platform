import type { ArtifactMetadata } from '../../types/api';

export interface ArtifactFilters {
  query: string;
  category: string;
  stage: string;
  mediaType: string;
}

export function filterArtifacts(
  artifacts: ArtifactMetadata[],
  filters: ArtifactFilters,
): ArtifactMetadata[] {
  const query = filters.query.trim().toLowerCase();
  return artifacts.filter((artifact) => {
    if (filters.category && artifact.category !== filters.category) return false;
    if (filters.stage && (artifact.stage ?? '') !== filters.stage) return false;
    if (filters.mediaType && artifact.media_type !== filters.mediaType) return false;
    if (!query) return true;
    return [artifact.key, artifact.path, artifact.category, artifact.media_type, artifact.stage ?? '']
      .some((value) => value.toLowerCase().includes(query));
  });
}

export function artifactFilterOptions(artifacts: ArtifactMetadata[]) {
  return {
    categories: unique(artifacts.map((artifact) => artifact.category)),
    stages: unique(artifacts.map((artifact) => artifact.stage).filter(isString)),
    mediaTypes: unique(artifacts.map((artifact) => artifact.media_type)),
  };
}

export function isDownloadableArtifact(artifact: ArtifactMetadata): boolean {
  return artifact.category !== 'intermediate';
}

export function hasInlineReport(artifacts: ArtifactMetadata[]): boolean {
  return artifacts.some(
    (artifact) =>
      artifact.category === 'report' &&
      artifact.media_type === 'text/html' &&
      (artifact.key === 'report_html' ||
        artifact.key === 'report' ||
        artifact.path.endsWith('report.html')),
  );
}

export function groupArtifactCounts(artifacts: ArtifactMetadata[]): Record<string, number> {
  return artifacts.reduce<Record<string, number>>((counts, artifact) => {
    counts[artifact.category] = (counts[artifact.category] ?? 0) + 1;
    return counts;
  }, {});
}

function unique(values: string[]): string[] {
  return [...new Set(values)].sort((left, right) => left.localeCompare(right));
}

function isString(value: string | null): value is string {
  return typeof value === 'string' && value.length > 0;
}
