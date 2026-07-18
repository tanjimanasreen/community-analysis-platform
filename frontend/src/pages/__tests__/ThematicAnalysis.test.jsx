import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ThematicAnalysisPage from '../ThematicAnalysis';
import { useThematicAnalysisData } from '../../features/topics/useThematicAnalysisData';
import { DashboardApiError } from '../../api/errors';

vi.mock('../../features/topics/useThematicAnalysisData', () => ({
  useThematicAnalysisData: vi.fn(),
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
  weighted_community: 2,
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
  weighted_community: 2,
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

function defaultData() {
  return {
    selectedRunId: 'run-1',
    overviewQuery: query({ matched_percentage: 75, model_metadata: { similarity_model: 'sentence-model' } }),
    topicsQuery: query({ run_id: 'run-1', topic_type: 'matched', records: [topicRecord], total: 11, limit: 10, offset: 0 }),
    themesQuery: query({ run_id: 'run-1', records: [themeRecord], total: 9, limit: 8, offset: 0, provider_metadata: { configured_primary_provider: 'ollama', configured_primary_model: 'llama3' } }),
    themeSummaryQuery: query({ run_id: 'run-1', records: [themeRecord], total: 1, limit: 500, offset: 0, provider_metadata: null }),
    themeCatalogQuery: query({ run_id: 'run-1', records: [themeRecord], total: 1, limit: 500, offset: 0, provider_metadata: { configured_primary_provider: 'ollama' } }),
    similarityQuery: query({ run_id: 'run-1', matrix: [[1]], labels: ['Policy'], artifacts: [] }),
  };
}

function renderPage(entry = '/thematic?run=run-1&metric=if') {
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

  it('shows LDA evidence before downstream provider labels and preserves structural links', () => {
    renderPage();
    expect(screen.getByText('LDA topic records')).toBeInTheDocument();
    expect(screen.getAllByText('alpha').length).toBeGreaterThan(0);
    expect(screen.getByText('Downstream theme labels')).toBeInTheDocument();
    expect(screen.getAllByText('Policy').length).toBeGreaterThan(0);
    expect(screen.getByText('ollama')).toBeInTheDocument();
    expect(screen.queryByText('Personal Support')).not.toBeInTheDocument();
    const ifLink = screen.getAllByRole('link', { name: 'Open IF community' })[0];
    expect(ifLink).toHaveAttribute('href', expect.stringContaining('metric=if'));
    expect(ifLink).toHaveAttribute('href', expect.stringContaining('community=1'));
  });

  it('stores matched/partial, token, metric, month, and exact community controls in the URL', () => {
    renderPage();
    fireEvent.change(screen.getByLabelText('Topic record type'), { target: { value: 'partial' } });
    fireEvent.change(screen.getByLabelText('Token representation'), { target: { value: 'bigram' } });
    fireEvent.change(screen.getByLabelText('Semantic metric view'), { target: { value: 'wif' } });
    fireEvent.change(screen.getByLabelText('Theme month'), { target: { value: '03' } });
    fireEvent.change(screen.getByLabelText('Exact community ID'), { target: { value: '22' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
    const location = screen.getByTestId('location');
    expect(location).toHaveTextContent('topicType=partial');
    expect(location).toHaveTextContent('token=bigram');
    expect(location).toHaveTextContent('semanticMetric=wif');
    expect(location).toHaveTextContent('themeMonth=03');
    expect(location).toHaveTextContent('semanticCommunity=22');
  });

  it('keeps topic and theme pagination independent', () => {
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: 'Next topic records page' }));
    expect(useThematicAnalysisData).toHaveBeenLastCalledWith(expect.objectContaining({ topicOffset: 10, themeOffset: 0 }));
    fireEvent.click(screen.getByRole('button', { name: 'Next theme records page' }));
    expect(useThematicAnalysisData).toHaveBeenLastCalledWith(expect.objectContaining({ topicOffset: 10, themeOffset: 8 }));
  });


  it('renders manifest-listed theme-similarity image artifacts through download URLs', () => {
    useThematicAnalysisData.mockReturnValue({
      ...defaultData(),
      similarityQuery: query({
        run_id: 'run-1',
        matrix: null,
        labels: [],
        artifacts: [{ artifact_key: 'visualization_theme_similarity_general.png', media_type: 'image/png', path: 'reports/general.png' }],
      }),
    });
    renderPage();
    const link = screen.getByRole('link', { name: 'Open artifact' });
    expect(link).toHaveAttribute('href', expect.stringContaining('/runs/run-1/downloads/visualization_theme_similarity_general.png'));
    expect(screen.getByRole('img', { name: /Theme similarity artifact/ })).toBeInTheDocument();
  });

  it('renders explicit artifact-unavailable states instead of mock semantic data', () => {
    const unavailable = new DashboardApiError({ code: 'ARTIFACT_NOT_AVAILABLE', message: 'Missing artifact' });
    useThematicAnalysisData.mockReturnValue({
      ...defaultData(),
      topicsQuery: query(undefined, unavailable),
      themesQuery: query(undefined, unavailable),
      themeSummaryQuery: query(undefined, unavailable),
      similarityQuery: query(undefined, unavailable),
    });
    renderPage();
    expect(screen.getAllByText('Artifact not generated').length).toBeGreaterThanOrEqual(3);
    expect(screen.queryByText('Current Events')).not.toBeInTheDocument();
  });
});
