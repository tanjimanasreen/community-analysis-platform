import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PageNavigationRail, { PageNavigationRailSlot } from '../PageNavigationRail';

const sections = [
  { id: 'section-a', label: 'Section A', icon: 'kpis' },
  { id: 'section-b', label: 'Section B', icon: 'themes' },
  { id: 'section-c', label: 'Section C', icon: 'provenance' },
];

describe('PageNavigationRail', () => {
  beforeEach(() => {
    class IntersectionObserverMock {
      observe = vi.fn();
      disconnect = vi.fn();
    }
    vi.stubGlobal('IntersectionObserver', IntersectionObserverMock);
  });


  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('uses one compact shared sticky slot instead of a full-screen centering wrapper', () => {
    const { container } = render(<PageNavigationRailSlot sections={sections} />);
    const slot = container.querySelector('aside');

    expect(slot).toHaveClass('sticky', 'top-4', 'self-start');
    expect(slot).not.toHaveClass('h-screen', 'top-0', 'justify-center');
    expect(screen.getByRole('navigation', { name: 'Section rail' })).toBeInTheDocument();
    expect(screen.getAllByRole('button')).toHaveLength(3);
  });

  it('scrolls the configured dashboard container and focuses the selected section', () => {
    render(
      <>
        <div id="main-content">
          <section id="section-a" tabIndex={-1}>A</section>
          <section id="section-b" tabIndex={-1}>B</section>
        </div>
        <PageNavigationRail sections={sections.slice(0, 2)} />
      </>,
    );
    const main = document.getElementById('main-content');
    const scrollTo = vi.fn();
    Object.defineProperty(main, 'scrollTo', { value: scrollTo });

    fireEvent.click(screen.getByRole('button', { name: 'Section B' }));

    expect(scrollTo).toHaveBeenCalledWith(expect.objectContaining({ behavior: 'smooth' }));
    expect(screen.getByRole('button', { name: 'Section B' })).toHaveAttribute('aria-current', 'true');
  });
});
