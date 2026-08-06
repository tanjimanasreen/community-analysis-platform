import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import type { OverviewResponse, RunDetail, RunSummary, ThemesResponse, VerificationResponse } from '../../../types/api';
import RunConfigurationPanel from '../RunConfigurationPanel';
import RunProvenancePanel from '../RunProvenancePanel';
import TopThemesPanel from '../TopThemesPanel';

const overview: OverviewResponse = {
  run_id: '739866ba-8f59-4784-a083-d64888b24ffd',
  platform: 'twitter',
  content_type: 'retweet_quote',
  date_start: '2017-01-01',
  date_end: '2017-04-30',
  total_users: 175,
  total_messages: 1273,
  total_interactions: 5165736,
  if_users: 175,
  wif_users: 174,
  if_messages: 1273,
  wif_messages: 1268,
  if_community_count: 18,
  wif_community_count: 18,
  matched_community_count: 18,
  matched_percentage: 100,
  persistent_community_count: 6,
  available_periods: ['2017-01', '2017-02', '2017-03', '2017-04'],
  top_themes: [],
  model_metadata: {},
  config_metadata: {
    graph_thresholds: { min_total_post: 10, min_shared_post: 5, min_members: 3 },
    louvain: { resolution: 1, seed: 123 },
    lda: { num_topics: 15, passes: 80, alpha: 'auto', eta: 'auto' },
    theme: { provider: 'openai:gpt-5-nano', render_visuals: false },
  },
};

const run: RunSummary = {
  run_id: overview.run_id,
  status: 'completed',
  platform: 'twitter',
  content_type: 'retweet_quote',
  date_start: null,
  date_end: null,
  year: 2017,
  month: null,
  started_at: '2026-07-24T13:42:32.717463+00:00',
  completed_at: '2026-07-24T14:12:20.548463+00:00',
  artifact_count: 93,
};

const detail: RunDetail = {
  run_id: overview.run_id,
  status: 'completed',
  dataset: { source_hash: 'd4b6002d879faf21b429d5ad14ca11891416d06195c4c68d7daaaaeab777c22f' },
  code: {
    git_commit: 'b07b1ece6cc9c3edb80020e6e36c42980f59a863',
    config_digest: 'ed606c5be5332dff0132965a53aa63a4a438e4846c7baa329ce252fefabf4031',
  },
  pipeline: {
    started_at: run.started_at,
    completed_at: run.completed_at,
    prefect_flow_run_id: 'c6d33ae2-d6de-4ca9-baec-087f71f74681',
  },
  artifact_count: 93,
  failure: null,
};

const verification: VerificationResponse = {
  run_id: overview.run_id,
  ok: true,
  status: 'valid',
  checked_artifacts: 93,
  error_code: null,
  error: null,
};

describe('Overview metadata panels', () => {
  it('groups safe analytical configuration and formats booleans', () => {
    render(
      <MemoryRouter>
        <RunConfigurationPanel overview={overview} metric="if" selectedRun={run} />
      </MemoryRouter>,
    );

    expect(screen.getByText('Minimum total posts')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('Louvain seed')).toBeInTheDocument();
    expect(screen.getByText('Number of topics')).toBeInTheDocument();
    expect(screen.getByText('No')).toBeInTheDocument();
    expect(screen.queryByText(/cache_path/i)).not.toBeInTheDocument();
  });

  it('formats identifiers, timestamps, duration, and verification provenance', () => {
    render(
      <RunProvenancePanel
        overview={overview}
        selectedRun={run}
        selectedRunDetail={detail}
        verification={verification}
      />,
    );

    expect(screen.getByText('93 artifacts verified')).toBeInTheDocument();
    expect(screen.getByText('29m 48s')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Copy Run ID' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Copy Git commit' })).toBeInTheDocument();
    expect(screen.getAllByText(/UTC$/).length).toBeGreaterThanOrEqual(2);
  });
});


const overviewWithThemes: OverviewResponse = {
  ...overview,
  top_themes: [
    { name: 'Immigration policy', count: 12 },
    { name: 'Public protest', count: 8 },
  ],
  model_metadata: {
    configured_primary_provider: 'openai',
    configured_primary_model: 'gpt-5-nano',
  },
};

describe('TopThemesPanel', () => {
  it('shows selected-month distinct community counts, percentages, and LDA keywords', () => {
    render(
      <MemoryRouter>
        <TopThemesPanel overview={overviewWithThemes} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Top Themes')).toBeInTheDocument();
    expect(screen.getByText('Immigration policy')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('openai')).toBeInTheDocument();
    expect(screen.getByText('gpt-5-nano')).toBeInTheDocument();
  });

  it('does not rank an incomplete monthly response', () => {
    render(
      <MemoryRouter>
        <TopThemesPanel overview={{ ...overviewWithThemes, top_themes: [] }} />
      </MemoryRouter>,
    );
    expect(screen.getByText('No theme summary available')).toBeInTheDocument();
    expect(screen.queryByText('Immigration policy')).not.toBeInTheDocument();
  });
});
