import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import EvidencePage from '../Evidence';
import { EVIDENCE_VIEWS } from '../../features/evidence/evidenceModel';
import { useEvidenceData } from '../../features/evidence/useEvidenceData';

vi.mock('../../features/evidence/useEvidenceData', () => ({ useEvidenceData: vi.fn() }));

const artifacts = [
  { key: 'report_html', path: 'reports/report.html', category: 'report', media_type: 'text/html', schema_version: '1', sha256: 'a'.repeat(64), rows: null, byte_size: 100, stage: 'report' },
  { key: 'network_data', path: 'data/network.csv', category: 'data', media_type: 'text/csv', schema_version: '1', sha256: 'b'.repeat(64), rows: 3, byte_size: 42, stage: 'network_community' },
  { key: 'temp', path: 'intermediate/temp.csv', category: 'intermediate', media_type: 'text/csv', schema_version: '1', sha256: 'c'.repeat(64), rows: 1, byte_size: 10, stage: 'topic' },
];

function resultFor(options) {
  const pages = {
    communities: {
      records: [{ community_id: '17', node_count: 12, edge_count: 20, total_weight: 44, cross_community_neighbor_count: 2, inbound_cross_community_weight: 8, outbound_cross_community_weight: 6 }],
      total: 1, limit: 25, offset: options.offset,
    },
    'matched-lda': {
      records: [{ absolute_community: 17, weighted_community: 8, absolute_unigram_topic: 2, weighted_unigram_topic: 4, jaccard_score: 1 }],
      total: 1, limit: 25, offset: options.offset,
    },
  };
  return {
    selectedRunId: 'run-1',
    metric: 'if',
    setMetric: vi.fn(),
    verification: { run_id: 'run-1', ok: true, status: 'valid', checked_artifacts: 3, error_code: null, error: null },
    definition: EVIDENCE_VIEWS[options.view],
    periods: ['2017-03', '2017-04'],
    selectedPeriod: '2017-03',
    setSelectedPeriod: vi.fn(),
    exactCommunitySearch: EVIDENCE_VIEWS[options.view].supportsCommunitySearch,
    overviewQuery: { isPending: false, error: null, refetch: vi.fn() },
    query: { isPending: false, error: null, refetch: vi.fn() },
    page: pages[options.view] ?? { records: [], total: 0, limit: 25, offset: options.offset },
    artifactsQuery: { data: { run_id: 'run-1', artifacts, total: artifacts.length }, isPending: false, error: null, refetch: vi.fn() },
  };
}

describe('Research Data & Reports page', () => {
  it('groups evidence by thesis dimension, uses local affinity only where applicable, and preserves month-local community links', () => {
    useEvidenceData.mockImplementation(resultFor);
    render(<MemoryRouter initialEntries={['/data-reports?run=run-1&metric=if&view=communities&period=2017-03']}><EvidencePage /></MemoryRouter>);

    expect(screen.getByRole('button', { name: /Structural · RQ1/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /Semantic · RQ2/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Temporal · RQ3 \/ RQ4/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Outputs/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Communities' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.queryByRole('button', { name: 'Matched LDA' })).not.toBeInTheDocument();
    expect(screen.getByLabelText('Data affinity')).toBeInTheDocument();
    expect(screen.getByLabelText('Data period')).toHaveValue('2017-03');

    fireEvent.click(screen.getByText('17'));
    const communityHref = screen.getByRole('link', { name: /Explore IF community 17/ }).getAttribute('href');
    expect(communityHref).toContain('/communities?');
    expect(communityHref).toContain('period=2017-03');
    expect(communityHref).toContain('metric=if');
    expect(communityHref).toContain('community=17');

    fireEvent.click(screen.getByRole('button', { name: /Semantic · RQ2/ }));
    expect(screen.getByRole('button', { name: 'Matched LDA' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Partial-match LDA' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Generated Themes' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Communities' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Matched LDA' }));
    expect(useEvidenceData).toHaveBeenLastCalledWith(expect.objectContaining({ view: 'matched-lda' }));
    expect(screen.queryByLabelText('Data affinity')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Exact community ID')).toBeInTheDocument();
  });

  it('unifies report/artifact browsing with verified download behavior', () => {
    useEvidenceData.mockImplementation(resultFor);
    render(<MemoryRouter initialEntries={['/data-reports?run=run-1&metric=if&view=outputs']}><EvidencePage /></MemoryRouter>);

    expect(screen.getByRole('link', { name: 'Open report' })).toHaveAttribute('href', expect.stringContaining('/runs/run-1/report'));
    expect(screen.getAllByRole('link', { name: /Run History/i })).toHaveLength(1);
    expect(screen.getByText('Published outputs')).toBeInTheDocument();
    expect(screen.getByText('Analytical data & metadata')).toBeInTheDocument();
    expect(screen.getByText('Advanced provenance')).toBeInTheDocument();
    expect(screen.getByText('Not downloadable')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Download' })).toHaveLength(2);
    expect(screen.queryByText('Create Report')).not.toBeInTheDocument();
  });
});
