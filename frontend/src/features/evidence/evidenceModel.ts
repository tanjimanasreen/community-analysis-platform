import type {
  CentralityLeadersPeriod,
  CommunitySummary,
  MetricName,
  ThemeRecord,
  TopicRecord,
  TransitionRecord,
} from '../../types/api';
import { communityIdForMetric, extractCommunityIdentifiers } from '../../utils/communityIds';

export const EVIDENCE_VIEW_PARAM = 'view';
export const DEFAULT_EVIDENCE_VIEW: EvidenceView = 'communities';

export type EvidenceView =
  | 'communities'
  | 'centrality'
  | 'matched-lda'
  | 'partial-lda'
  | 'themes'
  | 'transitions'
  | 'outputs';

export type EvidenceDimension = 'structural' | 'semantic' | 'temporal' | 'outputs';

export interface EvidenceViewDefinition {
  id: EvidenceView;
  label: string;
  shortLabel: string;
  dimension: EvidenceDimension;
  rq: string;
  eyebrow: string;
  description: string;
  requiresPeriod: boolean;
  usesMetric: boolean;
  supportsCommunitySearch: boolean;
  paginated: boolean;
}

export interface EvidenceColumn {
  key: string;
  label: string;
}

export interface EvidencePage {
  records: Record<string, unknown>[];
  total: number;
  limit: number;
  offset: number;
}

export const EVIDENCE_VIEWS: Record<EvidenceView, EvidenceViewDefinition> = {
  communities: {
    id: 'communities',
    label: 'Communities',
    shortLabel: 'Communities',
    dimension: 'structural',
    rq: 'RQ1',
    eyebrow: 'Structural evidence · RQ1',
    description: 'Monthly Louvain community summaries for the selected IF/WIF partition.',
    requiresPeriod: true,
    usesMetric: true,
    supportsCommunitySearch: false,
    paginated: true,
  },
  centrality: {
    id: 'centrality',
    label: 'Centrality',
    shortLabel: 'Centrality',
    dimension: 'structural',
    rq: 'RQ1',
    eyebrow: 'Structural evidence · RQ1',
    description: 'Period-specific structural reach for influential creators and spreaders from the persisted centrality output.',
    requiresPeriod: true,
    usesMetric: true,
    supportsCommunitySearch: false,
    paginated: false,
  },
  'matched-lda': {
    id: 'matched-lda',
    label: 'Matched LDA',
    shortLabel: 'Matched LDA',
    dimension: 'semantic',
    rq: 'RQ2',
    eyebrow: 'Semantic evidence · RQ2',
    description: 'Saved LDA evidence for communities matched across IF and WIF partitions.',
    requiresPeriod: true,
    usesMetric: false,
    supportsCommunitySearch: true,
    paginated: true,
  },
  'partial-lda': {
    id: 'partial-lda',
    label: 'Partial-match LDA',
    shortLabel: 'Partial-match LDA',
    dimension: 'semantic',
    rq: 'RQ2',
    eyebrow: 'Semantic evidence · RQ2',
    description: 'Saved LDA evidence for partially overlapping IF/WIF communities.',
    requiresPeriod: true,
    usesMetric: false,
    supportsCommunitySearch: true,
    paginated: true,
  },
  themes: {
    id: 'themes',
    label: 'Generated Themes',
    shortLabel: 'Generated Themes',
    dimension: 'semantic',
    rq: 'RQ2',
    eyebrow: 'Semantic interpretation · RQ2',
    description: 'Human-readable theme labels generated downstream from persisted LDA keyword evidence.',
    requiresPeriod: true,
    usesMetric: false,
    supportsCommunitySearch: true,
    paginated: true,
  },
  transitions: {
    id: 'transitions',
    label: 'Community Transitions',
    shortLabel: 'Community Transitions',
    dimension: 'temporal',
    rq: 'RQ3 / RQ4',
    eyebrow: 'Temporal evidence · RQ3 / RQ4',
    description: 'Persisted month-to-month community relationships derived from membership overlap.',
    requiresPeriod: false,
    usesMetric: false,
    supportsCommunitySearch: false,
    paginated: true,
  },
  outputs: {
    id: 'outputs',
    label: 'Artifacts & Reports',
    shortLabel: 'Artifacts & Reports',
    dimension: 'outputs',
    rq: 'Provenance',
    eyebrow: 'Run outputs · Provenance',
    description: 'Verified artifacts and already-produced report outputs from the selected canonical run.',
    requiresPeriod: false,
    usesMetric: false,
    supportsCommunitySearch: false,
    paginated: false,
  },
};

export const EVIDENCE_GROUPS = [
  {
    id: 'structural',
    label: 'Structural · RQ1',
    views: ['communities', 'centrality'] as EvidenceView[],
  },
  {
    id: 'semantic',
    label: 'Semantic · RQ2',
    views: ['matched-lda', 'partial-lda', 'themes'] as EvidenceView[],
  },
  {
    id: 'temporal',
    label: 'Temporal · RQ3 / RQ4',
    views: ['transitions'] as EvidenceView[],
  },
  {
    id: 'outputs',
    label: 'Run Outputs',
    views: ['outputs'] as EvidenceView[],
  },
] as const;

export function isEvidenceView(value: string | null): value is EvidenceView {
  return Boolean(value && value in EVIDENCE_VIEWS);
}

export function resolveEvidenceView(value: string | null): EvidenceView {
  return isEvidenceView(value) ? value : DEFAULT_EVIDENCE_VIEW;
}

export function evidenceColumns(view: EvidenceView): EvidenceColumn[] {
  switch (view) {
    case 'communities':
      return [
        { key: 'community_id', label: 'Community' },
        { key: 'node_count', label: 'Members' },
        { key: 'edge_count', label: 'Internal edges' },
        { key: 'total_weight', label: 'Total weight' },
        { key: 'cross_community_neighbor_count', label: 'Connected communities' },
        { key: 'inbound_cross_community_weight', label: 'Inbound cross weight' },
        { key: 'outbound_cross_community_weight', label: 'Outbound cross weight' },
      ];
    case 'centrality':
      return [
        { key: 'period', label: 'Period' },
        { key: 'top_spreader', label: 'Top spreader' },
        { key: 'spreader_centrality', label: 'In-degree centrality' },
        { key: 'top_influencer', label: 'Top influencer' },
        { key: 'influencer_centrality', label: 'Out-degree centrality' },
      ];
    case 'matched-lda':
    case 'partial-lda':
      return [
        { key: 'absolute_community', label: 'IF community' },
        { key: 'weighted_community', label: 'WIF community' },
        { key: 'absolute_unigram_topic', label: 'IF unigram topic' },
        { key: 'weighted_unigram_topic', label: 'WIF unigram topic' },
        { key: 'jaccard_score', label: 'Jaccard' },
      ];
    case 'themes':
      return [
        { key: 'month', label: 'Period' },
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
    case 'outputs':
      return [];
  }
}

export function adaptCommunities(records: CommunitySummary[]): Record<string, unknown>[] {
  return records.map((record) => ({ ...record }));
}

export function adaptCentralityLeader(
  period: CentralityLeadersPeriod,
  methodologyNote: string,
): Record<string, unknown> {
  return {
    period: period.period,
    top_spreader: period.spreader?.display_user_id || period.spreader?.user_id || null,
    spreader_centrality: period.spreader?.centrality ?? null,
    spreader_community: period.spreader?.community_id ?? null,
    top_influencer: period.influencer?.display_user_id || period.influencer?.user_id || null,
    influencer_centrality: period.influencer?.centrality ?? null,
    influencer_community: period.influencer?.community_id ?? null,
    average_in_degree_centrality: period.average_in_degree_centrality,
    average_out_degree_centrality: period.average_out_degree_centrality,
    methodology_note: methodologyNote,
  };
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

export function recordKey(record: Record<string, unknown>, index: number): string {
  const identifiers = extractCommunityIdentifiers(record);
  let candidate: unknown = record.key ?? identifiers.genericId;
  if (candidate === null || candidate === undefined) {
    if (identifiers.ifId || identifiers.wifId) {
      candidate = `${identifiers.ifId ?? ''}:${identifiers.wifId ?? ''}`;
    } else {
      candidate = `${record.start_month ?? record.period ?? ''}:${identifiers.startId ?? ''}:${record.end_month ?? ''}:${identifiers.endId ?? ''}`;
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
