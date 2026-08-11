import { ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { MetricName } from '../../types/api';
import { formatPeriod } from '../overview/overviewUtils';
import type { EvidenceViewDefinition } from './evidenceModel';

interface EvidenceContextHeaderProps {
  definition: EvidenceViewDefinition;
  periods: string[];
  selectedPeriod: string;
  onPeriodChange: (period: string) => void;
  metric: MetricName;
  onMetricChange: (metric: MetricName) => void;
  destinationHref: string | null;
  destinationLabel: string | null;
}

export default function EvidenceContextHeader({
  definition,
  periods,
  selectedPeriod,
  onPeriodChange,
  metric,
  onMetricChange,
  destinationHref,
  destinationLabel,
}: EvidenceContextHeaderProps) {
  return (
    <div className="border-b border-border px-5 py-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-primary">{definition.eyebrow}</p>
          <h2 className="mt-1 text-lg font-bold text-text-heading">{definition.label}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">{definition.description}</p>
        </div>
        {destinationHref && destinationLabel && (
          <Link
            to={destinationHref}
            className="inline-flex shrink-0 items-center gap-2 self-start rounded-lg border border-border px-3 py-2 text-xs font-semibold text-primary hover:bg-surface-soft"
          >
            {destinationLabel} <ExternalLink size={13} aria-hidden="true" />
          </Link>
        )}
      </div>

      {(definition.requiresPeriod || definition.usesMetric) && (
        <div className="mt-4 flex flex-wrap items-end gap-3 rounded-xl border border-border/70 bg-bg/30 p-3">
          {definition.requiresPeriod && (
            <label className="min-w-[180px] text-xs font-semibold text-text-heading">
              Period
              <select
                aria-label="Data period"
                value={selectedPeriod}
                onChange={(event) => onPeriodChange(event.target.value)}
                disabled={periods.length === 0}
                className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
              >
                {periods.length === 0 && <option value="">No monthly snapshots</option>}
                {periods.map((period) => <option key={period} value={period}>{formatPeriod(period)}</option>)}
              </select>
            </label>
          )}
          {definition.usesMetric && (
            <label className="min-w-[220px] text-xs font-semibold text-text-heading">
              Affinity
              <select
                aria-label="Data affinity"
                value={metric}
                onChange={(event) => onMetricChange(event.target.value as MetricName)}
                className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
              >
                <option value="if">Interaction Frequency (IF)</option>
                <option value="wif">Weighted Interaction Frequency (WIF)</option>
              </select>
            </label>
          )}
          <p className="max-w-xl text-[11px] leading-5 text-muted">
            {definition.usesMetric
              ? 'Affinity changes the persisted structural partition being inspected; it does not rerun Louvain or recalculate thesis metrics.'
              : 'This view preserves paired IF/WIF or longitudinal evidence and therefore does not use a single affinity filter.'}
          </p>
        </div>
      )}
    </div>
  );
}
