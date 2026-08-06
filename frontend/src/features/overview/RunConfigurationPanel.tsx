import { Settings2 } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import ArtifactValue from '../../components/ArtifactValue';
import type { MetricName, OverviewResponse, RunSummary } from '../../types/api';
import { formatPeriod } from './overviewUtils';

interface RunConfigurationPanelProps {
  overview: OverviewResponse;
  metric: MetricName;
  selectedRun: RunSummary | null;
}

interface ConfigurationGroup {
  title: string;
  fields: Array<[string, unknown]>;
}

export default function RunConfigurationPanel({
  overview,
  metric,
  selectedRun,
}: RunConfigurationPanelProps) {
  const location = useLocation();
  const metadata = overview.config_metadata ?? {};
  const groups: ConfigurationGroup[] = [
    {
      title: 'Analysis scope',
      fields: [
        ['Platform', overview.platform ?? selectedRun?.platform],
        ['Content type', overview.content_type ?? selectedRun?.content_type],
        ['Analysis period', formatRange(overview.available_periods ?? [])],
        ['Monthly snapshots', overview.available_periods?.length ?? null],
        ['Selected metric', metric.toUpperCase()],
        ['Run status', selectedRun?.status],
      ],
    },
    {
      title: 'Graph and community settings',
      fields: entriesFor(metadata.graph_thresholds, {
        min_total_post: 'Minimum total posts',
        min_shared_post: 'Minimum shared posts',
        min_members: 'Minimum members',
      }).concat(entriesFor(metadata.louvain, {
        resolution: 'Louvain resolution',
        seed: 'Louvain seed',
      })),
    },
    {
      title: 'Topic settings',
      fields: entriesFor(metadata.lda, {
        num_topics: 'Number of topics',
        passes: 'Passes',
        iterations: 'Iterations',
        chunksize: 'Chunk size',
        random_state: 'Random state',
        alpha: 'Alpha',
        eta: 'Eta',
        top_n_keywords: 'Top keywords',
      }),
    },
    {
      title: 'Theme settings',
      fields: entriesFor(metadata.theme, {
        provider: 'Provider and model',
        similarity_model: 'Similarity model',
        similarity_model_name: 'Similarity model',
        transition_threshold: 'Transition threshold',
        reply_transition_threshold: 'Reply transition threshold',
        render_visuals: 'Render visuals',
        max_workers: 'Theme workers',
      }),
    },
  ];

  return (
    <details className="panel overview-details-panel" open>
      <summary>
        <span><Settings2 size={17} aria-hidden="true" /> Run Configuration</span>
        <span>Safe analytical settings only</span>
      </summary>
      <p className="overview-details-panel__intro">
        Values are read from the resolved run configuration. Credentials, cache paths, raw input paths, and local filesystem paths are intentionally omitted.{' '}
        <Link to={`/methodology${location.search}`}>Review methodology and metric definitions.</Link>
      </p>
      <div className="overview-config-grid">
        {groups.map((group) => (
          <section key={group.title}>
            <h3>{group.title}</h3>
            {group.fields.length > 0 ? (
              <dl>
                {dedupe(group.fields).map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd><ArtifactValue value={value ?? null} compact /></dd>
                  </div>
                ))}
              </dl>
            ) : <p className="overview-unavailable">Unavailable for this run</p>}
          </section>
        ))}
      </div>
    </details>
  );
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function entriesFor(value: unknown, labels: Record<string, string>): Array<[string, unknown]> {
  const record = objectValue(value);
  return Object.entries(labels)
    .filter(([key]) => Object.prototype.hasOwnProperty.call(record, key))
    .map(([key, label]) => [label, record[key]]);
}

function dedupe(entries: Array<[string, unknown]>): Array<[string, unknown]> {
  const seen = new Set<string>();
  return entries.filter(([label]) => {
    if (seen.has(label)) return false;
    seen.add(label);
    return true;
  });
}

function formatRange(periods: string[]): string {
  if (periods.length === 0) return 'Unavailable';
  return `${formatPeriod(periods[0])} – ${formatPeriod(periods.at(-1))}`;
}
