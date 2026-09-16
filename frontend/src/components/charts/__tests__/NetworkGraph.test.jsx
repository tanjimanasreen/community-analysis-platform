import React, { forwardRef } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import NetworkGraph from '../NetworkGraph';

vi.mock('react-force-graph-2d', () => ({
  default: forwardRef(function MockForceGraph({ graphData, onNodeClick }, _ref) {
    return (
      <div data-testid="force-graph">
        {graphData.nodes.length} nodes / {graphData.links.length} links
        <button type="button" onClick={() => onNodeClick?.(graphData.nodes[0])}>select node</button>
      </div>
    );
  }),
}));

const sampledNetwork = {
  run_id: 'run-1',
  metric: 'if',
  community_id: null,
  nodes: [
    { id: 'u1', community_ids: ['1', '2'] },
    { id: 'u2', community_ids: ['1'] },
  ],
  edges: [{ source: 'u1', target: 'u2', community_id: '1', direction: 'out', weight: 2 }],
  available_nodes: 10,
  available_edges: 20,
  returned_nodes: 2,
  returned_edges: 1,
  sampled: true,
};

describe('NetworkGraph', () => {
  it('renders the bounded API graph, sampled counts, and IF weight metadata', async () => {
    render(<NetworkGraph metric="if" network={sampledNetwork} />);
    expect(screen.getByText('Bounded response')).toBeInTheDocument();
    expect(screen.getByText(/2 \/ 10 users/)).toBeInTheDocument();
    expect(screen.getAllByText(/interaction frequency \(if\) edge weight/i).length).toBeGreaterThan(0);
    expect(await screen.findByTestId('force-graph')).toHaveTextContent('2 nodes / 1 links');
  });

  it('shows a chooser when a node belongs to multiple communities', async () => {
    const onSelectCommunity = vi.fn();
    render(<NetworkGraph metric="if" network={sampledNetwork} onSelectCommunity={onSelectCommunity} />);
    fireEvent.click(await screen.findByRole('button', { name: 'select node' }));
    expect(screen.getByText('Choose a community')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '2' }));
    expect(onSelectCommunity).toHaveBeenCalledWith('2');
  });

  it('shows an explicit empty graph state instead of generated fallback nodes', () => {
    render(
      <NetworkGraph
        metric="wif"
        network={{
          run_id: 'run-1', metric: 'wif', community_id: null,
          nodes: [], edges: [], available_nodes: 0, available_edges: 0,
          returned_nodes: 0, returned_edges: 0, sampled: false,
        }}
      />,
    );
    expect(screen.getByText('No network nodes available')).toBeInTheDocument();
    expect(screen.queryByTestId('force-graph')).not.toBeInTheDocument();
  });

  it('keeps a fixed graph stage height and reports malformed edges without growing from observed height', async () => {
    render(
      <NetworkGraph
        metric="if"
        height={500}
        network={{
          ...sampledNetwork,
          edges: [
            ...sampledNetwork.edges,
            { source: 'missing', target: 'u2', community_id: '1', direction: 'out', weight: 1 },
          ],
          returned_edges: 2,
        }}
      />,
    );
    const stage = screen.getByTestId('network-graph-stage');
    expect(stage).toHaveStyle({ height: '500px' });
    expect(screen.getByText(/1 malformed edge was omitted/i)).toBeInTheDocument();
    expect(await screen.findByTestId('force-graph')).toHaveTextContent('2 nodes / 1 links');
  });

  it('renders the prominent community interaction network and opens the selected community', async () => {
    const onSelectCommunity = vi.fn();
    render(
      <NetworkGraph
        metric="if"
        periodLabel="February 2017"
        onSelectCommunity={onSelectCommunity}
        network={{
          run_id: 'run-1', metric: 'if', period: '2017-02', community_id: null,
          view: 'communities', sampling_strategy: null,
          nodes: [
            {
              id: '17', community_ids: ['17'], node_type: 'community', community_id: '17',
              member_count: 612, internal_edge_count: 1108, internal_weight: 25104,
              cross_community_neighbor_count: 1,
            },
            {
              id: '22', community_ids: ['22'], node_type: 'community', community_id: '22',
              member_count: 80, internal_edge_count: 140, internal_weight: 820,
              cross_community_neighbor_count: 1,
            },
          ],
          edges: [
            { source: '17', target: '22', community_id: null, direction: 'Directed', weight: 8, user_pair_count: 3 },
            { source: '22', target: '17', community_id: null, direction: 'Directed', weight: 2, user_pair_count: 1 },
          ],
          available_nodes: 2, available_edges: 2,
          returned_nodes: 2, returned_edges: 2, sampled: false,
          coverage: {
            is_complete: true, scope: 'prominent_community_interaction_network', completeness_reason: null,
            available_users: 692, represented_users: 692,
            available_edges: 2, represented_edges: 2,
            available_communities: 2, represented_communities: 2,
            available_weight: 10, represented_weight: 10,
            weight_coverage_ratio: 1, cross_community_edges_available: true,
          },
          sampling: null,
        }}
      />,
    );
    expect(screen.getByText(/Prominent Community Network · February 2017 · IF/)).toBeInTheDocument();
    expect(screen.getByText('Complete prominent partition')).toBeInTheDocument();
    expect(screen.getByText(/one node per prominent community/i)).toBeInTheDocument();
    expect(await screen.findByTestId('force-graph')).toHaveTextContent('2 nodes / 1 links');
    fireEvent.click(screen.getByRole('button', { name: 'select node' }));
    expect(onSelectCommunity).toHaveBeenCalledWith('17');
  });

  it('keeps legacy prominent communities visible without fabricating links', async () => {
    render(
      <NetworkGraph
        metric="if"
        network={{
          run_id: 'legacy', metric: 'if', period: '2017-02', community_id: null,
          view: 'communities', nodes: [
            { id: '17', community_ids: ['17'], node_type: 'community', community_id: '17', member_count: 12 },
          ], edges: [], available_nodes: 1, available_edges: 0,
          returned_nodes: 1, returned_edges: 0, sampled: false,
          coverage: {
            is_complete: true, scope: 'prominent_community_interaction_network', completeness_reason: 'cross_community_artifact_unavailable',
            available_users: 12, represented_users: 12, available_edges: 0, represented_edges: 0,
            available_communities: 1, represented_communities: 1, available_weight: 0, represented_weight: 0,
            weight_coverage_ratio: null, cross_community_edges_available: false,
            cross_community_edges_reason: 'cross_community_artifact_unavailable',
          },
        }}
      />,
    );
    expect(screen.getByText('Legacy nodes-only view')).toBeInTheDocument();
    expect(screen.getByText(/no links were fabricated/i)).toBeInTheDocument();
    expect(await screen.findByTestId('force-graph')).toHaveTextContent('1 nodes / 0 links');
  });

});
