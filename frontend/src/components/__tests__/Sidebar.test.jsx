import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import Sidebar from '../Sidebar';

describe('Sidebar', () => {
  it('exposes Methodology, removes fake identity/settings, and preserves run search state', () => {
    render(
      <MemoryRouter initialEntries={['/?run=run-1&metric=if']}>
        <Sidebar isCollapsed={false} toggleSidebar={vi.fn()} onNavigate={vi.fn()} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: 'Methodology' })).toHaveAttribute(
      'href',
      '/methodology?run=run-1&metric=if',
    );
    expect(screen.getByRole('link', { name: 'Community Evolution' })).toHaveAttribute(
      'href',
      '/evolution?run=run-1&metric=if',
    );
    expect(screen.queryByRole('link', { name: 'Community Transitions' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Evolution Over Time' })).not.toBeInTheDocument();
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
    expect(screen.queryByText('Aisha Rahman')).not.toBeInTheDocument();
    expect(screen.getByText('Read-only analytics')).toBeInTheDocument();
  });
});
