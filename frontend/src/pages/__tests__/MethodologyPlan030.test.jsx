import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MethodologyPage from '../Methodology';
import { useMethodologyData } from '../../features/methodology/useMethodologyData';

vi.mock('../../features/methodology/useMethodologyData', () => ({ useMethodologyData: vi.fn() }));

const query = (data) => ({ data, error: null, isPending: false });

function renderPage(route = '/methodology?run=run-1&metric=if') {
  return render(<MemoryRouter initialEntries={[route]}><MethodologyPage /></MemoryRouter>);
}

describe('Methodology page', () => {
  beforeEach(() => {
    useMethodologyData.mockReturnValue({
      selectedRunId: 'run-1',
      selectedRun: { run_id: 'run-1', status: 'completed', platform: 'telegram', content_type: 'forward', date_start: '2019-01-01', date_end: '2019-01-31', artifact_count: 1 },
      selectedRunDetail: { artifact_count: 1 },
      overviewQuery: query({ config_metadata: { louvain: { seed: 999 } }, model_metadata: { theme_provider: 'ollama', theme_model: 'llama3' } }),
      artifactsQuery: query({ artifacts: [{ category: 'data' }] }),
    });
  });

  it('leads with the thesis research narrative and exact research questions', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: 'Methodology' })).toBeInTheDocument();
    expect(screen.getAllByText('Structural').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Semantic').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Temporal').length).toBeGreaterThan(0);

    expect(screen.getByText('What is the impact of different user affinities on community detection?')).toBeInTheDocument();
    expect(screen.getByText('What topics do communities engage with?')).toBeInTheDocument();
    expect(screen.getByText('How do communities evolve over time?')).toBeInTheDocument();
    expect(screen.getByText('How do individuals migrate between communities?')).toBeInTheDocument();
  });

  it('keeps the workflow ordered and preserves LDA before downstream theme interpretation', () => {
    renderPage();

    const bodyText = document.body.textContent ?? '';
    const orderedTitles = [
      'Data Ingestion',
      'Interaction Network',
      'Community Extraction',
      'Structural Analysis',
      'Topic Modeling',
      'Theme Interpretation',
      'Longitudinal Analysis',
    ];
    let previousIndex = -1;
    orderedTitles.forEach((title) => {
      const nextIndex = bodyText.indexOf(title);
      expect(nextIndex).toBeGreaterThan(previousIndex);
      previousIndex = nextIndex;
    });
    expect(screen.getByText(/LDA produces topic-keyword evidence first/)).toBeInTheDocument();
    expect(screen.queryByText('GPT-4')).not.toBeInTheDocument();
  });

  it('shows platform-specific network models with one shared analytical projection', () => {
    renderPage();

    expect(screen.getByRole('tab', { name: 'Telegram' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('CREATED')).toBeInTheDocument();
    expect(screen.getByText('FORWARDED_BY')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Twitter · Retweet/Quote' }));
    expect(screen.getByText('RETWEETED_BY')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Twitter · Reply' }));
    expect(screen.getByText('REPLIED_TO')).toBeInTheDocument();
    expect(screen.getByText('REPLIED_BY')).toBeInTheDocument();
    expect(screen.getByText('Common analytical projection')).toBeInTheDocument();
    expect(screen.getByText('Creator')).toBeInTheDocument();
    expect(screen.getByText('Spreader')).toBeInTheDocument();
  });

  it('keeps thesis defaults separate from selected-run overrides and renders non-OpenAI metadata', () => {
    renderPage();

    fireEvent.click(screen.getByText('Thesis baseline & affinity definitions'));
    expect(screen.getByText('123')).toBeInTheDocument();
    expect(screen.getByText('Interaction Frequency (IF)')).toBeInTheDocument();
    expect(screen.getByText('Weighted Interaction Frequency (WIF)')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Selected run · resolved metadata'));
    expect(screen.getByText('999')).toBeInTheDocument();
    expect(screen.getByText('ollama')).toBeInTheDocument();
    expect(screen.getByText('llama3')).toBeInTheDocument();
    expect(screen.queryByText('GPT-4')).not.toBeInTheDocument();
  });

  it('preserves run search state in methodology links and exposes mobile section navigation', () => {
    renderPage();

    expect(screen.getByLabelText('RQ1: What is the impact of different user affinities on community detection?'))
      .toHaveAttribute('href', '/network?run=run-1&metric=if');
    expect(screen.getByLabelText('RQ2: What topics do communities engage with?'))
      .toHaveAttribute('href', '/thematic?run=run-1&metric=if');
    expect(screen.getByLabelText('Jump to Methodology section')).toBeInTheDocument();
  });
});
