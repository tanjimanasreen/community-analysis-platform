import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CommunityNetworkPage from '../CommunityNetwork';
import { useNetworkPageData } from '../../features/networks/useNetworkPageData';

vi.mock('../../features/networks/useNetworkPageData', () => ({ useNetworkPageData: vi.fn() }));
vi.mock('../../components/charts/NetworkGraph', () => ({
  default: ({ onSelectCommunity }) => <button type="button" onClick={() => onSelectCommunity('42')}>Select graph community</button>,
}));

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}{location.search}</div>;
}

function query(data, error = null) {
  return { data, error, isPending: false, refetch: vi.fn() };
}

const network = {
  run_id: 'run-1', metric: 'if', community_id: null,
  nodes: [{ id: 'u1', community_ids: ['1'] }, { id: 'u2', community_ids: ['1'] }],
  edges: [{ source: 'u1', target: 'u2', community_id: '1', direction: 'out', weight: 5 }],
  available_nodes: 20, available_edges: 30, returned_nodes: 2, returned_edges: 1, sampled: true,
};
const communities = {
  run_id: 'run-1', metric: 'if', communities: [{ community_id: '1', node_count: 2, edge_count: 1, total_weight: 5 }],
  total: 1, limit: 10, offset: 0,
};

function renderPage(entry) {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/network" element={<><CommunityNetworkPage /><LocationProbe /></>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CommunityNetwork page', () => {
  beforeEach(() => {
    useNetworkPageData.mockReturnValue({
      selectedRunId: 'run-1', metric: 'if',
      networkQuery: query(network),
      communitiesQuery: query(communities),
      centralityQuery: query({ run_id: 'run-1', artifact_key: 'user_centrality', records: [], total: 0, limit: 10, offset: 0 }),
      detailQuery: query(undefined),
      topicsQuery: query({ records: [] }),
      themesQuery: query({ records: [] }),
    });
  });

  it('renders canonical counts and selects a community through URL state', () => {
    renderPage('/network?run=run-1&metric=if');
    expect(screen.getByText('20')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
    expect(screen.queryByText('12,458')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Select graph community' }));
    expect(screen.getByTestId('location')).toHaveTextContent('community=42');
  });

  it('clears the selected community URL parameter from the detail rail', () => {
    useNetworkPageData.mockReturnValue({
      selectedRunId: 'run-1', metric: 'if',
      networkQuery: query(network), communitiesQuery: query(communities),
      centralityQuery: query({ run_id: 'run-1', artifact_key: 'user_centrality', records: [], total: 0, limit: 10, offset: 0 }),
      detailQuery: query({ run_id: 'run-1', metric: 'if', community: communities.communities[0], graph: network }),
      topicsQuery: query({ records: [] }), themesQuery: query({ records: [] }),
    });
    renderPage('/network?run=run-1&metric=if&community=1');
    fireEvent.click(screen.getByRole('button', { name: 'Clear selected community' }));
    expect(screen.getByTestId('location')).not.toHaveTextContent('community=');
  });
});
