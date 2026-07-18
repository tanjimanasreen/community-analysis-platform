import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ComparativeAnalysisPage from '../ComparativeAnalysis';
import { useComparisonData } from '../../features/comparison/useComparisonData';

vi.mock('../../features/comparison/useComparisonData', () => ({ useComparisonData: vi.fn() }));

const query = (data) => ({ data, error: null, isPending: false, fetchStatus: 'idle' });
const run = (id, platform, content) => ({ run_id: id, status: 'completed', platform, content_type: content, date_start: '2019-01-01', date_end: '2019-01-31', year: 2019, month: 1, started_at: null, completed_at: null, artifact_count: 1 });
const overview = (id, messages) => ({ run_id: id, platform: null, content_type: null, date_start: null, date_end: null, total_users: 10, total_messages: messages, total_interactions: 30, if_users: null, wif_users: null, if_messages: null, wif_messages: null, if_community_count: 4, wif_community_count: 5, matched_community_count: 3, matched_percentage: 75, persistent_community_count: 1, top_themes: [{ name: 'Policy', count: 2 }], model_metadata: { theme_provider: 'mock' }, config_metadata: {} });

describe('Comparative analysis page', () => {
  beforeEach(() => {
    const twitter = run('tw', 'twitter', 'reply');
    const telegram = run('tg', 'telegram', 'forward');
    useComparisonData.mockImplementation((twitterId, telegramId) => ({
      runs: [twitter, telegram], metric: 'if', isLoading: false,
      twitterOverview: query(twitterId ? overview('tw', 20) : undefined),
      telegramOverview: query(telegramId ? overview('tg', 15) : undefined),
      twitterDetail: query(twitterId ? { pipeline: {}, artifact_count: 1 } : undefined),
      telegramDetail: query(telegramId ? { pipeline: {}, artifact_count: 1 } : undefined),
      twitterArtifacts: query(twitterId ? { artifacts: [], total: 0 } : undefined),
      telegramArtifacts: query(telegramId ? { artifacts: [], total: 0 } : undefined),
    }));
  });

  it('requires explicit run selection and never shows a message-overlap Venn claim', () => {
    const { unmount } = render(<MemoryRouter initialEntries={['/comparative?metric=if']}><ComparativeAnalysisPage /></MemoryRouter>);
    expect(screen.getByText('Select both platform runs')).toBeInTheDocument();
    expect(screen.queryByText(/Shared Themes.*%/)).not.toBeInTheDocument();
    unmount();

    render(<MemoryRouter initialEntries={['/comparative?metric=if&twitterRun=tw&telegramRun=tg']}><ComparativeAnalysisPage /></MemoryRouter>);
    expect(screen.getByText('Supported overview fields')).toBeInTheDocument();
    expect(screen.getByText('Exact normalized theme-label overlap')).toBeInTheDocument();
    expect(screen.queryByText(/message-volume overlap/i)).toBeInTheDocument();
    expect(screen.queryByText('Thematic Diversity')).not.toBeInTheDocument();
  });
});
