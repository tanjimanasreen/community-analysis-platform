import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MethodologyPage from '../Methodology';
import { useMethodologyData } from '../../features/methodology/useMethodologyData';

vi.mock('../../features/methodology/useMethodologyData', () => ({ useMethodologyData: vi.fn() }));

const query = (data) => ({ data, error: null, isPending: false });

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

  it('separates thesis defaults from selected-run overrides and renders non-OpenAI metadata', () => {
    render(<MemoryRouter initialEntries={['/methodology?run=run-1&metric=if']}><MethodologyPage /></MemoryRouter>);
    expect(screen.getByText('Thesis baseline and protected defaults')).toBeInTheDocument();
    expect(screen.getByText('123')).toBeInTheDocument();
    expect(screen.getByText('999')).toBeInTheDocument();
    expect(screen.getByText('ollama')).toBeInTheDocument();
    expect(screen.queryByText('GPT-4')).not.toBeInTheDocument();
    expect(screen.getByText(/LDA → theme labels/)).toBeInTheDocument();
  });
});
