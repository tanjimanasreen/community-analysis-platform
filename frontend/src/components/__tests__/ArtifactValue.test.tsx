import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ArtifactValue from '../ArtifactValue';

describe('ArtifactValue', () => {
  it('renders JSON arrays as readable value chips', () => {
    render(<ArtifactValue value={'["alpha", "beta"]'} />);
    expect(screen.getByText('alpha')).toBeInTheDocument();
    expect(screen.getByText('beta')).toBeInTheDocument();
  });

  it('renders nested objects with humanized labels', () => {
    render(<ArtifactValue value={{ run_metrics: { cache_hits: 741 }, degraded: false }} />);
    expect(screen.getByText('Run Metrics')).toBeInTheDocument();
    expect(screen.getByText('Cache Hits')).toBeInTheDocument();
    expect(screen.getByText('741')).toBeInTheDocument();
    expect(screen.getByText('No')).toBeInTheDocument();
  });

  it('keeps ordinary text as text and never evaluates it', () => {
    render(<ArtifactValue value="['python', 'literal']" />);
    expect(screen.getByText("['python', 'literal']")).toBeInTheDocument();
  });
});
