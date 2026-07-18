import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { metricCommunityCount, runDate } from '../../features/overview/overviewUtils';

export default function EvolutionChart({
  history = [],
  metric = 'if',
  selectedRunDetail,
  points,
  title,
  description,
  unit = 'count',
}) {
  const chartData = points
    ? points.map((point) => ({ ...point, name: point.label }))
    : history.map(({ run, overview }) => ({
      name: runDate(run).slice(0, 10),
      label: runDate(run).slice(0, 10),
      value: metricCommunityCount(overview, metric),
      users: overview.total_users,
      messages: overview.total_messages,
      runId: run.run_id,
    }));
  const availablePoints = chartData.filter((item) => item.value !== null && item.value !== undefined);

  if (availablePoints.length < 2) {
    return <RunConfigurationPanel selectedRunDetail={selectedRunDetail} title={title} />;
  }

  return (
    <section className="bg-panel border border-border rounded-xl p-5 flex flex-col h-full">
      <div className="mb-6">
        <h3 className="text-sm font-bold text-text-heading">{title || 'Compatible Run History'}</h3>
        <p className="text-xs text-muted mt-1">
          {description || 'Separate completed runs with matching platform and content type; not a continuous dynamic model.'}
        </p>
      </div>
      <div className="flex-grow w-full min-h-[280px]" role="img" aria-label={`${title || 'Run history'} line chart`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: unit === 'percent' ? -10 : -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
            <XAxis dataKey="name" stroke="var(--color-muted)" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis
              stroke="var(--color-muted)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              allowDecimals={unit === 'percent'}
              tickFormatter={(value) => unit === 'percent' ? `${value}%` : value}
            />
            <Tooltip content={<HistoryTooltip unit={unit} />} />
            <Line
              type="monotone"
              dataKey="value"
              name={title || `${metric.toUpperCase()} communities`}
              stroke="var(--color-primary)"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function HistoryTooltip({ active, payload, label, unit }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  const raw = point.value;
  const value = raw === null || raw === undefined
    ? 'Unavailable'
    : unit === 'percent'
      ? `${Number(raw).toLocaleString(undefined, { maximumFractionDigits: 2 })}%`
      : Number(raw).toLocaleString(undefined, { maximumFractionDigits: 2 });
  return (
    <div className="bg-panel border border-border p-3 rounded-lg shadow-xl text-xs">
      <p className="font-bold text-text-heading">{label}</p>
      <p className="mt-2 text-muted">Value: <span className="text-text-heading">{value}</span></p>
      {point.runId && <p className="mt-1 font-mono text-[10px] text-muted">{point.runId}</p>}
    </div>
  );
}

function RunConfigurationPanel({ selectedRunDetail, title }) {
  const pipeline = selectedRunDetail?.pipeline ?? {};
  const dataset = selectedRunDetail?.dataset ?? {};
  const entries = [
    ['Platform', dataset.platform],
    ['Content type', dataset.content_type],
    ['Date start', dataset.date_start],
    ['Date end', dataset.date_end],
    ['Completed at', pipeline.completed_at],
    ['Artifact count', selectedRunDetail?.artifact_count],
  ].filter(([, value]) => value !== null && value !== undefined);

  return (
    <section className="bg-panel border border-border rounded-xl p-5 flex flex-col h-full min-h-[300px]">
      <h3 className="text-sm font-bold text-text-heading">{title || 'Run Configuration'}</h3>
      <p className="mt-1 text-xs text-muted">At least two compatible completed runs with available values are required for a run-history chart.</p>
      <dl className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {entries.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-border bg-panel-soft/50 p-3">
            <dt className="text-xs text-muted">{label}</dt>
            <dd className="mt-1 text-sm font-semibold text-text-heading break-words">{String(value)}</dd>
          </div>
        ))}
        {entries.length === 0 && <p className="text-sm text-muted">Configuration metadata is unavailable for this run.</p>}
      </dl>
    </section>
  );
}
