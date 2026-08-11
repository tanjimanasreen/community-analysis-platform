import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
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

  it('compresses the thesis framing while preserving all exact research questions and links', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: 'Methodology' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Research Aim' })).toBeInTheDocument();
    expect(screen.getAllByText('Structural').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Semantic').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Temporal').length).toBeGreaterThan(0);

    expect(screen.getByText('What is the impact of different user affinities on community detection?')).toBeInTheDocument();
    expect(screen.getByText('What topics do communities engage with?')).toBeInTheDocument();
    expect(screen.getByText('How do communities evolve over time?')).toBeInTheDocument();
    expect(screen.getByText('How do individuals migrate between communities?')).toBeInTheDocument();

    expect(screen.getByLabelText('RQ1: What is the impact of different user affinities on community detection?'))
      .toHaveAttribute('href', '/communities?run=run-1&metric=if');
    expect(screen.getByLabelText('RQ2: What topics do communities engage with?'))
      .toHaveAttribute('href', '/thematic?run=run-1&metric=if');
  });

  it('shows a shared foundation followed by structural, semantic, and temporal branches', () => {
    renderPage();

    const workflow = screen.getByRole('heading', { name: 'Methodological Workflow' }).closest('.panel');
    expect(workflow).not.toBeNull();
    const workflowText = workflow?.textContent ?? '';
    const foundationTitles = ['Platform Data', 'Interaction Network', 'IF / WIF', 'Louvain Communities'];
    let previousIndex = -1;
    foundationTitles.forEach((title) => {
      const nextIndex = workflowText.indexOf(title);
      expect(nextIndex).toBeGreaterThan(previousIndex);
      previousIndex = nextIndex;
    });

    const branches = screen.getByLabelText('Analytical branches');
    const branchText = branches.textContent ?? '';
    expect(branchText.indexOf('LDA')).toBeLessThan(branchText.indexOf('Topic keywords'));
    expect(branchText.indexOf('Topic keywords')).toBeLessThan(branchText.indexOf('Generated theme interpretation'));
    expect(within(branches).getByText('RQ1')).toBeInTheDocument();
    expect(within(branches).getByText('RQ2')).toBeInTheDocument();
    expect(within(branches).getByText('RQ3')).toBeInTheDocument();
    expect(within(branches).getByText('RQ4')).toBeInTheDocument();
    expect(screen.getByLabelText('Generated themes contribute to longitudinal theme similarity')).toBeInTheDocument();
    expect(screen.getByText(/LDA produces topic-keyword evidence first/)).toBeInTheDocument();
    expect(screen.queryByText('GPT-4')).not.toBeInTheDocument();
  });

  it('shows platform-specific network diagrams with Telegram forwarding and one shared projection', () => {
    renderPage();

    expect(screen.getByRole('tab', { name: 'Telegram' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('CREATED')).toBeInTheDocument();
    expect(screen.getByText('SENT_TO')).toBeInTheDocument();
    expect(screen.getByText('PRODUCED / ORIGINATED')).toBeInTheDocument();
    expect(screen.getByText('FORWARDED_BY')).toBeInTheDocument();
    expect(screen.getByText('FORWARDED_TO')).toBeInTheDocument();
    expect(screen.getByText('Forwarding user')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Twitter · Retweet/Quote' }));
    expect(screen.getByText('TWEETED')).toBeInTheDocument();
    expect(screen.getByText('RETWEETED_BY')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Twitter · Reply' }));
    expect(screen.getByText('REPLIED_BY')).toBeInTheDocument();
    expect(screen.getByText('REPLIED_TO')).toBeInTheDocument();
    expect(screen.getByText('Common analytical projection')).toBeInTheDocument();
    expect(screen.getByText('Creator')).toBeInTheDocument();
    expect(screen.getByText('Spreader')).toBeInTheDocument();
  });

  it('separates production implementation layers from the historical Neo4j thesis implementation', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: 'System Implementation' })).toBeInTheDocument();
    expect(screen.getByText('Data Sources')).toBeInTheDocument();
    expect(screen.getByText('Graph / Ingestion Boundary')).toBeInTheDocument();
    expect(screen.getByText('Analytical Pipelines')).toBeInTheDocument();
    expect(screen.getByText('Immutable Run Artifacts')).toBeInTheDocument();
    expect(screen.getByText('Read Layer')).toBeInTheDocument();
    expect(screen.getByText('Research Interface')).toBeInTheDocument();
    expect(screen.getByText(/Neo4j/)).toBeInTheDocument();
    expect(screen.getByText(/Memgraph Community Edition as the default local target/)).toBeInTheDocument();
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

  it('exposes exactly five logical methodology navigation sections', () => {
    renderPage();

    const jump = screen.getByLabelText('Jump to Methodology section');
    expect(within(jump).getAllByRole('option').map((option) => option.textContent)).toEqual([
      'Research Framing',
      'Workflow',
      'Network Models',
      'Implementation',
      'Reproducibility',
    ]);
    expect(screen.queryByRole('option', { name: 'Aim & Scope' })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Method → RQs' })).not.toBeInTheDocument();
  });
});
