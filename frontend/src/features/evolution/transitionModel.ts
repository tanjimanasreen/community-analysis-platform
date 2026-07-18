import Papa from 'papaparse';
import type { MembershipChange, TransitionRecord } from '../../types/api';
import { normalizedTextList } from '../../utils/artifactValues';

export interface SankeyNode {
  name: string;
}

export interface SankeyLink {
  source: number;
  target: number;
  value: number;
  jaccard: number;
  startLabel: string;
  endLabel: string;
}

export interface SankeyModel {
  nodes: SankeyNode[];
  links: SankeyLink[];
  displayedLinks: number;
  totalLinks: number;
}

export function buildTransitionSankeyModel(
  records: TransitionRecord[],
  maxLinks = 60,
): SankeyModel {
  const selected = [...records]
    .sort((left, right) => right.jaccard_score - left.jaccard_score)
    .slice(0, maxLinks);
  const nodeIndex = new Map<string, number>();
  const nodes: SankeyNode[] = [];
  const ensureNode = (label: string): number => {
    const existing = nodeIndex.get(label);
    if (existing !== undefined) return existing;
    const index = nodes.length;
    nodeIndex.set(label, index);
    nodes.push({ name: label });
    return index;
  };
  const links = selected.map((record) => {
    const startLabel = `${record.start_month}:${String(record.start_month_community)}`;
    const endLabel = `${record.end_month}:${String(record.end_month_community)}`;
    return {
      source: ensureNode(startLabel),
      target: ensureNode(endLabel),
      value: Math.max(0.01, record.jaccard_score),
      jaccard: record.jaccard_score,
      startLabel,
      endLabel,
    };
  });
  return {
    nodes,
    links,
    displayedLinks: links.length,
    totalLinks: records.length,
  };
}

export function transitionCommonCount(record: TransitionRecord): number | null {
  const common = normalizedTextList(record.common_members);
  return common.length > 0 ? common.length : null;
}

export function transitionsCsv(records: TransitionRecord[]): string {
  return Papa.unparse(records.map((record) => ({
    start_month: record.start_month,
    start_community: String(record.start_month_community),
    end_month: record.end_month,
    end_community: String(record.end_month_community),
    jaccard_score: record.jaccard_score,
    common_member_count: transitionCommonCount(record) ?? '',
    start_member_count: record.total_start_month_members ?? '',
    end_member_count: record.total_end_month_members ?? '',
  })));
}

export function membershipChangesCsv(records: MembershipChange[]): string {
  return Papa.unparse(records.map((record) => ({ ...record })));
}

export function downloadCsv(contents: string, filename: string): void {
  const blob = new Blob([contents], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
