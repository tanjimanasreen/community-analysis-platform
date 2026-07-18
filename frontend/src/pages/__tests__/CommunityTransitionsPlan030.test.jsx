import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DashboardApiError } from '../../api/errors';
import CommunityTransitionsPage from '../CommunityTransitions';
import { useTransitionData } from '../../features/evolution/useTransitionData';

vi.mock('../../features/evolution/useTransitionData', () => ({ useTransitionData: vi.fn() }));
vi.mock('../../components/charts/TransitionsSankey', () => ({ default: ({ records }) => <div>Real Sankey {records.length}</div> }));

const query = (data, error = null) => ({ data, error, isPending: false, refetch: vi.fn() });

describe('Community transitions page', () => {
  beforeEach(() => {
    const unavailable = new DashboardApiError({ code: 'ARTIFACT_NOT_AVAILABLE', message: 'optional' });
    useTransitionData.mockReturnValue({
      selectedRunId: 'run-1',
      transitionsQuery: query({ total: 1, records: [{ start_month: '03', end_month: '04', start_month_community: 1, end_month_community: 2, jaccard_score: 0.6, common_members: ['u1'], total_start_month_members: 2, total_end_month_members: 2 }] }),
      persistentQuery: query(undefined, unavailable),
      membershipQuery: query({ total: 1, records: [{ start_month: '03', end_month: '04', start_community: '1', end_community: '2', retained_count: 1, joined_count: 1, exited_count: 1, start_count: 2, end_count: 2 }] }),
      similarityQuery: query(undefined, unavailable),
    });
  });

  it('degrades optional panels independently and never invents reappearing counts', () => {
    render(<MemoryRouter><CommunityTransitionsPage /></MemoryRouter>);
    expect(screen.getByText('Real Sankey 1')).toBeInTheDocument();
    expect(screen.getAllByText('Artifact not generated').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('03:1 → 04:2')).toBeInTheDocument();
    expect(screen.queryByText(/reappearing/i)).not.toBeInTheDocument();
  });
});
