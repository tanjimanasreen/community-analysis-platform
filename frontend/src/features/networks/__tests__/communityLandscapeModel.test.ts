import { describe, expect, it } from 'vitest';
import { buildCommunityLandscapeModel } from '../communityLandscapeModel';
import type { NetworkResponse } from '../../../types/api';

function network(): NetworkResponse {
  return {
    run_id: 'run-1', metric: 'if', period: '2017-02', community_id: null,
    view: 'communities', sampling_strategy: null,
    nodes: [
      { id: '10', community_ids: ['10'], node_type: 'community', member_count: 9, internal_edge_count: 5, internal_weight: 20 },
      { id: '2', community_ids: ['2'], node_type: 'community', member_count: 100, internal_edge_count: 50, internal_weight: 200 },
    ],
    edges: [], available_nodes: 2, available_edges: 0,
    returned_nodes: 2, returned_edges: 0, sampled: false,
  };
}

describe('community landscape model', () => {
  it('sorts deterministically and scales area, weight intensity, and border independently', () => {
    const model = buildCommunityLandscapeModel(network());
    expect(model.items.map((item) => item.id)).toEqual(['2', '10']);
    expect(model.items[0].diameter).toBeGreaterThan(model.items[1].diameter);
    expect(model.items[0].weightIntensity).toBeGreaterThan(model.items[1].weightIntensity);
    expect(model.items[0].borderWidth).toBeGreaterThan(model.items[1].borderWidth);
  });
});
