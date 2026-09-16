import { describe, expect, it } from 'vitest';
import {
  averageDegreeInReturnedGraph,
  metricWeightLabel,
  parseMinWeight,
  transformNetworkResponse,
  updateNetworkSearchParams,
} from '../networkModel';

describe('network model', () => {
  const network = {
    run_id: 'run-1',
    metric: 'if' as const,
    period: null,
    community_id: null,
    nodes: [
      { id: '001', community_ids: ['1', '2'] },
      { id: 'user-2', community_ids: ['1'] },
      { id: '3', community_ids: [] },
    ],
    edges: [
      { source: '001', target: 'user-2', community_id: '1', direction: 'out', weight: 10 },
      { source: '3', target: '001', community_id: null, direction: 'out', weight: 2 },
    ],
    available_nodes: 3,
    available_edges: 2,
    returned_nodes: 3,
    returned_edges: 2,
    sampled: false,
  };

  it('preserves string IDs and computes returned-subgraph degrees', () => {
    const transformed = transformNetworkResponse(network, '2');
    expect(transformed.nodes.map((node) => node.id)).toEqual(['001', 'user-2', '3']);
    expect(transformed.nodes[0]).toMatchObject({
      id: '001', primaryCommunityId: '2', inDegree: 1, outDegree: 1, totalDegree: 2,
    });
    expect(transformed.links[0].weight).toBe(10);
    expect(transformed.links[0].width).toBeGreaterThan(transformed.links[1].width);
    expect(averageDegreeInReturnedGraph(transformed)).toBeCloseTo(4 / 3);
  });

  it('validates minimum weight and updates URL state without exceeding the UI cap', () => {
    expect(parseMinWeight('-2')).toBe(0);
    expect(parseMinWeight('not-a-number')).toBe(0);
    expect(parseMinWeight('999999999')).toBe(1_000_000);
    const params = updateNetworkSearchParams(new URLSearchParams('run=r&metric=if'), {
      communityId: ' 12 ', minWeight: 2.5,
    });
    expect(params.get('community')).toBe('12');
    expect(params.get('minWeight')).toBe('2.5');
    const cleared = updateNetworkSearchParams(params, { communityId: null, minWeight: 0 });
    expect(cleared.has('community')).toBe(false);
    expect(cleared.has('minWeight')).toBe(false);
  });

  it('labels IF and WIF edge metadata honestly', () => {
    expect(metricWeightLabel('if')).toContain('Interaction Frequency (IF)');
    expect(metricWeightLabel('wif')).toContain('Weighted Interaction Frequency (WIF)');
  });
});
