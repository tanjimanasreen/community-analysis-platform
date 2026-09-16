import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CommunitiesPage from '../Communities';
import { useCommunitiesWorkspaceData } from '../../features/communities/useCommunitiesWorkspaceData';

vi.mock('../../features/communities/useCommunitiesWorkspaceData', () => ({ useCommunitiesWorkspaceData: vi.fn() }));
vi.mock('../../features/communities/CommunityMemberGraph', () => ({ default: ({ graph }) => <div data-testid="member-graph">{graph.returned_nodes} members</div> }));
vi.mock('../../components/PageNavigationRail', () => ({ PageNavigationRailSlot: ({ sections }) => <nav aria-label="test rail">{sections.map((section) => <span key={section.id}>{section.label}</span>)}</nav> }));

function query(data, error = null, isPending = false) {
  return { data, error, isPending, refetch: vi.fn() };
}

const overview = {
  run_id: 'run-1', available_periods: ['2017-03', '2017-04'],
  periods: [{ period: '2017-04', if_users: 12, wif_users: 11, if_messages: 30, wif_messages: 29, if_community_count: 2, wif_community_count: 2 }],
};
const communities = {
  run_id: 'run-1', metric: 'if', period: '2017-04', total: 2, limit: 15, offset: 0,
  communities: [
    { community_id: '7', node_count: 5, edge_count: 4, total_weight: 8, cross_community_neighbor_count: 1 },
    { community_id: '9', node_count: 3, edge_count: 2, total_weight: 3, cross_community_neighbor_count: 0 },
  ],
};
const graph = { run_id: 'run-1', metric: 'if', period: '2017-04', community_id: '7', view: 'users', nodes: [], edges: [], available_nodes: 5, available_edges: 4, returned_nodes: 5, returned_edges: 4, sampled: false };

function baseData(selectedCommunityId = null) {
  return {
    selectedRunId: 'run-1', metric: 'if', selectedPeriod: '2017-04', periods: ['2017-03', '2017-04'],
    selectedPeriodSummary: overview.periods[0], selectedCommunityId,
    setSelectedPeriod: vi.fn(), selectCommunity: vi.fn(), clearCommunity: vi.fn(),
    overviewQuery: query(overview), communitiesQuery: query(communities), detailQuery: query(undefined),
    communityContextQuery: query(undefined), topicsQuery: query({ records: [] }), themesQuery: query({ records: [], provider_metadata: null }),
  };
}

describe('Communities page', () => {
  beforeEach(() => useCommunitiesWorkspaceData.mockReturnValue(baseData()));

  it('presents a monthly directory rather than a page-local top ranking', () => {
    const data = baseData();
    useCommunitiesWorkspaceData.mockReturnValue(data);
    render(<MemoryRouter initialEntries={['/communities?run=run-1&metric=if&period=2017-04']}><CommunitiesPage /></MemoryRouter>);

    expect(screen.getByRole('heading', { name: 'Communities', level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Community Directory' })).toBeInTheDocument();
    expect(screen.queryByText('Page rank')).not.toBeInTheDocument();
    expect(screen.queryByText('Centrality artifact')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('C7'));
    expect(data.selectCommunity).toHaveBeenCalledWith('7');
  });

  it('uses one selected community to drive structure, member network, and LDA-before-theme preview', () => {
    const data = baseData('7');
    data.detailQuery = query({ run_id: 'run-1', metric: 'if', period: '2017-04', community: communities.communities[0], graph });
    data.communityContextQuery = query({
      edges: [{ source: '7', target: '9', weight: 5, user_pair_count: 2 }],
    });
    data.topicsQuery = query({ records: [{ absolute_community: '7', absolute_unigram_keywords: ['refugee', 'policy'] }] });
    data.themesQuery = query({ records: [{ absolute_community: '7', general_theme_names: ['Refugees and Immigration Policy'] }], provider_metadata: null });
    useCommunitiesWorkspaceData.mockReturnValue(data);

    render(<MemoryRouter initialEntries={['/communities?run=run-1&metric=if&period=2017-04&community=7']}><CommunitiesPage /></MemoryRouter>);

    expect(screen.getByRole('heading', { name: 'C7' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Member Interaction Network' })).toBeInTheDocument();
    expect(screen.getByTestId('member-graph')).toHaveTextContent('5 members');
    expect(screen.getByText(/does not rerun Louvain/)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'C9' }).length).toBeGreaterThan(0);

    const ldaHeading = screen.getByRole('heading', { name: 'LDA keywords' });
    const themeHeading = screen.getByRole('heading', { name: 'Downstream theme labels' });
    expect(ldaHeading.compareDocumentPosition(themeHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByRole('link', { name: /Explore full thematic evidence/ })).toHaveAttribute('href', expect.stringContaining('semanticCommunity=7'));
  });
});
