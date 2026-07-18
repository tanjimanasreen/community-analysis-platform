import type { MetricName, NetworkResponse } from '../../types/api';
import { normalizeCommunityId } from '../../utils/communityIds';

export const NETWORK_UI_LIMITS = {
  maxNodes: 400,
  maxEdges: 1000,
  minWeightMax: 1_000_000,
} as const;

export interface NetworkGraphNode {
  id: string;
  communityIds: string[];
  primaryCommunityId: string | null;
  inDegree: number;
  outDegree: number;
  totalDegree: number;
  color: string;
  val: number;
}

export interface NetworkGraphLink {
  id: string;
  source: string;
  target: string;
  communityId: string | null;
  direction: string | null;
  weight: number;
  width: number;
  opacity: number;
}

export interface NetworkGraphData {
  nodes: NetworkGraphNode[];
  links: NetworkGraphLink[];
}

export function parseMinWeight(value: string | null): number {
  if (value === null || value.trim() === '') return 0;
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric < 0) return 0;
  return Math.min(numeric, NETWORK_UI_LIMITS.minWeightMax);
}

export function updateNetworkSearchParams(
  current: URLSearchParams,
  update: { communityId?: string | null; minWeight?: number | null },
): URLSearchParams {
  const next = new URLSearchParams(current);
  if (update.communityId !== undefined) {
    const communityId = normalizeCommunityId(update.communityId);
    if (communityId) next.set('community', communityId);
    else next.delete('community');
  }
  if (update.minWeight !== undefined) {
    const minWeight = update.minWeight === null ? 0 : parseMinWeight(String(update.minWeight));
    if (minWeight > 0) next.set('minWeight', String(minWeight));
    else next.delete('minWeight');
  }
  return next;
}

export function transformNetworkResponse(
  network: NetworkResponse | null | undefined,
  selectedCommunityId: string | null = null,
): NetworkGraphData {
  if (!network) return { nodes: [], links: [] };

  const degrees = new Map<string, { inDegree: number; outDegree: number }>();
  for (const node of network.nodes) {
    degrees.set(String(node.id), { inDegree: 0, outDegree: 0 });
  }
  for (const edge of network.edges) {
    const source = String(edge.source);
    const target = String(edge.target);
    const sourceDegree = degrees.get(source) ?? { inDegree: 0, outDegree: 0 };
    const targetDegree = degrees.get(target) ?? { inDegree: 0, outDegree: 0 };
    sourceDegree.outDegree += 1;
    targetDegree.inDegree += 1;
    degrees.set(source, sourceDegree);
    degrees.set(target, targetDegree);
  }

  const weights = network.edges.map((edge) => Math.max(0, Number(edge.weight) || 0));
  const maxWeight = Math.max(1, ...weights);

  return {
    nodes: network.nodes.map((node) => {
      const id = String(node.id);
      const communityIds = node.community_ids.map(String);
      const primaryCommunityId =
        (selectedCommunityId && communityIds.includes(selectedCommunityId)
          ? selectedCommunityId
          : communityIds[0]) ?? null;
      const degree = degrees.get(id) ?? { inDegree: 0, outDegree: 0 };
      const totalDegree = degree.inDegree + degree.outDegree;
      return {
        id,
        communityIds,
        primaryCommunityId,
        inDegree: degree.inDegree,
        outDegree: degree.outDegree,
        totalDegree,
        color: communityColor(primaryCommunityId),
        val: 2.5 + Math.sqrt(totalDegree),
      };
    }),
    links: network.edges.map((edge, index) => {
      const weight = Math.max(0, Number(edge.weight) || 0);
      const normalizedWeight = weight / maxWeight;
      return {
        id: `${String(edge.source)}-${String(edge.target)}-${index}`,
        source: String(edge.source),
        target: String(edge.target),
        communityId: normalizeCommunityId(edge.community_id),
        direction: edge.direction,
        weight,
        width: 0.5 + normalizedWeight * 3,
        opacity: 0.2 + normalizedWeight * 0.65,
      };
    }),
  };
}

export function averageDegreeInReturnedGraph(data: NetworkGraphData): number | null {
  if (data.nodes.length === 0) return null;
  const total = data.nodes.reduce((sum, node) => sum + node.totalDegree, 0);
  return total / data.nodes.length;
}

export function metricWeightLabel(metric: MetricName): string {
  return metric === 'if'
    ? 'Interaction Frequency (IF) edge weight'
    : 'Weighted Interaction Frequency (WIF) edge weight';
}

export function communityColor(communityId: string | null): string {
  if (!communityId) return 'hsl(215 16% 55%)';
  let hash = 0;
  for (let index = 0; index < communityId.length; index += 1) {
    hash = (hash * 31 + communityId.charCodeAt(index)) % 360;
  }
  return `hsl(${hash} 68% 64%)`;
}
