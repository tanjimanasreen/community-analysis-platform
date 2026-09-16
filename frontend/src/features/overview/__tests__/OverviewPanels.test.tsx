import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import type { MonthlyClusteredThemeResponse, OverviewResponse, RunDetail, RunSummary, VerificationResponse } from '../../../types/api';
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
  periods: [],
  run_summary: { interaction_records: 1273, persistent_community_count: 6, month_count: 4 },
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


const selectedMonthThemes: MonthlyClusteredThemeResponse = {
  run_id: overview.run_id,
  scope: 'matched',
  period: '2017-04',
  complete: true,
  source_observation_count: 3,
  excluded_records_missing_general_theme: 0,
  excluded_records_ambiguous_general_theme_serialization: 0,
  monthly_noise_observation_count: 0,
  total_themed_community_pairs: 2,
  distinct_clustered_theme_count: 2,
  embedding_provider: 'tei',
  embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
  monthly_cluster_contract_version: '1.0',
  canonicalization_contract_version: '1.0',
  themes: [
    {
      theme_id: 'ct_immigration',
      name: 'Immigration policy',
      community_count: 1,
      percentage: 50,
      keywords: ['immigration', 'ban'],
      monthly_cluster_ids: ['mc_1'],
      monthly_representative_themes: ['US Immigration Policy'],
      source_theme_labels: ['US Immigration Policy', 'Trump Immigration Policy'],
      community_pairs: [],
      mean_membership_probability: 0.9,
    },
    {
      theme_id: 'ct_protest',
      name: 'Public protest',
      community_count: 1,
      percentage: 50,
      keywords: ['protest', 'rights'],
      monthly_cluster_ids: ['mc_2'],
      monthly_representative_themes: ['Public protest'],
      source_theme_labels: ['Public protest'],
      community_pairs: [],
      mean_membership_probability: 0.95,
    },
  ],
};

describe('TopThemesPanel', () => {
  it('shows selected-month distinct pair counts, percentages, and LDA keywords', () => {
    render(
      <MemoryRouter>
        <TopThemesPanel period="2017-04" themes={selectedMonthThemes} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Top Themes · Apr 2017')).toBeInTheDocument();
    expect(screen.getByText('Immigration policy')).toBeInTheDocument();
    expect(screen.getAllByText('1 of 2 themed matched pairs')).toHaveLength(2);
    expect(screen.getAllByText('50.0%')).toHaveLength(2);
    expect(screen.getByText('immigration')).toBeInTheDocument();
  });

  it('bounds unusually long keyword evidence and reports ambiguous-source exclusions', () => {
    const longKeyword = 'community_led_cross_platform_public_accountability_discussion';
    const guarded = {
      ...selectedMonthThemes,
      excluded_records_ambiguous_general_theme_serialization: 1,
      themes: [
        {
          ...selectedMonthThemes.themes[0],
          name: 'Cross-platform civic discussion of public accountability and institutional response across multiple communities',
          keywords: [longKeyword],
        },
      ],
    };

    render(
      <MemoryRouter>
        <TopThemesPanel period="2017-04" themes={guarded} />
      </MemoryRouter>,
    );

    expect(screen.getByText(longKeyword)).toHaveClass('truncate', 'max-w-48');
    expect(screen.getByText(/1 matched source record contained an ambiguous legacy general-theme serialization/i)).toBeInTheDocument();
  });

  it('shows a safe empty state when no canonical themes are published', () => {
    render(
      <MemoryRouter>
        <TopThemesPanel period="2017-04" themes={{ ...selectedMonthThemes, themes: [], total_themed_community_pairs: 0 }} />
      </MemoryRouter>,
    );
    expect(screen.getByText('No clustered theme summary available')).toBeInTheDocument();
  });
});
