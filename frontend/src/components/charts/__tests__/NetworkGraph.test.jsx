import React from 'react';
import { forwardRef } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import NetworkGraph from '../NetworkGraph';

vi.mock('react-force-graph-2d', () => ({
  default: forwardRef(function MockForceGraph({ graphData }, _ref) {
    return (
      <div data-testid="force-graph">
        {graphData.nodes.length} nodes / {graphData.links.length} links
      </div>
    );
  }),
}));

describe('NetworkGraph', () => {
  it('renders the bounded API graph and sampled counts', () => {
    render(
      <NetworkGraph
        metric="if"
        network={{
          run_id: 'run-1',
          metric: 'if',
          community_id: null,
          nodes: [
            { id: 'u1', community_ids: ['1'] },
            { id: 'u2', community_ids: ['1'] },
          ],
          edges: [{ source: 'u1', target: 'u2', community_id: '1', direction: 'out', weight: 2 }],
          available_nodes: 10,
          available_edges: 20,
          returned_nodes: 2,
          returned_edges: 1,
          sampled: true,
        }}
      />,
    );
    expect(screen.getByText('Sampled preview')).toBeInTheDocument();
    expect(screen.getByText(/2 \/ 10 nodes/)).toBeInTheDocument();
    expect(screen.getByTestId('force-graph')).toHaveTextContent('2 nodes / 1 links');
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
    expect(screen.getByText('No network edges available')).toBeInTheDocument();
    expect(screen.queryByTestId('force-graph')).not.toBeInTheDocument();
  });
});
