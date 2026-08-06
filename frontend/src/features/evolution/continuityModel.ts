import type { TransitionRecord } from '../../types/api';
import { normalizedTextList } from '../../utils/artifactValues';
import { normalizeCommunityId } from '../../utils/communityIds';

export interface ContinuityMonth {
  key: string;
  label: string;
  order: number;
}

export interface ContinuityNode {
  key: string;
  monthKey: string;
  monthLabel: string;
  monthOrder: number;
  communityId: string;
  memberCount: number | null;
  memberCountValues: number[];
  memberCountInconsistent: boolean;
}

export interface ContinuityLink {
  key: string;
  sourceKey: string;
  targetKey: string;
  startMonthLabel: string;
  endMonthLabel: string;
  startCommunityId: string;
  endCommunityId: string;
  retainedCount: number | null;
  startMemberCount: number | null;
  endMemberCount: number | null;
  jaccard: number;
}

export interface ContinuityPath {
  id: string;
  nodes: ContinuityNode[];
  links: ContinuityLink[];
  months: ContinuityMonth[];
  duration: number;
  totalRetainedMembers: number;
  retainedCountAvailable: boolean;
  earliestKey: string;
  inconsistentNodeCount: number;
}

export interface ContinuityModel {
  paths: ContinuityPath[];
  months: ContinuityMonth[];
  displayedPaths: number;
  totalPaths: number;
}

interface MutableNode {
  key: string;
  month: ContinuityMonth;
  communityId: string;
  memberCounts: Set<number>;
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export function buildContinuityModel(
  records: TransitionRecord[],
  maxPaths = 5,
): ContinuityModel {
  const nodes = new Map<string, MutableNode>();
  const links: ContinuityLink[] = [];
  const directedAdjacency = new Map<string, Set<string>>();
  const inDegrees = new Map<string, number>();

  records.forEach((record, index) => {
    const startMonth = normalizeTransitionMonth(record.start_month);
    const endMonth = normalizeTransitionMonth(record.end_month);
    const startCommunityId = normalizeCommunityId(record.start_month_community)
      ?? String(record.start_month_community);
    const endCommunityId = normalizeCommunityId(record.end_month_community)
      ?? String(record.end_month_community);
    const sourceKey = nodeKey(startMonth.key, startCommunityId);
    const targetKey = nodeKey(endMonth.key, endCommunityId);
    const startMemberCount = finiteNumber(record.total_start_month_members);
    const endMemberCount = finiteNumber(record.total_end_month_members);

    ensureNode(nodes, sourceKey, startMonth, startCommunityId, startMemberCount);
    ensureNode(nodes, targetKey, endMonth, endCommunityId, endMemberCount);

    const outEdges = directedAdjacency.get(sourceKey) ?? new Set<string>();
    outEdges.add(targetKey);
    directedAdjacency.set(sourceKey, outEdges);

    inDegrees.set(targetKey, (inDegrees.get(targetKey) ?? 0) + 1);
    if (!inDegrees.has(sourceKey)) inDegrees.set(sourceKey, 0);

    links.push({
      key: `${sourceKey}->${targetKey}:${index}`,
      sourceKey,
      targetKey,
      startMonthLabel: startMonth.label,
      endMonthLabel: endMonth.label,
      startCommunityId,
      endCommunityId,
      retainedCount: commonMemberCount(record.common_members),
      startMemberCount,
      endMemberCount,
      jaccard: finiteNumber(record.jaccard_score) ?? 0,
    });
  });

  const nodeModels = new Map(
    [...nodes.entries()].map(([key, node]) => [key, finalizeNode(node)]),
  );
  const components = findDFSPaths([...nodes.keys()], directedAdjacency, inDegrees);
  const allPaths = components
    .map((component, index) => buildPath(component, links, nodeModels, index))
    .filter((path) => path.links.length > 0)
    .sort(comparePaths);
  const paths = allPaths.slice(0, Math.max(0, maxPaths));
  const months = uniqueMonths(paths.flatMap((path) => path.months));

  return {
    paths,
    months,
    displayedPaths: paths.length,
    totalPaths: allPaths.length,
  };
}

export function normalizeTransitionMonth(value: string): ContinuityMonth {
  const raw = String(value ?? '').trim();
  const yearMonth = /^(\d{4})[-_/](\d{1,2})$/.exec(raw);
  if (yearMonth) {
    const year = Number(yearMonth[1]);
    const month = validMonth(Number(yearMonth[2]));
    if (month !== null) {
      return {
        key: `${year}-${String(month).padStart(2, '0')}`,
        label: `${MONTH_NAMES[month - 1]} ${year}`,
        order: year * 12 + month,
      };
    }
  }

  if (/^\d{1,2}$/.test(raw)) {
    const month = validMonth(Number(raw));
    if (month !== null) {
      return {
        key: String(month).padStart(2, '0'),
        label: MONTH_NAMES[month - 1],
        order: month,
      };
    }
  }

  const normalizedName = raw.toLocaleLowerCase().replace(/[^a-z]/g, '');
  const monthIndex = MONTH_NAMES.findIndex((name) => (
    name.toLocaleLowerCase() === normalizedName
    || name.toLocaleLowerCase().slice(0, 3) === normalizedName.slice(0, 3)
  ));
  if (monthIndex >= 0 && normalizedName.length >= 3) {
    return {
      key: String(monthIndex + 1).padStart(2, '0'),
      label: MONTH_NAMES[monthIndex],
      order: monthIndex + 1,
    };
  }

  return {
    key: raw || 'unknown',
    label: raw || 'Unknown month',
    order: 100_000 + stableHash(raw),
  };
}

function ensureNode(
  nodes: Map<string, MutableNode>,
  key: string,
  month: ContinuityMonth,
  communityId: string,
  memberCount: number | null,
): void {
  const node = nodes.get(key) ?? {
    key,
    month,
    communityId,
    memberCounts: new Set<number>(),
  };
  if (memberCount !== null) node.memberCounts.add(memberCount);
  nodes.set(key, node);
}

function finalizeNode(node: MutableNode): ContinuityNode {
  const memberCountValues = [...node.memberCounts].sort((left, right) => left - right);
  return {
    key: node.key,
    monthKey: node.month.key,
    monthLabel: node.month.label,
    monthOrder: node.month.order,
    communityId: node.communityId,
    memberCount: memberCountValues.length === 1 ? memberCountValues[0] : null,
    memberCountValues,
    memberCountInconsistent: memberCountValues.length > 1,
  };
}

function buildPath(
  component: Set<string>,
  allLinks: ContinuityLink[],
  nodes: Map<string, ContinuityNode>,
  index: number,
): ContinuityPath {
  const pathNodes = [...component]
    .map((key) => nodes.get(key))
    .filter((node): node is ContinuityNode => Boolean(node))
    .sort(compareNodes);
  const pathLinks = allLinks
    .filter((link) => component.has(link.sourceKey) && component.has(link.targetKey))
    .sort((left, right) => (
      (nodes.get(left.sourceKey)?.monthOrder ?? 0) - (nodes.get(right.sourceKey)?.monthOrder ?? 0)
      || left.startCommunityId.localeCompare(right.startCommunityId, undefined, { numeric: true })
      || left.endCommunityId.localeCompare(right.endCommunityId, undefined, { numeric: true })
    ));
  const months = uniqueMonths(pathNodes.map((node) => ({
    key: node.monthKey,
    label: node.monthLabel,
    order: node.monthOrder,
  })));
  const earliestKey = pathNodes.length > 0
    ? `${String(pathNodes[0].monthOrder).padStart(8, '0')}:${pathNodes[0].communityId}`
    : String(index);
  return {
    id: `persistent-path-${index + 1}`,
    nodes: pathNodes,
    links: pathLinks,
    months,
    duration: months.length,
    totalRetainedMembers: pathLinks.reduce((sum, link) => sum + (link.retainedCount ?? 0), 0),
    retainedCountAvailable: pathLinks.some((link) => link.retainedCount !== null),
    earliestKey,
    inconsistentNodeCount: pathNodes.filter((node) => node.memberCountInconsistent).length,
  };
}

function findDFSPaths(
  nodeKeys: string[],
  adjacency: Map<string, Set<string>>,
  inDegrees: Map<string, number>
): Set<string>[] {
  const paths: Set<string>[] = [];
  const startNodes = nodeKeys.filter(key => (inDegrees.get(key) ?? 0) === 0).sort();

  function dfs(currentPath: string[]) {
    const current = currentPath[currentPath.length - 1];
    const neighbors = adjacency.get(current) ?? new Set<string>();

    if (neighbors.size === 0) {
      paths.push(new Set(currentPath));
      return;
    }

    const sortedNeighbors = [...neighbors].sort();
    for (const neighbor of sortedNeighbors) {
      if (!currentPath.includes(neighbor)) {
        currentPath.push(neighbor);
        dfs(currentPath);
        currentPath.pop();
      }
    }
  }

  for (const start of startNodes) {
    dfs([start]);
  }

  return paths;
}

function commonMemberCount(value: unknown): number | null {
  const commonMembers = normalizedTextList(value);
  return commonMembers.length > 0 ? commonMembers.length : null;
}

function uniqueMonths(months: ContinuityMonth[]): ContinuityMonth[] {
  const byKey = new Map<string, ContinuityMonth>();
  for (const month of months) if (!byKey.has(month.key)) byKey.set(month.key, month);
  return [...byKey.values()].sort((left, right) => left.order - right.order || left.key.localeCompare(right.key));
}

function comparePaths(left: ContinuityPath, right: ContinuityPath): number {
  return right.duration - left.duration
    || right.totalRetainedMembers - left.totalRetainedMembers
    || left.earliestKey.localeCompare(right.earliestKey, undefined, { numeric: true });
}

function compareNodes(left: ContinuityNode, right: ContinuityNode): number {
  return left.monthOrder - right.monthOrder
    || left.communityId.localeCompare(right.communityId, undefined, { numeric: true });
}

function nodeKey(monthKey: string, communityId: string): string {
  return `${monthKey}\u0000${communityId}`;
}

function finiteNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function validMonth(value: number): number | null {
  const month = Math.trunc(value);
  return month >= 1 && month <= 12 ? month : null;
}

function stableHash(value: string): number {
  let hash = 0;
  for (const character of value) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return hash;
}
