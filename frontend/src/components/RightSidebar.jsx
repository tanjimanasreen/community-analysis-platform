import React from 'react';
import { AlertCircle, CheckCircle2, Database, Info, Lightbulb, PieChart } from 'lucide-react';
import { formatCount, metadataValue } from '../features/overview/overviewUtils';

function InsightItem({ title, description, icon: Icon, tone = 'primary' }) {
  const toneClass = {
    primary: 'text-primary bg-primary/10',
    success: 'text-success bg-success/10',
    warning: 'text-warning bg-warning/10',
    neutral: 'text-muted bg-panel-soft',
  }[tone];
  return (
    <div className="flex gap-3">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${toneClass}`}>
        <Icon size={16} aria-hidden="true" />
      </div>
      <div>
        <h4 className="text-sm font-semibold text-text-heading">{title}</h4>
        <p className="text-xs text-muted mt-1 leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

export default function RightSidebar({
  overview,
  network,
  metric,
  selectedRun,
  selectedRunDetail,
  hasTransitions,
}) {
  const insights = [];
  if (overview.matched_percentage !== null) {
    if (overview.matched_percentage >= 80) {
      insights.push({
        title: 'High IF/WIF overlap',
        description: `${formatCount(overview.matched_percentage)}% matched community overlap is reported for this run.`,
        icon: CheckCircle2,
        tone: 'success',
      });
    } else if (overview.matched_percentage < 50) {
      insights.push({
        title: 'Limited IF/WIF overlap',
        description: `${formatCount(overview.matched_percentage)}% matched overlap indicates stronger partition differences for this run.`,
        icon: AlertCircle,
        tone: 'warning',
      });
    } else {
      insights.push({
        title: 'Moderate IF/WIF overlap',
        description: `${formatCount(overview.matched_percentage)}% of communities are matched across affinity definitions.`,
        icon: Info,
        tone: 'primary',
      });
    }
  }
  if (network?.sampled) {
    insights.push({
      title: 'Network preview is sampled',
      description: `${formatCount(network.returned_nodes)} of ${formatCount(network.available_nodes)} nodes and ${formatCount(network.returned_edges)} of ${formatCount(network.available_edges)} edges are shown.`,
      icon: Database,
      tone: 'warning',
    });
  }
  const themeTotal = overview.top_themes.reduce((sum, theme) => sum + theme.count, 0);
  const leadingTheme = overview.top_themes[0];
  if (leadingTheme && themeTotal > 0 && leadingTheme.count / themeTotal >= 0.5) {
    insights.push({
      title: 'Concentrated leading theme',
      description: `${leadingTheme.name} accounts for ${formatCount((leadingTheme.count / themeTotal) * 100)}% of the returned top-theme counts.`,
      icon: PieChart,
      tone: 'primary',
    });
  }
  if (!hasTransitions) {
    insights.push({
      title: 'No transition artifact',
      description: 'This run does not list community_transitions, so longitudinal transition analysis is unavailable.',
      icon: AlertCircle,
      tone: 'neutral',
    });
  }

  const provider = metadataValue(overview.model_metadata, [
    'configured_primary_provider',
    'provider',
  ]);
  const model = metadataValue(overview.model_metadata, [
    'configured_primary_model',
    'model',
  ]);

  return (
    <aside className="flex flex-col gap-6 h-full">
      <section className="bg-panel border border-border rounded-xl p-5">
        <h3 className="text-sm font-bold text-text-heading flex items-center gap-2 mb-6 uppercase tracking-wider">
          <Lightbulb size={16} className="text-warning" />
          Traceable Insights
        </h3>
        <div className="flex flex-col gap-6">
          {insights.slice(0, 4).map((insight) => (
            <InsightItem key={insight.title} {...insight} />
          ))}
          {insights.length === 0 && (
            <InsightItem
              title="Run provenance"
              description="No deterministic insight threshold was triggered. Review the validated run metadata below."
              icon={Info}
              tone="neutral"
            />
          )}
        </div>
      </section>

      <section className="bg-panel border border-border rounded-xl p-5 flex-grow">
        <h3 className="text-sm font-bold text-text-heading mb-4 uppercase tracking-wider">Run Summary</h3>
        <dl className="flex flex-col gap-3 text-sm">
          <SummaryRow label="Time Range" value={formatRange(overview.date_start, overview.date_end)} />
          <SummaryRow label="Platform" value={overview.platform || selectedRun?.platform || 'Unavailable'} />
          <SummaryRow label="Content Type" value={overview.content_type || selectedRun?.content_type || 'Unavailable'} />
          <SummaryRow label="Affinity Metric" value={metric.toUpperCase()} />
          <SummaryRow label="Run Status" value={selectedRun?.status || 'Unavailable'} />
          <SummaryRow label="Artifacts" value={selectedRunDetail ? formatCount(selectedRunDetail.artifact_count) : 'Unavailable'} />
          <SummaryRow label="Theme Provider" value={provider || 'Unavailable'} />
          <SummaryRow label="Theme Model" value={model || 'Unavailable'} />
        </dl>
      </section>
    </aside>
  );
}

function SummaryRow({ label, value }) {
  return (
    <div className="flex justify-between gap-4 py-2 border-b border-border/50 last:border-0">
      <dt className="text-muted">{label}</dt>
      <dd className="font-medium text-text-heading text-right break-words">{value}</dd>
    </div>
  );
}

function formatRange(start, end) {
  if (!start && !end) return 'Unavailable';
  return `${start || 'Unknown'} – ${end || 'Unknown'}`;
}
