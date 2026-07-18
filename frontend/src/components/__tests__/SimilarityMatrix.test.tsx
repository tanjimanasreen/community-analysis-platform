import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import SimilarityMatrix from '../SimilarityMatrix';

describe('SimilarityMatrix', () => {
  it('renders the API matrix with an accessible table alternative', () => {
    render(<SimilarityMatrix matrix={[[1, 0.42], [0.42, 1]]} labels={['Policy', 'Civic']} />);
    expect(screen.getByRole('table', { name: 'Theme similarity matrix' })).toBeInTheDocument();
    expect(screen.getAllByText('0.42').length).toBe(2);
  });
});
