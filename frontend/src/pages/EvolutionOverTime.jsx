import React from 'react';
import { Activity, CalendarRange, GitCompareArrows, Users } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import EvolutionChart from '../components/charts/EvolutionChart';
import MetricCard from '../components/MetricCard';
import EmptyState from '../components/states/EmptyState';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import {
  buildEvolutionPoints,
  EVOLUTION_METRICS,
  formatNumber,
  trendSummary,
} from '../features/evolution/evolutionModel';
import { historyConfigurationWarnings } from '../features/evolution/runCompatibility';
import { useEvolutionHistory } from '../features/evolution/useEvolutionHistory';

const SERIES_PARAM = 'historyMetric';

export default function EvolutionOverTimePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const data = useEvolutionHistory();
  const requested = searchParams.get(SERIES_PARAM);
  const selectedMetric = EVOLUTION_METRICS.find((item) => item.key === requested) ?? EVOLUTION_METRICS[0];
  const points = buildEvolutionPoints(data.history, selectedMetric.key, data.metric);
  const availablePoints = points.filter((point) => point.value !== null);
  const warnings = historyConfigurationWarnings(data.history);
  const note = trendSummary(points, selectedMetric.label);
  const first = availablePoints[0] ?? null;
  const last = availablePoints.at(-1) ?? null;

  const updateSeries = (value) => {
    const next = new URLSearchParams(searchParams);
    next.set(SERIES_PARAM, value);
    setSearchParams(next);
  };

  if (data.isLoading && data.history.length === 0) {
    return <LoadingState title="Loading compatible run history" />;
  }
  if (data.errors.length > 0 && data.history.length === 0) {
    return <ErrorState error={data.errors[0]} title="Run history could not be loaded" onRetry={data.retry} />;
  }

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <header className="flex flex-col gap-4 rounded-xl border border-border bg-panel p-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-xl font-bold text-text-heading">Evolution over completed runs</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted">
            This view compares separate completed runs with the same platform and content type. It does not infer a continuous dynamic model between snapshots.
          </p>
        </div>
        <label className="min-w-64 text-xs font-medium text-muted">
          Time-series metric
          <select
            value={selectedMetric.key}
            onChange={(event) => updateSeries(event.target.value)}
            className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-heading"
          >
            {EVOLUTION_METRICS.map((item) => (
              <option key={item.key} value={item.key}>{item.label}</option>
            ))}
          </select>
        </label>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Compatible completed runs"
          value={data.compatibleRuns.length}
          detail={`${data.selectedRun?.platform ?? 'Unavailable'} / ${data.selectedRun?.content_type ?? 'Unavailable'}`}
          source="GET /runs catalog grouped by platform and content type"
          icon={CalendarRange}
          colorClass="text-blue-500"
          bgClass="bg-blue-500"
          format={(value) => formatNumber(Number(value))}
        />
        <MetricCard
          title="Runs with loaded overview"
          value={data.history.length}
          detail={`Maximum ${12} recent compatible runs requested`}
          source="GET /runs/{run_id}/overview"
          icon={Activity}
          colorClass="text-purple-500"
          bgClass="bg-purple-500"
          format={(value) => formatNumber(Number(value))}
        />
        <MetricCard
          title="First available value"
          value={first?.value ?? null}
          detail={first?.label ?? 'No available values'}
          source={`Overview field: ${selectedMetric.key}; metric=${data.metric}`}
          icon={Users}
          colorClass="text-green-500"
          bgClass="bg-green-500"
          format={(value) => selectedMetric.unit === 'percent' ? `${formatNumber(Number(value))}%` : formatNumber(Number(value))}
        />
        <MetricCard
          title="Latest available value"
          value={last?.value ?? null}
          detail={last?.label ?? 'No available values'}
          source={`Overview field: ${selectedMetric.key}; metric=${data.metric}`}
          icon={GitCompareArrows}
          colorClass="text-orange-500"
          bgClass="bg-orange-500"
          format={(value) => selectedMetric.unit === 'percent' ? `${formatNumber(Number(value))}%` : formatNumber(Number(value))}
        />
      </div>

      {warnings.length > 0 && (
        <section className="rounded-xl border border-warning/30 bg-warning/5 p-5" aria-label="Run compatibility warnings">
          <h2 className="text-sm font-bold text-text-heading">Configuration warnings</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-muted">
            {warnings.map((warning) => <li key={warning.code}>{warning.message}</li>)}
          </ul>
        </section>
      )}

      {data.compatibleRuns.length < 2 ? (
        <EmptyState
          title="At least two compatible completed runs are required"
          message="Generate or select another completed run with the same platform and content type to build a time series. The selected run remains available in the global run selector."
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div className="xl:col-span-2">
            <EvolutionChart
              points={points}
              title={`${selectedMetric.label} over compatible runs`}
              description={`Actual run dates; ${data.metric.toUpperCase()} is used where the selected field is metric-specific.`}
              unit={selectedMetric.unit}
              selectedRunDetail={data.selectedRunDetail}
            />
          </div>
          <section className="rounded-xl border border-border bg-panel p-5">
            <h2 className="text-sm font-bold text-text-heading">Deterministic endpoint comparison</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              {note ?? 'Fewer than two runs contain a value for the selected field, so no endpoint change is calculated.'}
            </p>
            <p className="mt-4 text-xs text-muted">Missing values are displayed as unavailable and excluded from the arithmetic comparison.</p>
          </section>
        </div>
      )}

      <section className="rounded-xl border border-border bg-panel p-5">
        <h2 className="text-sm font-bold text-text-heading">Accessible run-history table</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-border text-xs text-muted">
              <tr>
                <th className="px-3 py-3">Run date</th>
                <th className="px-3 py-3">Run ID</th>
                <th className="px-3 py-3">Platform</th>
                <th className="px-3 py-3">Content type</th>
                <th className="px-3 py-3">{selectedMetric.label}</th>
              </tr>
            </thead>
            <tbody>
              {points.map((point) => {
                const run = data.compatibleRuns.find((item) => item.run_id === point.runId);
                return (
                  <tr key={point.runId} className="border-b border-border/40">
                    <td className="px-3 py-3 text-text-heading">{point.label}</td>
                    <td className="px-3 py-3 font-mono text-xs text-muted">{point.runId}</td>
                    <td className="px-3 py-3 text-muted">{run?.platform ?? 'Unavailable'}</td>
                    <td className="px-3 py-3 text-muted">{run?.content_type ?? 'Unavailable'}</td>
                    <td className="px-3 py-3 font-semibold text-text-heading">
                      {point.value === null ? 'Unavailable' : selectedMetric.unit === 'percent' ? `${formatNumber(point.value)}%` : formatNumber(point.value)}
                    </td>
                  </tr>
                );
              })}
              {points.length === 0 && (
                <tr><td colSpan={5} className="px-3 py-8 text-center text-muted">No compatible run overview records loaded.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
