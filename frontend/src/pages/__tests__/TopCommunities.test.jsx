import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TopCommunitiesPage from '../TopCommunities';
import { useCommunitiesPageData } from '../../features/communities/useCommunitiesPageData';

vi.mock('../../features/communities/useCommunitiesPageData', () => ({ useCommunitiesPageData: vi.fn() }));

function query(data, error = null) {
  return { data, error, isPending: false, refetch: vi.fn() };
}

describe('TopCommunities page', () => {
  beforeEach(() => {
    useCommunitiesPageData.mockReturnValue({
      selectedRunId: 'run-1', metric: 'wif',
      communitiesQuery: query({
        run_id: 'run-1', metric: 'wif', total: 2, limit: 15, offset: 0,
        communities: [
          { community_id: '9', node_count: 3, edge_count: 2, total_weight: 2 },
          { community_id: '2', node_count: 5, edge_count: 4, total_weight: 8 },
        ],
      }),
      detailQuery: query(undefined), topicsQuery: query({ records: [] }), themesQuery: query({ records: [] }),
    });
  });

  it('shows supported WIF fields and page-local sorting without mock communities', () => {
    render(<MemoryRouter initialEntries={['/top-communities?run=run-1&metric=wif']}><TopCommunitiesPage /></MemoryRouter>);
    expect(screen.getByText('WIF communities')).toBeInTheDocument();
    expect(screen.getByText(/Sorting applies to the loaded page only/)).toBeInTheDocument();
    expect(screen.queryByText('C-1124')).not.toBeInTheDocument();
    const rows = screen.getAllByRole('row');
    expect(rows[1]).toHaveTextContent('2');
    fireEvent.click(screen.getByRole('button', { name: /Community ID/ }));
    expect(screen.getAllByRole('row')[1]).toHaveTextContent('2');
  });
});
