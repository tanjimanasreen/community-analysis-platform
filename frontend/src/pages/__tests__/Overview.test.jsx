import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Overview from '../Overview';
import { useOverviewData } from '../../features/overview/useOverviewData';

vi.mock('../../features/overview/useOverviewData', () => ({
  useOverviewData: vi.fn(),
}));
vi.mock('../../components/charts/NetworkGraph', () => ({
  default: ({ network }) => <div>{network?.sampled ? 'Sampled graph' : 'Empty graph'}</div>,
}));

describe('Overview page', () => {
  beforeEach(() => {
    useOverviewData.mockReturnValue({
      selectedRunId: 'run-empty',
      selectedRun: {
        run_id: 'run-empty', status: 'completed', platform: 'twitter', content_type: 'reply',
        date_start: '2017-03-01', date_end: '2017-03-31', artifact_count: 3,
      },
      selectedRunDetail: {
        run_id: 'run-empty', status: 'completed', dataset: {}, code: {}, pipeline: {}, artifact_count: 3,
      },
      metric: 'if',
      selectedPeriod: '2017-03',
      setSelectedPeriod: vi.fn(),
      networkView: 'communities',
      samplingStrategy: 'community_balanced',
      selectedCommunityId: null,
      setNetworkView: vi.fn(),
      setSamplingStrategy: vi.fn(),
      inspectCommunity: vi.fn(),
      clearCommunity: vi.fn(),
      overviewQuery: {
        isPending: false,
        error: null,
        data: {
          run_id: 'run-empty', platform: 'twitter', content_type: 'reply',
          date_start: '2017-03-01', date_end: '2017-03-31',
          total_users: null, total_messages: null, total_interactions: null,
          if_users: null, wif_users: null, if_messages: null, wif_messages: null,
          if_community_count: null, wif_community_count: null,
          matched_community_count: null, matched_percentage: null,
          persistent_community_count: null,
          available_periods: ['2017-03'],
          periods: [{
            period: '2017-03', if_users: null, wif_users: null,
            if_messages: null, wif_messages: null, interaction_records: null,
            if_community_count: null, wif_community_count: null,
            matched_community_count: null, matched_percentage: null,
          }],
          run_summary: { interaction_records: null, persistent_community_count: null, month_count: 1 },
          top_themes: [], model_metadata: {}, config_metadata: {},
        },
      },
      networkQuery: { isPending: false, error: null, data: undefined, refetch: vi.fn() },
      centralityLeadersQuery: {
        isPending: false, error: null,
        data: { run_id: 'run-empty', metric: 'if', periods: [], methodology_note: '' },
        refetch: vi.fn(),
      },
      communitiesQuery: {
        isPending: false, error: null,
        data: { run_id: 'run-empty', metric: 'if', communities: [], total: 0, limit: 5, offset: 0 },
        refetch: vi.fn(),
      },
      artifactsQuery: { isPending: false, error: null, data: { artifacts: [] }, refetch: vi.fn() },
      themesQuery: { isPending: false, error: null, data: { run_id: 'run-empty', records: [], total: 0, limit: 500, offset: 0, provider_metadata: null }, refetch: vi.fn() },
      themeClustersQuery: { isPending: false, error: null, data: { run_id: 'run-empty', scope: 'matched', period: '2017-03', complete: true, source_observation_count: 0, excluded_records_missing_general_theme: 0, excluded_records_ambiguous_general_theme_serialization: 0, monthly_noise_observation_count: 0, total_themed_community_pairs: 0, distinct_clustered_theme_count: 0, themes: [], embedding_provider: null, embedding_model: null, monthly_cluster_contract_version: null, canonicalization_contract_version: null }, refetch: vi.fn() },
      transitionsQuery: { isPending: false, error: null, data: undefined, refetch: vi.fn() },
      history: [],
      hasThemes: true,
      hasThemeClusters: true,
      hasTransitions: false,
      retryOverview: vi.fn(),
    });
  });

  it('renders unavailable and empty states without mock analytical fallbacks', () => {
    render(
      <MemoryRouter initialEntries={['/?run=run-empty&metric=if']}>
        <Overview />
      </MemoryRouter>,
    );
    expect(screen.getAllByText('Unavailable for this run').length).toBeGreaterThan(0);
    expect(screen.getByText('No communities available')).toBeInTheDocument();
    expect(screen.getByText('Artifact not generated')).toBeInTheDocument();
    expect(screen.getByText('No clustered theme summary available')).toBeInTheDocument();
    expect(screen.queryByText('C-1124')).not.toBeInTheDocument();
    expect(screen.queryByText('May 1')).not.toBeInTheDocument();
    expect(screen.queryByText('Platforms: Both')).not.toBeInTheDocument();
  });
});
