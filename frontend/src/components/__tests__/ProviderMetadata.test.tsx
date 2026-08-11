import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ProviderMetadata from '../ProviderMetadata';

describe('ProviderMetadata', () => {
  it('keeps large run-metric arrays collapsed behind compact summaries', () => {
    const latency = Array.from({ length: 281 }, (_, index) => 5000 + index * 10);
    render(<ProviderMetadata providerMetadata={{
      configured_primary_provider: 'openai:gpt-5-nano',
      configured_primary_model: 'gpt-5-nano',
      provider_config_digest: '53cdd219aee49a26b832aa519fc3f91d740fdf8379ce3c13eae464b02e5381a8',
      run_metrics: {
        calls: 281,
        logical_theme_requests: 281,
        cache_hits: 456,
        total_cost: 0.42,
        latency_ms_list: latency,
        ttft_ms_list: latency,
        tpot_ms_list: latency.map((value) => value / 50),
        prompts_and_responses: [{ user_prompt: 'sensitive prompt body' }],
      },
    }} />);

    expect(screen.getByRole('heading', { name: 'Theme provider and model provenance' })).toBeInTheDocument();
    expect(screen.getByText('Provider calls')).toBeInTheDocument();
    expect(screen.getAllByText('281').length).toBeGreaterThan(0);
    expect(screen.getByText('Performance summary')).toBeInTheDocument();
    expect(screen.getByText('Latency')).toBeInTheDocument();
    expect(screen.getByText('Advanced provenance').closest('details')).not.toHaveAttribute('open');
    expect(screen.getByText('Raw run metrics').closest('details')).not.toHaveAttribute('open');
    expect(screen.queryByText('sensitive prompt body')).not.toBeInTheDocument();
    expect(document.body.textContent).not.toContain('5000, 5010, 5020');
  });

  it('retains full digest values accessibly while rendering a compact visual value', () => {
    const digest = '53cdd219aee49a26b832aa519fc3f91d740fdf8379ce3c13eae464b02e5381a8';
    render(<ProviderMetadata providerMetadata={{ provider_config_digest: digest }} />);

    const advanced = screen.getByText('Advanced provenance').closest('details');
    expect(advanced).not.toBeNull();
    advanced?.setAttribute('open', '');
    const digestValue = screen.getByLabelText(digest);
    expect(digestValue).toHaveAttribute('title', digest);
    expect(digestValue.textContent).toContain('…');
  });

  it('renders an explicit unavailable state when no metadata exists', () => {
    render(<ProviderMetadata />);
    expect(screen.getByText('Provider metadata unavailable for this run.')).toBeInTheDocument();
  });
});
