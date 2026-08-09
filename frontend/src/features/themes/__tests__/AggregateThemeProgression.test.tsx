import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type {
  ClusteredThemeTimelineResponse,
  MonthlyClusteredThemeSummary,
} from '../../../types/api';
import AggregateThemeProgression from '../AggregateThemeProgression';

function summary(period: string, names: string[]): MonthlyClusteredThemeSummary {
  const denominator = Math.max(1, names.length);
  return {
    period,
    source_observation_count: denominator,
    excluded_records_missing_general_theme: 0,
    excluded_records_ambiguous_general_theme_serialization: 0,
    monthly_noise_observation_count: 0,
    total_themed_community_pairs: denominator,
    distinct_clustered_theme_count: names.length,
    themes: names.map((name, index) => ({
      theme_id: `ct_${period}_${index}`,
      name,
      community_count: denominator - index,
      percentage: ((denominator - index) * 100) / denominator,
      keywords: [`keyword-${index}`],
      monthly_cluster_ids: [`mc_${period}_${index}`],
      monthly_representative_themes: [name],
      source_theme_labels: [name],
      community_pairs: [],
      mean_membership_probability: 0.9,
    })),
    embedding_provider: 'tei',
    embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
    monthly_cluster_contract_version: '2.1',
    canonicalization_contract_version: '2.1',
  };
}

function timeline(monthly: MonthlyClusteredThemeSummary[]): ClusteredThemeTimelineResponse {
  return {
    run_id: 'run-1',
    scope: 'matched',
    available_periods: monthly.map((item) => item.period),
    periods: monthly.map((item) => item.period),
    complete: true,
    source_observation_count: monthly.reduce((total, item) => total + item.source_observation_count, 0),
    excluded_records_missing_general_theme: 0,
    excluded_records_ambiguous_general_theme_serialization: 0,
    monthly_noise_observation_count: 0,
    distinct_canonical_theme_count: monthly.reduce((total, item) => total + item.themes.length, 0),
    monthly_summaries: monthly,
    most_discussed_theme: null,
  };
}

describe('AggregateThemeProgression', () => {
  it('renders sparse monthly rankings without fabricating missing ranks and keeps the final column inside the SVG', () => {
    const longFinalTheme = 'Immigration policy and constitutional court challenges across institutions';
    const response = timeline([
      summary('2017-01', ['January one', 'January two', 'January three', 'January four', 'January five']),
      summary('2017-02', ['February one', 'February two', 'February three']),
      summary('2017-03', ['March one', 'March two', 'March three', 'March four']),
      summary('2017-04', [longFinalTheme, 'Religious text bans and public debate']),
    ]);

    render(<AggregateThemeProgression response={response} onSelectTheme={vi.fn()} />);

    expect(screen.getByText('Up to 5 themes per month')).toBeInTheDocument();
    const table = screen.getByRole('table');
    expect(within(table).getAllByText('Apr 2017')).toHaveLength(2);
    expect(within(table).getAllByRole('row')).toHaveLength(15); // header + 5 + 3 + 4 + 2

    const chart = screen.getByTestId('aggregate-theme-progression-chart');
    const [, , widthText] = (chart.getAttribute('viewBox') ?? '').split(' ');
    const width = Number(widthText);
    expect(width).toBeGreaterThan(760);

    const finalPoint = chart.querySelector('g[data-period="2017-04"][data-theme-id="ct_2017-04_0"]');
    expect(finalPoint).not.toBeNull();
    const cx = Number(finalPoint?.querySelector('circle')?.getAttribute('cx'));
    expect(width - cx).toBeGreaterThanOrEqual(120);
    expect(finalPoint?.querySelector('title')?.textContent).toContain(longFinalTheme);
    expect(finalPoint?.getAttribute('aria-label')).toContain(longFinalTheme);
    expect(finalPoint?.querySelectorAll('tspan').length).toBeLessThanOrEqual(2);
  });

  it('supports a single-month timeline without drawing invalid progression lines', () => {
    render(
      <AggregateThemeProgression
        response={timeline([summary('2017-01', ['Policy', 'Activism'])])}
        onSelectTheme={vi.fn()}
      />,
    );

    const chart = screen.getByTestId('aggregate-theme-progression-chart');
    expect(chart.querySelectorAll('polyline')).toHaveLength(0);
    expect(chart.getAttribute('viewBox')).toMatch(/^0 0 760 /);
    expect(chart.textContent).toContain('Jan 2017');
  });

  it('grows horizontally for long timelines and derives rank guides from the configured limit', () => {
    const months = Array.from({ length: 8 }, (_, index) => {
      const month = String(index + 1).padStart(2, '0');
      return summary(`2017-${month}`, ['One', 'Two', 'Three', 'Four', 'Five']);
    });
    const onSelectTheme = vi.fn();

    render(<AggregateThemeProgression response={timeline(months)} onSelectTheme={onSelectTheme} limit={3} />);

    const chart = screen.getByTestId('aggregate-theme-progression-chart');
    const [, , widthText] = (chart.getAttribute('viewBox') ?? '').split(' ');
    expect(Number(widthText)).toBeGreaterThan(2000);
    expect(screen.getByText('Rank 1')).toBeInTheDocument();
    expect(screen.getByText('Rank 3')).toBeInTheDocument();
    expect(screen.queryByText('Rank 4')).not.toBeInTheDocument();
    expect(screen.getByText('Up to 3 themes per month')).toBeInTheDocument();
    expect(screen.getByTestId('aggregate-theme-progression-scroll')).toHaveClass('overflow-x-auto');

    fireEvent.click(screen.getAllByRole('button', { name: /One, Jan 2017, rank 1/i })[0]);
    expect(onSelectTheme).toHaveBeenCalled();
  });
});
