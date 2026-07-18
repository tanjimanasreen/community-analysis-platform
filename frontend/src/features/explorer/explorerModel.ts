import type {
  ArtifactMetadata,
  CommunitySummary,
  MetricName,
  ThemeRecord,
  TopicRecord,
  TransitionRecord,
} from '../../types/api';
import { communityIdForMetric, extractCommunityIdentifiers } from '../../utils/communityIds';

export type ExplorerMode =
  | 'communities'
  | 'centrality'
  | 'matched-topics'
  | 'partial-topics'
  | 'themes'
  | 'transitions'
  | 'artifacts';

export interface ExplorerColumn {
  key: string;
  label: string;
}

export interface ExplorerPage {
  records: Record<string, unknown>[];
  total: number;
  limit: number;
  offset: number;
}

export const EXPLORER_MODES: Array<{ id: ExplorerMode; label: string }> = [
  { id: 'communities', label: 'Communities' },
  { id: 'centrality', label: 'Centrality' },
  { id: 'matched-topics', label: 'Matched topics' },
  { id: 'partial-topics', label: 'Partial topics' },
  { id: 'themes', label: 'Themes' },
  { id: 'transitions', label: 'Transitions' },
  { id: 'artifacts', label: 'Artifacts' },
];

const CENTRALITY_COLUMNS = ['month', 'absolute', 'weighted'] as const;

export function explorerColumns(mode: ExplorerMode): ExplorerColumn[] {
  switch (mode) {
    case 'communities':
      return [
        { key: 'community_id', label: 'Community ID' },
        { key: 'node_count', label: 'Nodes' },
        { key: 'edge_count', label: 'Edges' },
        { key: 'total_weight', label: 'Total weight' },
      ];
    case 'centrality':
      return [
        { key: 'month', label: 'Month' },
        { key: 'absolute', label: 'IF centrality' },
        { key: 'weighted', label: 'WIF centrality' },
      ];
    case 'matched-topics':
    case 'partial-topics':
      return [
        { key: 'absolute_community', label: 'IF community' },
        { key: 'weighted_community', label: 'WIF community' },
        { key: 'absolute_unigram_topic', label: 'IF unigram topic' },
        { key: 'weighted_unigram_topic', label: 'WIF unigram topic' },
        { key: 'jaccard_score', label: 'Jaccard' },
      ];
    case 'themes':
      return [
        { key: 'month', label: 'Month' },
        { key: 'absolute_community', label: 'IF community' },
        { key: 'weighted_community', label: 'WIF community' },
        { key: 'general_theme_names', label: 'General themes' },
        { key: 'absolute_theme_names', label: 'IF themes' },
        { key: 'weighted_theme_names', label: 'WIF themes' },
      ];
    case 'transitions':
      return [
        { key: 'start_month', label: 'Start month' },
        { key: 'start_month_community', label: 'Start community' },
        { key: 'end_month', label: 'End month' },
        { key: 'end_month_community', label: 'End community' },
        { key: 'jaccard_score', label: 'Jaccard' },
      ];
    case 'artifacts':
      return [
        { key: 'key', label: 'Key' },
        { key: 'category', label: 'Category' },
        { key: 'media_type', label: 'Media type' },
        { key: 'schema_version', label: 'Schema version' },
        { key: 'stage', label: 'Stage' },
        { key: 'rows', label: 'Rows' },
        { key: 'byte_size', label: 'Bytes' },
      ];
  }
}

export function adaptCommunities(records: CommunitySummary[]): Record<string, unknown>[] {
  return records.map((record) => ({ ...record }));
}

export function adaptCentrality(records: Record<string, unknown>[]): Record<string, unknown>[] {
  return records.map((record) => {
    const adapted: Record<string, unknown> = {};
    for (const key of CENTRALITY_COLUMNS) {
      adapted[key] = key in record ? record[key] : null;
    }
    return adapted;
  });
}

export function adaptTopics(records: TopicRecord[]): Record<string, unknown>[] {
  return records.map((record) => ({ ...record }));
}

export function adaptThemes(records: ThemeRecord[]): Record<string, unknown>[] {
  return records.map((record) => ({ ...record }));
}

export function adaptTransitions(records: TransitionRecord[]): Record<string, unknown>[] {
  return records.map((record) => ({ ...record }));
}

export function adaptArtifacts(records: ArtifactMetadata[]): Record<string, unknown>[] {
  return records.map((record) => ({ ...record }));
}

export function safeDisplayValue(value: unknown): string {
  if (value === null || value === undefined) return 'Unavailable';
  if (typeof value === 'string') return value || '—';
  if (typeof value === 'number') {
    return Number.isFinite(value)
      ? new Intl.NumberFormat('en-US', { maximumFractionDigits: 4 }).format(value)
      : 'Unavailable';
  }
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (Array.isArray(value)) return value.map(safeDisplayValue).join(', ');
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return '[Unserializable value]';
    }
  }
  return String(value);
}

export function filterLoadedPage(
  records: Record<string, unknown>[],
  query: string,
): Record<string, unknown>[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return records;
  return records.filter((record) =>
    Object.values(record).some((value) => safeDisplayValue(value).toLowerCase().includes(normalized)),
  );
}

export function recordKey(record: Record<string, unknown>, index: number): string {
  const identifiers = extractCommunityIdentifiers(record);
  let candidate: unknown = record.key ?? identifiers.genericId;
  if (candidate === null || candidate === undefined) {
    if (identifiers.ifId || identifiers.wifId) {
      candidate = `${identifiers.ifId ?? ''}:${identifiers.wifId ?? ''}`;
    } else {
      candidate = `${record.start_month ?? ''}:${identifiers.startId ?? ''}:${record.end_month ?? ''}:${identifiers.endId ?? ''}`;
    }
  }
  return `${safeDisplayValue(candidate)}-${index}`;
}

export function navigationCommunityId(
  record: Record<string, unknown>,
  metric: MetricName,
): string | null {
  return communityIdForMetric(record, metric);
}

export function isArtifactDownloadable(record: Record<string, unknown>): boolean {
  return record.category !== 'intermediate' && typeof record.key === 'string';
}

export function modeSupportsExactCommunitySearch(mode: ExplorerMode): boolean {
  return mode === 'matched-topics' || mode === 'partial-topics' || mode === 'themes';
}
