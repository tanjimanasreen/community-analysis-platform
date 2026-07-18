import type { ArtifactMetadata, OverviewResponse, RunSummary } from '../../types/api';

export interface CompatibilityWarning {
  code: string;
  message: string;
}

export interface RunOverviewRecord {
  run: RunSummary;
  overview: OverviewResponse;
}

export function completedRunsByPlatformAndContent(
  runs: RunSummary[],
): Map<string, RunSummary[]> {
  const groups = new Map<string, RunSummary[]>();
  for (const run of runs) {
    if (run.status !== 'completed' || !run.platform || !run.content_type) continue;
    const key = `${run.platform.toLowerCase()}::${run.content_type.toLowerCase()}`;
    const values = groups.get(key) ?? [];
    values.push(run);
    groups.set(key, values);
  }
  for (const values of groups.values()) {
    values.sort((left, right) => runSortValue(left).localeCompare(runSortValue(right)));
  }
  return groups;
}

export function compatibleCompletedRuns(
  runs: RunSummary[],
  selectedRun: RunSummary | null,
  limit = 12,
): RunSummary[] {
  if (!selectedRun?.platform || !selectedRun.content_type) return [];
  const key = `${selectedRun.platform.toLowerCase()}::${selectedRun.content_type.toLowerCase()}`;
  const group = completedRunsByPlatformAndContent(runs).get(key) ?? [];
  return group.slice(-Math.max(2, limit));
}

export function runSortValue(run: RunSummary): string {
  return (
    run.date_start ??
    (run.year && run.month
      ? `${run.year}-${String(run.month).padStart(2, '0')}-01`
      : null) ??
    run.completed_at ??
    run.started_at ??
    run.run_id
  );
}

export function historyConfigurationWarnings(history: RunOverviewRecord[]): CompatibilityWarning[] {
  if (history.length < 2) return [];
  const warnings: CompatibilityWarning[] = [];
  const sections = ['graph_thresholds', 'louvain', 'lda'];
  for (const section of sections) {
    const values = new Set(
      history.map(({ overview }) => stableSerialize(overview.config_metadata?.[section])),
    );
    if (values.size > 1) {
      warnings.push({
        code: `DIFFERENT_${section.toUpperCase()}`,
        message: `Compatible runs use different ${section.replace('_', ' ')} settings. Values are shown as separate run results and should not be interpreted as one controlled series.`,
      });
    }
  }
  return warnings;
}

export function comparisonWarnings({
  leftRun,
  rightRun,
  leftOverview,
  rightOverview,
  leftArtifacts = [],
  rightArtifacts = [],
}: {
  leftRun: RunSummary;
  rightRun: RunSummary;
  leftOverview: OverviewResponse;
  rightOverview: OverviewResponse;
  leftArtifacts?: ArtifactMetadata[];
  rightArtifacts?: ArtifactMetadata[];
}): CompatibilityWarning[] {
  const warnings: CompatibilityWarning[] = [];
  if (leftRun.content_type !== rightRun.content_type) {
    warnings.push({
      code: 'DIFFERENT_CONTENT_TYPE',
      message: `Content types differ (${leftRun.content_type ?? 'unavailable'} vs ${rightRun.content_type ?? 'unavailable'}). Structural values remain visible, but they do not represent identical interaction definitions.`,
    });
  }
  if (dateWindow(leftRun) !== dateWindow(rightRun)) {
    warnings.push({
      code: 'DIFFERENT_DATE_WINDOW',
      message: `Date windows differ (${dateWindow(leftRun)} vs ${dateWindow(rightRun)}). The comparison is descriptive only.`,
    });
  }
  for (const section of ['graph_thresholds', 'louvain', 'lda']) {
    if (
      stableSerialize(leftOverview.config_metadata?.[section]) !==
      stableSerialize(rightOverview.config_metadata?.[section])
    ) {
      warnings.push({
        code: `DIFFERENT_${section.toUpperCase()}`,
        message: `${section.replace('_', ' ')} settings differ between the selected runs.`,
      });
    }
  }
  if (stableSerialize(leftOverview.model_metadata) !== stableSerialize(rightOverview.model_metadata)) {
    warnings.push({
      code: 'DIFFERENT_MODEL_METADATA',
      message: 'Theme provider or similarity-model metadata differs between the selected runs.',
    });
  }

  const leftCategories = new Set(leftArtifacts.map((artifact) => artifact.category));
  const rightCategories = new Set(rightArtifacts.map((artifact) => artifact.category));
  const categoryDifference = [...new Set([...leftCategories, ...rightCategories])].filter(
    (category) => leftCategories.has(category) !== rightCategories.has(category),
  );
  if (categoryDifference.length > 0) {
    warnings.push({
      code: 'DIFFERENT_ARTIFACT_CATEGORIES',
      message: `Available artifact categories differ: ${categoryDifference.join(', ')}.`,
    });
  }
  return warnings;
}

function dateWindow(run: RunSummary): string {
  return `${run.date_start ?? 'unknown'}–${run.date_end ?? 'unknown'}`;
}

function stableSerialize(value: unknown): string {
  if (value === undefined) return 'undefined';
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableSerialize).join(',')}]`;
  return `{${Object.entries(value as Record<string, unknown>)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, item]) => `${JSON.stringify(key)}:${stableSerialize(item)}`)
    .join(',')}}`;
}
