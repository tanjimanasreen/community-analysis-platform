import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ArtifactUnavailableState from '../ArtifactUnavailableState';
import EmptyState from '../EmptyState';
import ErrorState from '../ErrorState';
import LoadingState from '../LoadingState';
import VerificationFailureState from '../VerificationFailureState';

describe('dashboard request states', () => {
  it('announces loading without exposing stale analytical content', () => {
    render(<LoadingState />);
    expect(screen.getByText('Loading dashboard data')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true');
  });

  it('renders a retry action for idempotent request failures', () => {
    const retry = vi.fn();
    render(<ErrorState error={new Error('offline')} onRetry={retry} />);
    screen.getByRole('button', { name: 'Retry' }).click();
    expect(retry).toHaveBeenCalledOnce();
    expect(screen.getByRole('alert')).toHaveTextContent('offline');
  });

  it('distinguishes empty and optional-artifact states', () => {
    const { rerender } = render(<EmptyState />);
    expect(screen.getByText('No records available')).toBeInTheDocument();
    rerender(<ArtifactUnavailableState artifactName="Theme similarity" />);
    expect(screen.getByText('Artifact not generated')).toBeInTheDocument();
    expect(screen.getByText(/Theme similarity/)).toBeInTheDocument();
  });

  it('shows the verification error code for integrity failures', () => {
    render(
      <VerificationFailureState
        verification={{
          run_id: 'run-1',
          ok: false,
          status: 'invalid',
          checked_artifacts: 0,
          error_code: 'ARTIFACT_CHECKSUM_MISMATCH',
          error: 'Checksum mismatch.',
        }}
      />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent(
      'ARTIFACT_CHECKSUM_MISMATCH',
    );
  });
});
