import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import DataExplorerPage from '../DataExplorer';
import { useExplorerData } from '../../features/explorer/useExplorerData';

vi.mock('../../features/explorer/useExplorerData', () => ({ useExplorerData: vi.fn() }));

function resultFor(options) {
  const artifact = {
    key: 'network_data', path: 'data/network.csv', category: 'data', media_type: 'text/csv',
    schema_version: '1', sha256: 'a'.repeat(64), rows: 3, byte_size: 42, stage: 'network_community',
  };
  const pages = {
    communities: { records: [{ community_id: '1', node_count: 2, edge_count: 1, total_weight: 5 }], total: 50, limit: 25, offset: options.offset },
    artifacts: { records: [artifact], total: 1, limit: 25, offset: options.offset },
  };
  return {
    selectedRunId: 'run-1', metric: 'if', exactCommunitySearch: false,
    query: { isPending: false, error: null, refetch: vi.fn() },
    page: pages[options.mode] ?? { records: [], total: 0, limit: 25, offset: options.offset },
  };
}

describe('DataExplorer page', () => {
  it('switches real modes, preserves independent offsets, and uses manifest download URLs', () => {
    useExplorerData.mockImplementation(resultFor);
    render(<MemoryRouter initialEntries={['/data?run=run-1&metric=if']}><DataExplorerPage /></MemoryRouter>);
    expect(screen.getByText('1–25 of 50')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Next explorer page' }));
    expect(useExplorerData).toHaveBeenLastCalledWith(expect.objectContaining({ mode: 'communities', offset: 25 }));

    fireEvent.click(screen.getByRole('button', { name: 'Artifacts' }));
    expect(useExplorerData).toHaveBeenLastCalledWith(expect.objectContaining({ mode: 'artifacts', offset: 0 }));
    fireEvent.click(screen.getByText('network_data'));
    const download = screen.getByRole('link', { name: 'Download verified artifact' });
    expect(download.getAttribute('href')).toContain('/runs/run-1/downloads/network_data');

    fireEvent.click(screen.getByRole('button', { name: 'Communities' }));
    expect(useExplorerData).toHaveBeenLastCalledWith(expect.objectContaining({ mode: 'communities', offset: 25 }));
    expect(screen.queryByText('Personal Support')).not.toBeInTheDocument();
  });
});
