import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ThematicAnalysisPage from '../ThematicAnalysis';
import { useThematicAnalysisData } from '../../features/topics/useThematicAnalysisData';
import { DashboardApiError } from '../../api/errors';

vi.mock('../../features/topics/useThematicAnalysisData', () => ({
  useThematicAnalysisData: vi.fn(),
}));
vi.mock('../../components/PageNavigationRail', () => ({
  PageNavigationRailSlot: ({ sections }) => <nav aria-label="Section rail">{sections.map((section) => <span key={section.id}>{section.label}</span>)}</nav>,
}));

function query(data, error = null) {
  return { data, error, isPending: false, refetch: vi.fn() };
}

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}{location.search}</div>;
}

const topicRecord = {
  absolute_community: 1,
  absolute_unigram_topic: 'if-topic',
  absolute_unigram_keywords: ['alpha', 'beta'],
  weighted_community: 11,
  weighted_unigram_topic: 'wif-topic',
  weighted_unigram_keywords: ['gamma'],
  absolute_bigram_topic: 'if-bigram',
  absolute_bigram_keywords: ['alpha beta'],
  weighted_bigram_topic: 'wif-bigram',
  weighted_bigram_keywords: ['gamma delta'],
  members: ['u1', 'u2'],
  absolute_members: null,
  weighted_members: null,
  jaccard_score: 0.5,
  common_members: ['u1'],
  uncommon_members: ['u2'],
};

const themeRecord = {
  month: '03',
  absolute_community: 1,
  absolute_unigram_topic: 'if-topic',
  absolute_unigram_keywords: ['alpha'],
  weighted_community: 11,
  weighted_unigram_topic: 'wif-topic',
  weighted_unigram_keywords: ['gamma'],
  absolute_bigram_topic: null,
  absolute_bigram_keywords: null,
  weighted_bigram_topic: null,
  weighted_bigram_keywords: null,
  members: ['u1'],
  general_theme_gpt: { Policy: ['alpha'] },
  general_theme_names: ['Policy'],
  absolute_theme_gpt: { Civic: ['alpha'] },
  absolute_theme_names: ['Civic'],
  weighted_theme_gpt: { Law: ['gamma'] },
  weighted_theme_names: ['Law'],
  all_keywords: ['alpha', 'gamma'],
  absolute_keywords: ['alpha'],
  weighted_keywords: ['gamma'],
};

const monthlySummaries = [
  {
    period: '2017-01', source_observation_count: 5, excluded_records_missing_general_theme: 0,
    excluded_records_ambiguous_general_theme_serialization: 0,
    total_themed_community_pairs: 5, distinct_clustered_theme_count: 5,
    themes: [
      theme('Policy', 5, 100, ['ban', 'court']),
      theme('Inclusion', 4, 80, ['heartland']),
      theme('Travel Ban', 3, 60, ['travel']),
      theme('Protest', 2, 40, ['march']),
      theme('Refugees', 1, 20, ['refugee']),
    ],
  },
  {
    period: '2017-02', source_observation_count: 6, excluded_records_missing_general_theme: 0,
    excluded_records_ambiguous_general_theme_serialization: 0,
    total_themed_community_pairs: 6, distinct_clustered_theme_count: 5,
    themes: [
      theme('Policy', 6, 100, ['appeal', 'judge']),
      theme('Activism', 4, 66.7, ['protest']),
      theme('Travel Ban', 3, 50, ['court']),
      theme('Legal Challenges', 2, 33.3, ['federal']),
      theme('Refugees', 1, 16.7, ['welcome']),
    ],
  },
  {
    period: '2017-03', source_observation_count: 4, excluded_records_missing_general_theme: 0,
    excluded_records_ambiguous_general_theme_serialization: 0,
    total_themed_community_pairs: 4, distinct_clustered_theme_count: 4,
    themes: [
      theme('Policy', 4, 100, ['alpha', 'court']),
      theme('Activism', 2, 50, ['rally']),
      theme('Legal Challenges', 2, 50, ['hawaii']),
      theme('Media', 1, 25, ['radio']),
    ],
  },
  {
    period: '2017-04', source_observation_count: 2, excluded_records_missing_general_theme: 0,
    excluded_records_ambiguous_general_theme_serialization: 0,
    total_themed_community_pairs: 2, distinct_clustered_theme_count: 3,
    themes: [
      theme('Activism', 2, 100, ['rights', 'petition']),
      theme('Refugees', 1, 50, ['solidarity']),
      theme('Policy', 1, 50, ['immigration']),
    ],
  },
];

function theme(name, communityCount, percentage, keywords) {
  const themeId = `ct_${name.toLowerCase().replace(/[^a-z0-9]+/g, '_')}`;
  return {
    theme_id: themeId,
    name,
    community_count: communityCount,
    percentage,
    keywords,
    monthly_cluster_ids: [`mc_${themeId}`],
    monthly_representative_themes: [name],
    source_theme_labels: [name],
    community_pairs: [{ absolute_community: '1', weighted_community: '11', source_labels: [name], keywords }],
    mean_membership_probability: 0.9,
  };
}

function defaultData() {
  return {
    selectedRunId: 'run-1',
    overviewQuery: query({
      available_periods: ['2017-01', '2017-02', '2017-03', '2017-04'],
      matched_percentage: 75,
      model_metadata: { theme_model: 'llama3' },
    }),
    topicsQuery: query({ run_id: 'run-1', topic_type: 'matched', records: [topicRecord], total: 11, limit: 10, offset: 0 }),
    themesQuery: query({ run_id: 'run-1', records: [themeRecord], total: 9, limit: 8, offset: 0, provider_metadata: { configured_primary_provider: 'ollama', configured_primary_model: 'llama3' } }),
    clusterEvidenceQuery: query({
      run_id: 'run-1', period: '2017-03', canonical_theme_id: 'ct_policy', total: 1, limit: 8, offset: 0,
      records: [{
        period: '2017-03', canonical_theme_id: 'ct_policy', canonical_theme_label: 'Policy',
        monthly_cluster_id: 'mc_policy', monthly_representative_theme: 'Policy',
        source_general_theme_label: 'US Immigration Policy', absolute_community: '1', weighted_community: '11',
        keywords: ['alpha', 'court'], membership_probability: 0.9,
      }],
    }),
    timelineQuery: query({
      run_id: 'run-1', scope: 'matched',
      available_periods: monthlySummaries.map((summary) => summary.period),
      periods: monthlySummaries.map((summary) => summary.period),
      complete: true,
      source_observation_count: 17,
      excluded_records_missing_general_theme: 0,
      excluded_records_ambiguous_general_theme_serialization: 0,
      monthly_summaries: monthlySummaries,
      most_discussed_theme: {
        theme_id: 'ct_policy', name: 'Policy', total_community_month_count: 16, months_present: 4,
        peak_period: '2017-02', peak_month_count: 6, keywords: ['ban', 'court'],
        series: [
          { period: '2017-01', community_count: 5, total_themed_community_pairs: 5, percentage: 100 },
          { period: '2017-02', community_count: 6, total_themed_community_pairs: 6, percentage: 100 },
          { period: '2017-03', community_count: 4, total_themed_community_pairs: 4, percentage: 100 },
          { period: '2017-04', community_count: 1, total_themed_community_pairs: 2, percentage: 50 },
        ],
      },
    }),
  };
}

function renderPage(entry = '/thematic?run=run-1&metric=if&themeMonth=2017-03&themeStart=2017-01&themeEnd=2017-04') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/thematic" element={<><ThematicAnalysisPage /><LocationProbe /></>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Thematic Analysis page', () => {
  beforeEach(() => {
    useThematicAnalysisData.mockImplementation(() => defaultData());
  });

  it('shows every monthly top-five summary, aggregate progression, and matched evidence', () => {
    renderPage();
    expect(screen.getByText('Top Themes by Month')).toBeInTheDocument();
    const matrix = screen.getByText('Top Themes by Month').closest('section');
    expect(within(matrix).getByText('Jan 2017')).toBeInTheDocument();
    expect(within(matrix).getByText('Feb 2017')).toBeInTheDocument();
    expect(within(matrix).getByText('Mar 2017')).toBeInTheDocument();
    expect(within(matrix).getByText('Apr 2017')).toBeInTheDocument();
    expect(within(matrix).getAllByText('court').length).toBeGreaterThan(0);
    expect(screen.getByText('Aggregate Theme Progression')).toBeInTheDocument();
    expect(screen.getByText('Up to 5 per month')).toBeInTheDocument();
    expect(screen.getByText('Up to 5 themes per month')).toBeInTheDocument();
    expect(screen.getByText('Evidence · Matched LDA topic records')).toBeInTheDocument();
    expect(screen.getByText('Evidence · Generated theme labels')).toBeInTheDocument();
    expect(screen.getByText('ollama')).toBeInTheDocument();
  });


  it('explains the thematic derivation before results and exposes section navigation', () => {
    renderPage();

    const bodyText = document.body.textContent ?? '';
    expect(bodyText.indexOf('How these results are derived')).toBeLessThan(bodyText.indexOf('Timeline scope'));
    expect(screen.getByText('LDA Topic Extraction')).toBeInTheDocument();
    expect(screen.getByText('HDBSCAN Canonicalization')).toBeInTheDocument();
    expect(screen.getByText(/all-MiniLM-L6-v2/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /View full methodology/i })).toHaveAttribute('href', expect.stringContaining('/methodology?'));
    expect(screen.getByLabelText('Jump to Thematic Analysis section')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Section rail' })).toBeInTheDocument();

    [
      'thematic-methodology',
      'thematic-overview',
      'thematic-monthly-themes',
      'thematic-progression',
      'thematic-canonical-evidence',
      'thematic-evidence-explorer',
      'thematic-theme-labels',
      'thematic-lda-evidence',
      'thematic-provenance',
    ].forEach((id) => expect(document.getElementById(id)).toBeInTheDocument());
  });

  it('separates selected canonical-cluster evidence from the source-record browser', () => {
    renderPage();
    const bodyText = document.body.textContent ?? '';
    const progressionIndex = bodyText.indexOf('Aggregate Theme Progression');
    const canonicalIndex = bodyText.indexOf('Selected Canonical Theme · Cluster Evidence');
    const explorerIndex = bodyText.indexOf('Source Evidence Explorer');
    const labelsIndex = bodyText.indexOf('Evidence · Generated theme labels');
    const ldaIndex = bodyText.indexOf('Evidence · Matched LDA topic records');
    const provenanceIndex = bodyText.indexOf('Theme provider and model provenance');

    expect(canonicalIndex).toBeGreaterThan(progressionIndex);
    expect(explorerIndex).toBeGreaterThan(canonicalIndex);
    expect(labelsIndex).toBeGreaterThan(explorerIndex);
    expect(ldaIndex).toBeGreaterThan(labelsIndex);
    expect(provenanceIndex).toBeGreaterThan(ldaIndex);
    expect(screen.getByText(/controls do not change monthly rankings, aggregate progression, or the complete selected canonical-cluster evidence/i)).toBeInTheDocument();
  });

  it('contains long valid canonical labels and keyword evidence without hiding the full text', () => {
    const longName = 'Cross-platform civic discussion of public accountability and institutional response across multiple communities';
    const longKeyword = 'community_led_cross_platform_public_accountability_discussion';
    const data = defaultData();
    const monthly = data.timelineQuery.data.monthly_summaries.map((summary) =>
      summary.period === '2017-03'
        ? {
            ...summary,
            excluded_records_ambiguous_general_theme_serialization: 1,
            themes: [theme(longName, 1, 25, [longKeyword]), ...summary.themes],
          }
        : summary,
    );
    data.timelineQuery = query({
      ...data.timelineQuery.data,
      excluded_records_ambiguous_general_theme_serialization: 1,
      monthly_summaries: monthly,
    });
    useThematicAnalysisData.mockReturnValue(data);

    renderPage();

    const matrix = screen.getByText('Top Themes by Month').closest('section');
    expect(within(matrix).getByText(longName)).toHaveClass('line-clamp-3');
    expect(within(matrix).getByText(longKeyword)).toHaveClass('truncate', 'max-w-48');
    expect(within(matrix).getByText(/1 matched source record contained an ambiguous legacy general-theme serialization/i)).toBeInTheDocument();
  });

  it('does not show persisted-community, transition, retention, or theme-similarity content', () => {
    renderPage();
    expect(screen.queryByText(/Persistent paths/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Theme Progression Across Persistent Communities/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Selected path evidence/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/retained members/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Saved theme similarity/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Open Community Transitions/i })).not.toBeInTheDocument();
  });

  it('keeps token representation inside LDA evidence and source filters outside canonical evidence', () => {
    renderPage();

    const explorer = document.getElementById('thematic-evidence-explorer');
    const canonical = document.getElementById('thematic-canonical-evidence');
    const lda = document.getElementById('thematic-lda-evidence');

    expect(within(explorer).getByLabelText('Evidence month')).toBeInTheDocument();
    expect(within(explorer).getByLabelText('Exact community ID')).toBeInTheDocument();
    expect(within(explorer).getByLabelText('IF/WIF evidence view')).toBeInTheDocument();
    expect(within(explorer).queryByLabelText('Token representation')).not.toBeInTheDocument();
    expect(within(canonical).queryByLabelText('Exact community ID')).not.toBeInTheDocument();
    expect(within(lda).getByLabelText('Token representation')).toBeInTheDocument();
  });

  it('clears period-specific canonical selection when the source evidence month changes', () => {
    renderPage('/thematic?run=run-1&themeMonth=2017-03&canonicalTheme=ct_policy');
    expect(screen.getByRole('button', { name: /Policy.*clear/i })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Evidence month'), { target: { value: '2017-04' } });

    const location = screen.getByTestId('location');
    expect(location).toHaveTextContent('themeMonth=2017-04');
    expect(location).not.toHaveTextContent('canonicalTheme=');
  });

  it('canonicalizes this route to matched evidence and removes obsolete path state', async () => {
    renderPage('/thematic?run=run-1&topicType=partial&themePath=legacy-path&themeMonth=2017-03');
    await waitFor(() => {
      expect(screen.getByTestId('location')).toHaveTextContent('topicType=matched');
      expect(screen.getByTestId('location')).not.toHaveTextContent('themePath=');
    });
    expect(screen.queryByLabelText('Topic record type')).not.toBeInTheDocument();
    expect(useThematicAnalysisData.mock.calls.at(-1)[0]).not.toHaveProperty('topicType');
  });

  it('stores timeline and evidence controls in the URL without changing aggregate scope', () => {
    renderPage();
    fireEvent.change(screen.getByLabelText('Token representation'), { target: { value: 'combined' } });
    fireEvent.change(screen.getByLabelText('IF/WIF evidence view'), { target: { value: 'wif' } });
    fireEvent.change(screen.getByLabelText('Theme timeline start'), { target: { value: '2017-02' } });
    fireEvent.change(screen.getByLabelText('Theme timeline end'), { target: { value: '2017-04' } });
    fireEvent.change(screen.getByLabelText('Exact community ID'), { target: { value: '22' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    const matrix = screen.getByText('Top Themes by Month').closest('section');
    fireEvent.click(within(matrix).getByRole('button', { name: /Activism.*2 of 2 themed matched pairs/i }));

    const location = screen.getByTestId('location');
    expect(location).toHaveTextContent('topicType=matched');
    expect(location).toHaveTextContent('token=combined');
    expect(location).toHaveTextContent('semanticMetric=wif');
    expect(location).toHaveTextContent('themeMonth=2017-04');
    expect(location).toHaveTextContent('themeStart=2017-02');
    expect(location).toHaveTextContent('themeEnd=2017-04');
    expect(location).toHaveTextContent('semanticCommunity=22');
    expect(location).toHaveTextContent('canonicalTheme=ct_activism');
    expect(within(matrix).getByText('Jan 2017')).toBeInTheDocument();
  });

  it('selects monthly theme evidence and keeps topic/theme pagination independent', () => {
    renderPage();
    const matrix = screen.getByText('Top Themes by Month').closest('section');
    fireEvent.click(within(matrix).getByRole('button', { name: /Policy.*4 of 4 themed matched pairs/i }));
    expect(screen.getByRole('button', { name: /Policy.*clear/i })).toBeInTheDocument();
    expect(screen.getByLabelText('Evidence month')).toHaveValue('2017-03');

    fireEvent.click(screen.getByRole('button', { name: 'Next topic records page' }));
    expect(useThematicAnalysisData).toHaveBeenLastCalledWith(expect.objectContaining({ topicOffset: 10, themeOffset: 0 }));
    fireEvent.click(screen.getByRole('button', { name: 'Next theme records page' }));
    expect(useThematicAnalysisData).toHaveBeenLastCalledWith(expect.objectContaining({ topicOffset: 10, themeOffset: 8 }));
  });

  it('allows the aggregate progression table to set the evidence month and canonical theme', () => {
    renderPage();
    const progression = screen.getByText('Aggregate Theme Progression').closest('section');
    const table = within(progression).getByRole('table');
    const aprilPolicyRow = within(table).getAllByRole('row').find((row) =>
      row.textContent?.includes('Policy') && row.textContent?.includes('Apr 2017'),
    );
    expect(aprilPolicyRow).toBeTruthy();
    fireEvent.click(within(aprilPolicyRow).getByRole('button', { name: 'Policy' }));
    expect(screen.getByLabelText('Evidence month')).toHaveValue('2017-04');
    expect(screen.getByRole('button', { name: /Policy.*clear/i })).toBeInTheDocument();
  });

  it('preserves run, evidence period, metric, and community IDs in network deep links', () => {
    renderPage();
    const topicLink = screen.getAllByRole('link', { name: 'Open IF community' })[0];
    expect(topicLink).toHaveAttribute('href', expect.stringContaining('run=run-1'));
    expect(topicLink).toHaveAttribute('href', expect.stringContaining('metric=if'));
    expect(topicLink).toHaveAttribute('href', expect.stringContaining('community=1'));
    expect(topicLink).toHaveAttribute('href', expect.stringContaining('period=2017-03'));
  });

  it('renders explicit artifact-unavailable states instead of fabricated semantic data', () => {
    const unavailable = new DashboardApiError({ code: 'ARTIFACT_NOT_AVAILABLE', message: 'Missing artifact' });
    useThematicAnalysisData.mockReturnValue({
      ...defaultData(),
      topicsQuery: query(undefined, unavailable),
      themesQuery: query(undefined, unavailable),
      timelineQuery: query(undefined, unavailable),
    });
    renderPage();
    expect(screen.getAllByText('Artifact not generated').length).toBeGreaterThanOrEqual(3);
    expect(screen.queryByText('Current Events')).not.toBeInTheDocument();
    expect(screen.queryByText('Aggregate Theme Progression')).not.toBeInTheDocument();
  });
});
