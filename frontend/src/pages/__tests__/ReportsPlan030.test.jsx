import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ReportsPage from '../Reports';
import { useArtifactLibrary } from '../../features/reports/useArtifactLibrary';

vi.mock('../../features/reports/useArtifactLibrary', () => ({ useArtifactLibrary: vi.fn() }));

const artifacts = [
  { key: 'report_html', path: 'reports/report.html', category: 'report', media_type: 'text/html', schema_version: '1', sha256: 'a'.repeat(64), rows: null, byte_size: 100, stage: 'report' },
  { key: 'temp', path: 'intermediate/temp.csv', category: 'intermediate', media_type: 'text/csv', schema_version: '1', sha256: 'b'.repeat(64), rows: 1, byte_size: 10, stage: 'topic' },
];

describe('Reports artifact library', () => {
  beforeEach(() => {
    useArtifactLibrary.mockReturnValue({ selectedRunId: 'run-1', verification: { ok: true }, artifactsQuery: { data: { artifacts, total: 2 }, isPending: false, error: null, refetch: vi.fn() } });
  });

  it('filters artifact metadata and suppresses intermediate downloads', () => {
    render(<MemoryRouter><ReportsPage /></MemoryRouter>);
    expect(screen.getByRole('link', { name: 'Open report' })).toHaveAttribute('href', expect.stringContaining('/runs/run-1/report'));
    expect(screen.getByText('Not downloadable')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Download' })).toHaveLength(1);
    fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'intermediate' } });
    expect(screen.queryByText('report_html')).not.toBeInTheDocument();
    expect(screen.getByText('temp')).toBeInTheDocument();
    expect(screen.queryByText('Create Report')).not.toBeInTheDocument();
  });
});
