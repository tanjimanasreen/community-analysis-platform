import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import Topbar from '../Topbar';

const runs = [
  {
    run_id: 'twitter-reply-2017-03-long-id',
    status: 'completed',
    platform: 'twitter',
    content_type: 'reply',
    date_start: '2017-03-01',
    date_end: '2017-03-31',
    year: 2017,
    month: 3,
    artifact_count: 9,
  },
  {
    run_id: 'telegram-forward-2019-01',
    status: 'completed',
    platform: 'telegram',
    content_type: 'forward',
    date_start: '2019-01-01',
    date_end: '2019-01-31',
    year: 2019,
    month: 1,
    artifact_count: 8,
  },
];

function renderTopbar(overrides = {}) {
  const props = {
    selectedRunId: runs[0].run_id,
    selectedRun: runs[0],
    runs,
    onRunChange: vi.fn(),
    metric: 'if',
    onMetricChange: vi.fn(),
    health: { status: 'ok', read_only: true, schema_version: '1' },
    verification: { run_id: runs[0].run_id, ok: true, status: 'valid', checked_artifacts: 9 },
    toggleSidebar: vi.fn(),
    ...overrides,
  };
  render(
    <MemoryRouter initialEntries={['/?run=twitter-reply-2017-03-long-id&metric=if']}>
      <Topbar {...props} />
    </MemoryRouter>,
  );
  return props;
}

describe('Topbar', () => {
  it('shows a concrete run selector and canonical IF/WIF labels', () => {
    renderTopbar();
    expect(screen.getByRole('option', { name: /twitter · reply · 2017-03-01 → 2017-03-31/ })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Interaction Frequency (IF)' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Weighted Interaction Frequency (WIF)' })).toBeInTheDocument();
    expect(screen.getByLabelText('API ok')).toBeInTheDocument();
    expect(screen.getByText('Run verified')).toBeInTheDocument();
  });

  it('changes the concrete run and metric without exposing inert controls', async () => {
    const user = userEvent.setup();
    const props = renderTopbar();
    await user.selectOptions(screen.getByLabelText('Analysis run'), runs[1].run_id);
    await user.selectOptions(screen.getByLabelText('Affinity metric'), 'wif');
    expect(props.onRunChange).toHaveBeenCalledWith(runs[1].run_id);
    expect(props.onMetricChange).toHaveBeenCalledWith('wif');
    expect(screen.queryByText('Platforms: Both')).not.toBeInTheDocument();
    expect(screen.queryByText('Export Report')).not.toBeInTheDocument();
    expect(screen.queryByText('Create Report')).not.toBeInTheDocument();
    expect(screen.queryByText('Filters')).not.toBeInTheDocument();
  });

  it('links Help to Methodology while preserving dashboard search state', () => {
    renderTopbar();
    expect(screen.getByRole('link', { name: 'Open methodology help' })).toHaveAttribute(
      'href',
      '/methodology?run=twitter-reply-2017-03-long-id&metric=if',
    );
  });
});
