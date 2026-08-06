import React from 'react';
import { Activity, GitCompareArrows, MessageSquare, Network, ShieldCheck, Users } from 'lucide-react';
import SkeletonCard from './SkeletonCard';
import {
  formatCount,
  formatPeriod,
  percentageChange,
  periodMetricValue,
  previousPeriod,
  selectedOverviewPeriod,
} from '../features/overview/overviewUtils';

export default function KPICards({
  overview,
  metric,
  selectedPeriod,
  isLoading = false,
}) {
  if (isLoading) {
    return (
      <div className="overview-kpi-grid" aria-label="Loading monthly metrics">
        {[0, 1, 2, 3].map((item) => <SkeletonCard key={item} className="overview-kpi-card" />)}
      </div>
    );
  }

  const current = selectedOverviewPeriod(overview, selectedPeriod);
  const previous = previousPeriod(overview?.periods ?? [], selectedPeriod);
  const periodLabel = formatPeriod(selectedPeriod);
  const cards = [
    {
      title: 'Users',
      value: current ? periodMetricValue(current, metric, 'users') : null,
      previous: previous ? periodMetricValue(previous, metric, 'users') : null,
      values: (overview?.periods ?? []).map((item) => periodMetricValue(item, metric, 'users')),
      source: `${metric}_users`,
      icon: Users,
      tone: 'primary',
    },
    {
      title: 'Messages',
      value: current ? periodMetricValue(current, metric, 'messages') : null,
      previous: previous ? periodMetricValue(previous, metric, 'messages') : null,
      values: (overview?.periods ?? []).map((item) => periodMetricValue(item, metric, 'messages')),
      source: `${metric}_messages`,
      icon: MessageSquare,
      tone: 'secondary',
    },
    {
      title: 'Interaction records',
      value: current?.interaction_records ?? null,
      previous: previous?.interaction_records ?? null,
      values: (overview?.periods ?? []).map((item) => item.interaction_records),
      source: 'network artifact rows',
      icon: Activity,
      tone: 'success',
    },
    {
      title: `${metric.toUpperCase()} communities`,
      value: current ? periodMetricValue(current, metric, 'communities') : null,
      previous: previous ? periodMetricValue(previous, metric, 'communities') : null,
      values: (overview?.periods ?? []).map((item) => periodMetricValue(item, metric, 'communities')),
      source: metric === 'if' ? 'total_absolute' : 'total_weighted',
      icon: Network,
      tone: 'warning',
    },
  ];

  return (
    <>
      <div className="overview-kpi-grid">
        {cards.map((card) => (
          <MonthlyMetricCard key={card.title} {...card} periodLabel={periodLabel} />
        ))}
      </div>
      <LongitudinalSummary overview={overview} current={current} />
    </>
  );
}

function MonthlyMetricCard({ title, value, previous, values, source, icon: Icon, tone, periodLabel }) {
  const change = percentageChange(value, previous);
  return (
    <article className={`overview-kpi-card overview-kpi-card--${tone}`} title={`Source: ${source}`}>
      <div className="overview-kpi-card__topline">
        <span className={`overview-kpi-card__icon overview-kpi-card__icon--${tone}`}>
          <Icon size={17} aria-hidden="true" />
        </span>
        <span className="overview-kpi-card__period">{periodLabel}</span>
      </div>
      <div className="overview-kpi-card__body">
        <div>
          <h3>{title}</h3>
          <p className={value === null || value === undefined ? 'is-unavailable' : ''}>
            {value === null || value === undefined ? 'Unavailable' : formatCount(value)}
          </p>
        </div>
        <MiniSparkline values={values} label={`${title} monthly trend`} />
      </div>
      <div className="overview-kpi-card__footer">
        <span>{change === null ? 'No previous-month comparison' : `${change >= 0 ? '↑' : '↓'} ${formatCount(Math.abs(change))}% from previous month`}</span>
        <span className="overview-kpi-card__source">{source}</span>
      </div>
    </article>
  );
}

function LongitudinalSummary({ overview, current }) {
  const items = [
    {
      label: 'Matched communities',
      value: current?.matched_community_count ?? null,
      detail: current?.matched_percentage === null || current?.matched_percentage === undefined
        ? 'Monthly match rate unavailable'
        : `${formatCount(current.matched_percentage)}% of the larger partition`,
      icon: GitCompareArrows,
    },
    {
      label: 'Persistent communities',
      value: overview?.run_summary?.persistent_community_count ?? null,
      detail: 'Longitudinal result across the full run',
      icon: ShieldCheck,
    },
    {
      label: 'Run interaction records',
      value: overview?.run_summary?.interaction_records ?? null,
      detail: 'Rows across all monthly network artifacts',
      icon: Activity,
    },
    {
      label: 'Analysis period',
      value: overview?.run_summary?.month_count ?? null,
      detail: periodRange(overview?.available_periods ?? []),
      suffix: ' months',
      icon: Network,
    },
  ];

  return (
    <section className="overview-summary-strip" aria-label="Longitudinal run summary">
      {items.map(({ label, value, detail, suffix = '', icon: Icon }) => (
        <div key={label} className="overview-summary-strip__item">
          <Icon size={16} aria-hidden="true" />
          <div>
            <p>{label}</p>
            <strong>{value === null || value === undefined ? 'Unavailable' : `${formatCount(value)}${suffix}`}</strong>
            <span>{detail}</span>
          </div>
        </div>
      ))}
    </section>
  );
}

function periodRange(periods) {
  if (!periods.length) return 'Period unavailable';
  return `${formatPeriod(periods[0])} – ${formatPeriod(periods.at(-1))}`;
}

function MiniSparkline({ values, label }) {
  const numeric = values.map((value, index) => ({ value, index })).filter((item) => Number.isFinite(item.value));
  if (numeric.length < 2) return <span className="overview-sparkline overview-sparkline--empty">No trend</span>;
  const min = Math.min(...numeric.map((item) => item.value));
  const max = Math.max(...numeric.map((item) => item.value));
  const width = 96;
  const height = 34;
  const points = numeric.map(({ value, index }) => {
    const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
    const y = max === min ? height / 2 : height - ((value - min) / (max - min)) * (height - 6) - 3;
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg className="overview-sparkline" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label}>
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
