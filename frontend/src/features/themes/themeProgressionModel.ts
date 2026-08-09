import type {
  ThemeTimelineResponse,
  TransitionRecord,
  TransitionsResponse,
} from '../../types/api';
import { normalizeArtifactValue, normalizedTextList } from '../../utils/artifactValues';
import { normalizeCommunityId } from '../../utils/communityIds';

const MONTH_NAMES = [
  'january', 'february', 'march', 'april', 'may', 'june',
  'july', 'august', 'september', 'october', 'november', 'december',
];

export interface ThemeProgressionEvidence {
  absoluteCommunityId: string | null;
  weightedCommunityId: string | null;
  labels: string[];
  keywords: string[];
}

export interface ThemeProgressionNode {
  key: string;
  period: string;
  communityId: string;
  labels: string[];
  keywords: string[];
  absoluteCommunityId: string | null;
  weightedCommunityId: string | null;
}

export interface ThemeProgressionLink {
  key: string;
  sourceKey: string;
  targetKey: string;
  jaccard: number;
  retainedCount: number | null;
  startCount: number | null;
  endCount: number | null;
}

export interface ThemeProgressionPath {
  id: string;
  nodes: ThemeProgressionNode[];
  links: ThemeProgressionLink[];
  distinctMonthCount: number;
  totalRetainedMembers: number | null;
  averageJaccard: number;
}

export interface ThemeProgressionResult {
  complete: boolean;
  paths: ThemeProgressionPath[];
  returnedRecords: number;
  totalRecords: number;
}

interface MutableNode extends ThemeProgressionNode {
  outgoing: ThemeProgressionLink[];
  incoming: number;
}

interface MutableEvidence extends ThemeProgressionEvidence {
  pairKey: string;
}

export function buildThemeProgressionPaths(
  transitions: TransitionsResponse | null | undefined,
  timeline: ThemeTimelineResponse | null | undefined,
  periodStart: string | null,
  periodEnd: string | null,
  limit = 5,
): ThemeProgressionResult {
  if (!transitions) {
    return { complete: true, paths: [], returnedRecords: 0, totalRecords: 0 };
  }
  if (transitions.total > transitions.records.length) {
    return {
      complete: false,
      paths: [],
      returnedRecords: transitions.records.length,
      totalRecords: transitions.total,
    };
  }

  const periods = timeline?.periods ?? [];
  const evidence = buildEvidenceIndex(timeline);
  const nodes = new Map<string, MutableNode>();
  transitions.records.forEach((record, index) => {
    const startPeriod = resolveTransitionPeriod(record.start_month, periods);
    const endPeriod = resolveTransitionPeriod(record.end_month, periods);
    if (!startPeriod || !endPeriod) return;
    if (!withinRange(startPeriod, periodStart, periodEnd) || !withinRange(endPeriod, periodStart, periodEnd)) return;

    const startCommunity = normalizeCommunityId(record.start_month_community);
    const endCommunity = normalizeCommunityId(record.end_month_community);
    if (!startCommunity || !endCommunity) return;

    const startKey = nodeKey(startPeriod, startCommunity);
    const endKey = nodeKey(endPeriod, endCommunity);
    const startNode = ensureNode(
      nodes,
      startKey,
      startPeriod,
      startCommunity,
      transitionThemes(record, 'start'),
      evidence,
    );
    const endNode = ensureNode(
      nodes,
      endKey,
      endPeriod,
      endCommunity,
      transitionThemes(record, 'end'),
      evidence,
    );
    const link: ThemeProgressionLink = {
      key: `${startKey}->${endKey}:${index}`,
      sourceKey: startKey,
      targetKey: endKey,
      jaccard: finiteNumber(record.jaccard_score) ?? 0,
      retainedCount: countMembers(record.common_members),
      startCount: finiteNumber(record.total_start_month_members),
      endCount: finiteNumber(record.total_end_month_members),
    };
    startNode.outgoing.push(link);
    endNode.incoming += 1;
  });

  const roots = [...nodes.values()]
    .filter((node) => node.incoming === 0)
    .sort(compareNodes);
  const starts = roots.length > 0 ? roots : [...nodes.values()].sort(compareNodes);
  const rawPaths: Array<{ nodeKeys: string[]; links: ThemeProgressionLink[] }> = [];

  for (const root of starts) {
    walk(root.key, [], [], new Set<string>(), nodes, rawPaths);
  }

  const seenPaths = new Set<string>();
  const paths = rawPaths
    .map(({ nodeKeys, links: pathLinks }) => {
      const pathNodes = nodeKeys.map((key) => nodes.get(key)).filter((node): node is MutableNode => Boolean(node));
      const id = nodeKeys.join('>');
      const retained = pathLinks.map((link) => link.retainedCount);
      const availableRetained = retained.filter((value): value is number => value !== null);
      const allRetainedCountsAvailable = pathLinks.length > 0 && availableRetained.length === pathLinks.length;
      return {
        id,
        nodes: pathNodes.map(stripMutableNode),
        links: pathLinks,
        distinctMonthCount: new Set(pathNodes.map((node) => node.period)).size,
        totalRetainedMembers: allRetainedCountsAvailable
          ? availableRetained.reduce((sum, value) => sum + value, 0)
          : null,
        averageJaccard: pathLinks.length > 0
          ? pathLinks.reduce((sum, link) => sum + link.jaccard, 0) / pathLinks.length
          : 0,
      } satisfies ThemeProgressionPath;
    })
    .filter((path) => {
      if (path.nodes.length < 2 || seenPaths.has(path.id)) return false;
      seenPaths.add(path.id);
      return true;
    })
    .sort(comparePaths)
    .slice(0, Math.max(0, limit));

  return {
    complete: true,
    paths,
    returnedRecords: transitions.records.length,
    totalRecords: transitions.total,
  };
}

function buildEvidenceIndex(timeline: ThemeTimelineResponse | null | undefined): Map<string, ThemeProgressionEvidence> {
  const candidates = new Map<string, Map<string, MutableEvidence>>();
  for (const summary of timeline?.monthly_summaries ?? []) {
    for (const theme of summary.themes) {
      for (const pair of theme.community_pairs) {
        const absolute = normalizeCommunityId(pair.absolute_community);
        const weighted = normalizeCommunityId(pair.weighted_community);
        const pairKey = `if:${absolute ?? ''}|wif:${weighted ?? ''}`;
        for (const communityId of unique([absolute, weighted].filter((value): value is string => Boolean(value)))) {
          const key = nodeKey(summary.period, communityId);
          const byPair = candidates.get(key) ?? new Map<string, MutableEvidence>();
          const current = byPair.get(pairKey) ?? {
            pairKey,
            absoluteCommunityId: absolute,
            weightedCommunityId: weighted,
            labels: [],
            keywords: [],
          };
          current.labels = unique([...current.labels, theme.name]);
          current.keywords = unique([...current.keywords, ...pair.keywords, ...theme.keywords]);
          byPair.set(pairKey, current);
          candidates.set(key, byPair);
        }
      }
    }
  }

  const index = new Map<string, ThemeProgressionEvidence>();
  for (const [key, byPair] of candidates) {
    if (byPair.size !== 1) continue;
    const [{ pairKey: _pairKey, ...evidence }] = [...byPair.values()];
    index.set(key, evidence);
  }
  return index;
}

function ensureNode(
  nodes: Map<string, MutableNode>,
  key: string,
  period: string,
  communityId: string,
  savedLabels: string[],
  evidence: Map<string, ThemeProgressionEvidence>,
): MutableNode {
  const existing = nodes.get(key);
  const item = evidence.get(key);
  const labels = savedLabels.length > 0 ? savedLabels : item?.labels ?? [];
  if (existing) {
    existing.labels = unique([...existing.labels, ...labels]);
    existing.keywords = unique([...existing.keywords, ...(item?.keywords ?? [])]);
    existing.absoluteCommunityId ??= item?.absoluteCommunityId ?? null;
    existing.weightedCommunityId ??= item?.weightedCommunityId ?? null;
    return existing;
  }
  const node: MutableNode = {
    key,
    period,
    communityId,
    labels,
    keywords: item?.keywords ?? [],
    absoluteCommunityId: item?.absoluteCommunityId ?? null,
    weightedCommunityId: item?.weightedCommunityId ?? null,
    outgoing: [],
    incoming: 0,
  };
  nodes.set(key, node);
  return node;
}

function transitionThemes(record: TransitionRecord, side: 'start' | 'end'): string[] {
  const general = normalizedTextList(
    side === 'start' ? record.start_month_general_theme : record.end_month_general_theme,
  );
  if (general.length > 0) return unique(general);
  const absolute = side === 'start'
    ? record.start_month_absolute_theme
    : record.end_month_absolute_theme;
  const weighted = side === 'start'
    ? record.start_month_weighted_theme
    : record.end_month_weighted_theme;
  return unique([
    ...normalizedTextList(absolute),
    ...normalizedTextList(weighted),
  ]);
}

function walk(
  currentKey: string,
  nodeKeys: string[],
  pathLinks: ThemeProgressionLink[],
  visited: Set<string>,
  nodes: Map<string, MutableNode>,
  output: Array<{ nodeKeys: string[]; links: ThemeProgressionLink[] }>,
): void {
  if (visited.has(currentKey)) return;
  const node = nodes.get(currentKey);
  if (!node) return;
  const nextVisited = new Set(visited);
  nextVisited.add(currentKey);
  const nextNodeKeys = [...nodeKeys, currentKey];
  const outgoing = [...node.outgoing].sort((left, right) => left.targetKey.localeCompare(right.targetKey));
  if (outgoing.length === 0) {
    output.push({ nodeKeys: nextNodeKeys, links: pathLinks });
    return;
  }
  for (const link of outgoing) {
    walk(link.targetKey, nextNodeKeys, [...pathLinks, link], nextVisited, nodes, output);
  }
}

function stripMutableNode(node: MutableNode): ThemeProgressionNode {
  const { outgoing: _outgoing, incoming: _incoming, ...clean } = node;
  return clean;
}

function compareNodes(left: MutableNode, right: MutableNode): number {
  return left.period.localeCompare(right.period) || left.communityId.localeCompare(right.communityId, undefined, { numeric: true });
}

function comparePaths(left: ThemeProgressionPath, right: ThemeProgressionPath): number {
  if (right.distinctMonthCount !== left.distinctMonthCount) return right.distinctMonthCount - left.distinctMonthCount;
  const leftRetained = left.totalRetainedMembers ?? -1;
  const rightRetained = right.totalRetainedMembers ?? -1;
  if (rightRetained !== leftRetained) return rightRetained - leftRetained;
  if (right.averageJaccard !== left.averageJaccard) return right.averageJaccard - left.averageJaccard;
  return left.id.localeCompare(right.id, undefined, { numeric: true });
}

function resolveTransitionPeriod(value: string, periods: string[]): string | null {
  const raw = String(value ?? '').trim();
  if (!raw) return null;
  const direct = /^(\d{4})[-_/](\d{1,2})$/.exec(raw);
  if (direct) {
    const monthNumber = Number(direct[2]);
    if (monthNumber >= 1 && monthNumber <= 12) {
      return `${direct[1]}-${String(monthNumber).padStart(2, '0')}`;
    }
  }

  let monthNumber: number | null = null;
  if (/^\d{1,2}$/.test(raw)) {
    const candidate = Number(raw);
    if (candidate >= 1 && candidate <= 12) monthNumber = candidate;
  } else {
    const normalized = raw.toLocaleLowerCase().replace(/[^a-z]/g, '');
    const index = MONTH_NAMES.findIndex((name) => (
      name === normalized || (normalized.length >= 3 && name.slice(0, 3) === normalized.slice(0, 3))
    ));
    if (index >= 0) monthNumber = index + 1;
  }
  if (monthNumber === null) return null;
  const month = String(monthNumber).padStart(2, '0');
  const matches = periods.filter((period) => period.endsWith(`-${month}`));
  return matches.length === 1 ? matches[0] : null;
}

function withinRange(period: string, start: string | null, end: string | null): boolean {
  return (!start || period >= start) && (!end || period <= end);
}

function countMembers(value: unknown): number | null {
  const normalized = normalizeArtifactValue(value);
  if (normalized === null || normalized === '') return null;
  if (Array.isArray(normalized)) return normalized.length;
  return normalizedTextList(normalized).length;
}

function finiteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function nodeKey(period: string, communityId: string): string {
  return `${period}:${communityId}`;
}

function unique(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))];
}
