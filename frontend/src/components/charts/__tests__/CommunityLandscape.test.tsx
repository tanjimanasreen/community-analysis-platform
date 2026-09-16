import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import CommunityLandscape from '../CommunityLandscape';
import type { NetworkResponse } from '../../../types/api';

const network: NetworkResponse = {
  run_id: 'run-1',
  metric: 'if',
  period: '2017-02',
  community_id: null,
  view: 'communities',
  sampling_strategy: null,
  nodes: [
    { id: '2', community_ids: ['2'], node_type: 'community', community_id: '2', member_count: 25, internal_edge_count: 40, internal_weight: 250 },
    { id: '1', community_ids: ['1'], node_type: 'community', community_id: '1', member_count: 100, internal_edge_count: 200, internal_weight: 1000 },
  ],
  edges: [],
  available_nodes: 2,
  available_edges: 0,
  returned_nodes: 2,
  returned_edges: 0,
  sampled: false,
};

describe('CommunityLandscape', () => {
  it('renders every disconnected community with visible labels and independent encodings', () => {
    render(<CommunityLandscape network={network} metric="if" />);
    expect(screen.getByRole('button', { name: /C1\. Members: 100/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /C2\. Members: 25/ })).toBeInTheDocument();
    expect(screen.getByText('Relative area: members')).toBeInTheDocument();
    expect(screen.getByText('Fill intensity: total IF weight')).toBeInTheDocument();
    expect(screen.getByText('Border width: internal edges')).toBeInTheDocument();
    expect(screen.getByText('200')).toBeInTheDocument();
    expect(screen.getByText('1,000')).toBeInTheDocument();
  });

  it('supports keyboard-focus details and community drill-down', () => {
    const onSelectCommunity = vi.fn();
    const onInteraction = vi.fn();
    render(
      <CommunityLandscape
        network={network}
        metric="if"
        onSelectCommunity={onSelectCommunity}
        onInteraction={onInteraction}
      />,
    );
    const community = screen.getByRole('button', { name: /C2\. Members: 25/i });
    fireEvent.focus(community);
    expect(screen.getByText('Selected community')).toBeInTheDocument();
    expect(screen.getByText('40')).toBeInTheDocument();
    fireEvent.click(community);
    expect(onSelectCommunity).toHaveBeenCalledWith('2');
    expect(onInteraction).toHaveBeenCalled();
  });
});
