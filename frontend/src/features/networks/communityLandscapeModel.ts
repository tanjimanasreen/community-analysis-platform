import type { NetworkNode, NetworkResponse } from '../../types/api';
import { normalizeCommunityId } from '../../utils/communityIds';

export interface CommunityLandscapeItem {
  id: string;
  label: string;
  memberCount: number | null;
  internalEdgeCount: number | null;
  internalWeight: number | null;
  diameter: number;
  weightIntensity: number;
  borderWidth: number;
}

export interface CommunityLandscapeModel {
  items: CommunityLandscapeItem[];
  maxMemberCount: number;
  maxInternalWeight: number;
  maxInternalEdgeCount: number;
}

const MIN_DIAMETER = 68;
const MAX_DIAMETER = 132;
const MIN_BORDER_WIDTH = 1;
const MAX_BORDER_WIDTH = 5;

export function buildCommunityLandscapeModel(
  network: NetworkResponse | null | undefined,
): CommunityLandscapeModel {
  const communityNodes = (network?.nodes ?? [])
    .filter((node) => (node.node_type ?? network?.view) === 'community')
    .map(toCommunityNode)
    .sort((left, right) => (
      (right.memberCount ?? -1) - (left.memberCount ?? -1)
      || left.id.localeCompare(right.id, undefined, { numeric: true })
    ));

  const maxMemberCount = maxFinite(communityNodes.map((item) => item.memberCount));
  const maxInternalWeight = maxFinite(communityNodes.map((item) => item.internalWeight));
  const maxInternalEdgeCount = maxFinite(communityNodes.map((item) => item.internalEdgeCount));

  return {
    items: communityNodes.map((item) => ({
      ...item,
      diameter: relativeDiameter(item.memberCount, maxMemberCount),
      weightIntensity: normalizedEncoding(item.internalWeight, maxInternalWeight),
      borderWidth: MIN_BORDER_WIDTH
        + normalizedEncoding(item.internalEdgeCount, maxInternalEdgeCount)
          * (MAX_BORDER_WIDTH - MIN_BORDER_WIDTH),
    })),
    maxMemberCount,
    maxInternalWeight,
    maxInternalEdgeCount,
  };
}

function toCommunityNode(node: NetworkNode): Omit<CommunityLandscapeItem, 'diameter' | 'weightIntensity' | 'borderWidth'> {
  const id = normalizeCommunityId(node.community_id)
    ?? normalizeCommunityId(node.id)
    ?? String(node.id);
  return {
    id,
    label: `C${id}`,
    memberCount: finiteNumber(node.member_count),
    internalEdgeCount: finiteNumber(node.internal_edge_count),
    internalWeight: finiteNumber(node.internal_weight),
  };
}

function relativeDiameter(value: number | null, maximum: number): number {
  if (value === null || value <= 0 || maximum <= 0) return MIN_DIAMETER;
  return Math.max(MIN_DIAMETER, Math.min(MAX_DIAMETER, MAX_DIAMETER * Math.sqrt(value / maximum)));
}

function normalizedEncoding(value: number | null, maximum: number): number {
  if (value === null || value < 0 || maximum <= 0) return 0;
  return Math.max(0, Math.min(1, value / maximum));
}

function maxFinite(values: Array<number | null>): number {
  return values.reduce((maximum, value) => (
    value !== null && value > maximum ? value : maximum
  ), 0);
}

function finiteNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}
