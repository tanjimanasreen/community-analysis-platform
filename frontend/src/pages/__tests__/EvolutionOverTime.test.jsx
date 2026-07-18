import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import EvolutionOverTimePage from '../EvolutionOverTime';
import { useEvolutionHistory } from '../../features/evolution/useEvolutionHistory';

vi.mock('../../features/evolution/useEvolutionHistory', () => ({ useEvolutionHistory: vi.fn() }));
vi.mock('../../components/charts/EvolutionChart', () => ({ default: ({ points, title }) => <div>{title}: {points.length} points</div> }));

const run = (id, date) => ({ run_id: id, status: 'completed', platform: 'twitter', content_type: 'reply', date_start: date, date_end: date, year: null, month: null, started_at: null, completed_at: null, artifact_count: 1 });
const overview = (id, users) => ({ run_id: id, platform: 'twitter', content_type: 'reply', date_start: null, date_end: null, total_users: users, total_messages: null, total_interactions: null, if_users: null, wif_users: null, if_messages: null, wif_messages: null, if_community_count: null, wif_community_count: null, matched_community_count: null, matched_percentage: null, persistent_community_count: null, top_themes: [], model_metadata: {}, config_metadata: {} });

describe('Evolution over time page', () => {
  beforeEach(() => {
    const runs = [run('a', '2017-03-01'), run('b', '2017-04-01')];
    useEvolutionHistory.mockReturnValue({
      selectedRun: runs[0], selectedRunDetail: null, metric: 'if', compatibleRuns: runs,
      history: [{ run: runs[0], overview: overview('a', null) }, { run: runs[1], overview: overview('b', 20) }],
      isLoading: false, errors: [], retry: vi.fn(),
    });
  });

  it('uses actual run dates and shows unavailable values without fixed 2024 data', () => {
    render(<MemoryRouter initialEntries={['/evolution?run=a&metric=if']}><EvolutionOverTimePage /></MemoryRouter>);
    expect(screen.getByText('Mar 1, 2017')).toBeInTheDocument();
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0);
    expect(screen.queryByText(/May 2024/)).not.toBeInTheDocument();
  });
});
