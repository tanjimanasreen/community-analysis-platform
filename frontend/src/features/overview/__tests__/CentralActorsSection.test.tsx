import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { CentralityLeadersResponse, NetworkResponse } from '../../../types/api';
import CentralActorsSection from '../CentralActorsSection';

const leaders: CentralityLeadersResponse = {
  run_id: 'run-1',
  metric: 'if',
  methodology_note: '',
  periods: [
    {
      period: '2017-01',
      spreader: {
        user_id: 'user-spreader-1', display_user_id: 'us••••••-1', centrality: 0.12,
        community_id: '17', community_assignment_status: 'available',
      },
      influencer: {
        user_id: 'user-influencer-1', display_user_id: 'us••••••-1', centrality: 0.29,
        community_id: '42', community_assignment_status: 'available',
      },
      average_in_degree_centrality: 0.01,
      average_out_degree_centrality: 0.01,
    },
    {
      period: '2017-02',
      spreader: {
        user_id: 'user-spreader-2', display_user_id: 'us••••••-2', centrality: 0.2,
        community_id: '9', community_assignment_status: 'available',
      },
      influencer: {
        user_id: 'user-influencer-2', display_user_id: 'us••••••-2', centrality: 0.4,
        community_id: null, community_assignment_status: 'unavailable',
      },
      average_in_degree_centrality: 0.02,
      average_out_degree_centrality: 0.02,
    },
  ],
};

const network: NetworkResponse = {
  run_id: 'run-1', metric: 'if', period: '2017-02', community_id: null,
  view: 'users', sampling_strategy: 'community_balanced',
  nodes: [{ id: 'user-spreader-2', community_ids: ['9'] }],
  edges: [], available_nodes: 10, available_edges: 20,
  returned_nodes: 1, returned_edges: 0, sampled: true,
  coverage: null,
};

describe('CentralActorsSection', () => {
  it('shows selected-month leaders, community assignments, and preview availability', () => {
    const inspect = vi.fn();
    const highlight = vi.fn();
    render(
      <CentralActorsSection
        leaders={leaders}
        selectedPeriod="2017-02"
        metric="if"
        network={network}
        isLoading={false}
        error={null}
        onRetry={vi.fn()}
        onSelectPeriod={vi.fn()}
        onInspectCommunity={inspect}
        onHighlightUser={highlight}
      />,
    );

    expect(screen.getByText('Top spreader')).toBeInTheDocument();
    expect(screen.getByText('In-degree centrality: 0.200')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Community 9' })).toBeInTheDocument();
    expect(screen.getByText('Community unavailable')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Highlight in graph/i }));
    expect(highlight).toHaveBeenCalledWith('user-spreader-2');
    fireEvent.click(screen.getByRole('button', { name: 'Community 9' }));
    expect(inspect).toHaveBeenCalledWith('9');
  });



  it('uses the monthly timeline to update the shared period', () => {
    const selectPeriod = vi.fn();
    render(
      <CentralActorsSection
        leaders={leaders}
        selectedPeriod="2017-02"
        metric="if"
        network={undefined}
        isLoading={false}
        error={null}
        onRetry={vi.fn()}
        onSelectPeriod={selectPeriod}
        onInspectCommunity={vi.fn()}
        onHighlightUser={vi.fn()}
      />,
    );

    fireEvent.click(screen.getAllByRole('button', { name: /Jan 2017/i })[0]);
    expect(selectPeriod).toHaveBeenCalledWith('2017-01');
  });
});
