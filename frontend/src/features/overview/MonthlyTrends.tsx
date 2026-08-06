import { useMemo, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MetricName, OverviewPeriod } from '../../types/api';
import { formatCount, formatPeriod, periodMetricValue } from './overviewUtils';

type TrendKey = 'users' | 'messages' | 'interactions' | 'communities' | 'matched';

interface MonthlyTrendsProps {
  periods: OverviewPeriod[];
  selectedPeriod: string;
  metric: MetricName;
  onSelectPeriod: (period: string) => void;
}

const trendOptions: Array<{ key: TrendKey; label: string }> = [
  { key: 'users', label: 'Users' },
  { key: 'messages', label: 'Messages' },
  { key: 'interactions', label: 'Interaction records' },
  { key: 'communities', label: 'Communities' },
  { key: 'matched', label: 'Matched %' },
];

export default function MonthlyTrends({ periods, selectedPeriod, metric, onSelectPeriod }: MonthlyTrendsProps) {
  const [trend, setTrend] = useState<TrendKey>('users');
  const data = useMemo(
    () => periods.map((period) => ({
      period: period.period,
      label: formatPeriod(period.period).replace(/\s\d{4}$/, ''),
      value: trendValue(period, metric, trend),
    })),
    [metric, periods, trend],
  );
  const hasValues = data.some((item) => item.value !== null);

  return (
    <section className="panel overview-trends-panel">
      <div className="overview-section-heading">
        <div>
          <p className="overview-eyebrow">Monthly trend</p>
          <h2>{trendOptions.find((item) => item.key === trend)?.label}</h2>
          <p>Click a point to update the selected monthly snapshot.</p>
        </div>
        <label className="overview-trend-select">
          <span>Metric</span>
          <select value={trend} onChange={(event) => setTrend(event.target.value as TrendKey)}>
            {trendOptions.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
          </select>
        </label>
      </div>

      {hasValues ? (
        <div className="overview-trends-chart" role="img" aria-label={`${trend} by month`}>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={data} margin={{ top: 12, right: 20, left: 4, bottom: 4 }}>
              <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis dataKey="label" stroke="#94a3b8" tickLine={false} axisLine={false} />
              <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} width={74} tickFormatter={(value) => compactNumber(value)} />
              <Tooltip
                contentStyle={{ background: '#161f33', border: '1px solid #2a354b', borderRadius: 10 }}
                labelFormatter={(_, payload) => formatPeriod(payload?.[0]?.payload?.period)}
                formatter={(value) => [trend === 'matched' ? `${formatCount(Number(value))}%` : formatCount(Number(value)), trendOptions.find((item) => item.key === trend)?.label]}
              />
              <Line
                type="linear"
                dataKey="value"
                stroke="#3b82f6"
                strokeWidth={2.5}
                connectNulls={false}
                activeDot={(props: any) => (
                  <circle
                    cx={props.cx ?? 0}
                    cy={props.cy ?? 0}
                    r={7}
                    fill="#f59e0b"
                    stroke="#0b1121"
                    strokeWidth={2}
                    style={{ cursor: 'pointer' }}
                    onClick={() => onSelectPeriod(String(props.payload.period))}
                  />
                )}
                dot={(props: any) => {
                  const selected = props.payload.period === selectedPeriod;
                  return (
                    <circle
                      key={props.payload.period}
                      cx={props.cx ?? 0}
                      cy={props.cy ?? 0}
                      r={selected ? 6 : 4}
                      fill={selected ? '#f59e0b' : '#3b82f6'}
                      stroke="#0b1121"
                      strokeWidth={2}
                      style={{ cursor: 'pointer' }}
                      onClick={() => onSelectPeriod(String(props.payload.period))}
                    />
                  );
                }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="overview-trends-empty">No monthly values are available for this metric.</div>
      )}

      <details className="overview-values-table">
        <summary>View exact monthly values</summary>
        <div className="overview-values-table__scroll">
          <table>
            <thead><tr><th>Month</th><th>Value</th><th>Selected</th></tr></thead>
            <tbody>
              {data.map((item) => (
                <tr key={item.period}>
                  <td>{formatPeriod(item.period)}</td>
                  <td>{item.value === null ? 'Unavailable' : `${formatCount(item.value)}${trend === 'matched' ? '%' : ''}`}</td>
                  <td>{item.period === selectedPeriod ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}

function trendValue(period: OverviewPeriod, metric: MetricName, trend: TrendKey): number | null {
  if (trend === 'users') return periodMetricValue(period, metric, 'users');
  if (trend === 'messages') return periodMetricValue(period, metric, 'messages');
  if (trend === 'communities') return periodMetricValue(period, metric, 'communities');
  if (trend === 'matched') return period.matched_percentage;
  return period.interaction_records;
}

function compactNumber(value: number): string {
  return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(value);
}
