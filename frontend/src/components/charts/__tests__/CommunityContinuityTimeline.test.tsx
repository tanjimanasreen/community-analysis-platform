import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import CommunityContinuityTimeline from '../CommunityContinuityTimeline';
import type { TransitionsResponse } from '../../../types/api';

const transitions: TransitionsResponse = {
  run_id: 'run-1',
  total: 2,
  limit: 1000,
  offset: 0,
  records: [
    {
      start_month: '01', end_month: '02', start_month_community: 1, end_month_community: 2,
      jaccard_score: 0.75, common_members: ['u1', 'u2'], uncommon_members: null,
      start_month_members: null, total_start_month_members: 4,
      end_month_members: null, total_end_month_members: 5,
      start_month_absolute_theme: null, end_month_absolute_theme: null,
      start_month_weighted_theme: null, end_month_weighted_theme: null,
      start_month_general_theme: null, end_month_general_theme: null,
    },
    {
      start_month: '02', end_month: '03', start_month_community: 2, end_month_community: 3,
      jaccard_score: 0.6, common_members: ['u1'], uncommon_members: null,
      start_month_members: null, total_start_month_members: 5,
      end_month_members: null, total_end_month_members: 3,
      start_month_absolute_theme: null, end_month_absolute_theme: null,
      start_month_weighted_theme: null, end_month_weighted_theme: null,
      start_month_general_theme: null, end_month_general_theme: null,
    },
  ],
};

describe('CommunityContinuityTimeline', () => {
  it('renders readable month, community, member, and encoding labels', () => {
    render(
      <MemoryRouter>
        <CommunityContinuityTimeline transitions={transitions} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Community Continuity Timeline')).toBeInTheDocument();
    expect(screen.getByText('January')).toBeInTheDocument();
    expect(screen.getByText('February')).toBeInTheDocument();
    expect(screen.getByText('March')).toBeInTheDocument();
    expect(screen.getByText('C1')).toBeInTheDocument();
    expect(screen.getByText('C2')).toBeInTheDocument();
    expect(screen.getByText('Link width: retained members')).toBeInTheDocument();
    expect(screen.getByText('1 of 1 persistent paths displayed')).toBeInTheDocument();
  });

  it('exposes canonical link details on keyboard focus and stops playback interaction', () => {
    const onInteraction = vi.fn();
    render(
      <MemoryRouter>
        <CommunityContinuityTimeline transitions={transitions} onInteraction={onInteraction} />
      </MemoryRouter>,
    );
    const link = screen.getByRole('img', { name: /January community 1 to February community 2/i });
    fireEvent.focus(link);
    expect(screen.getByText(/Retained: 2.*Start: 4.*End: 5.*Jaccard: 0.750/i)).toBeInTheDocument();
    expect(onInteraction).toHaveBeenCalled();
  });

  it('refuses to rank incomplete transition pages', () => {
    render(
      <MemoryRouter>
        <CommunityContinuityTimeline transitions={{ ...transitions, total: 3 }} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Complete continuity summary unavailable')).toBeInTheDocument();
    expect(screen.queryByText('Path 1')).not.toBeInTheDocument();
  });
});
