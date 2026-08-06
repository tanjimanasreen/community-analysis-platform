import React from 'react';
import { AlertTriangle, Database, Lightbulb, Scale, Send } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import ArtifactValue from '../components/ArtifactValue';
import ErrorState from '../components/states/ErrorState';
import LoadingState from '../components/states/LoadingState';
import EmptyState from '../components/states/EmptyState';
import {
  compareThemeLabels,
  comparisonMetricRows,
  deterministicComparisonFindings,
  formatMetric,
  platformRuns,
} from '../features/comparison/comparisonModel';
import { useComparisonData } from '../features/comparison/useComparisonData';
import { comparisonWarnings } from '../features/evolution/runCompatibility';

const TWITTER_RUN_PARAM = 'twitterRun';
const TELEGRAM_RUN_PARAM = 'telegramRun';

export default function ComparativeAnalysisPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const dashboard = useComparisonData(
    searchParams.get(TWITTER_RUN_PARAM) ?? '',
    searchParams.get(TELEGRAM_RUN_PARAM) ?? '',
  );
  const twitterOptions = platformRuns(dashboard.runs, 'twitter');
  const telegramOptions = platformRuns(dashboard.runs, 'telegram');
  const twitterRunId = twitterOptions.some((run) => run.run_id === searchParams.get(TWITTER_RUN_PARAM))
    ? searchParams.get(TWITTER_RUN_PARAM) ?? ''
    : '';
  const telegramRunId = telegramOptions.some((run) => run.run_id === searchParams.get(TELEGRAM_RUN_PARAM))
    ? searchParams.get(TELEGRAM_RUN_PARAM) ?? ''
    : '';
  const twitterRun = twitterOptions.find((run) => run.run_id === twitterRunId) ?? null;
  const telegramRun = telegramOptions.find((run) => run.run_id === telegramRunId) ?? null;

  const updateRun = (key, runId) => {
    const next = new URLSearchParams(searchParams);
    if (runId) next.set(key, runId);
    else next.delete(key);
    setSearchParams(next);
  };

  const selectionComplete = Boolean(twitterRun && telegramRun);
  const errors = [
    dashboard.twitterOverview.error,
    dashboard.telegramOverview.error,
    dashboard.twitterDetail.error,
    dashboard.telegramDetail.error,
    dashboard.twitterArtifacts.error,
    dashboard.telegramArtifacts.error,
  ].filter(Boolean);

  const twitterOverview = dashboard.twitterOverview.data;
  const telegramOverview = dashboard.telegramOverview.data;
  const comparisonReady = Boolean(selectionComplete && twitterOverview && telegramOverview);
  const rows = comparisonReady
    ? comparisonMetricRows(twitterOverview, telegramOverview, dashboard.metric)
    : [];
  const themes = comparisonReady
    ? compareThemeLabels(twitterOverview.top_themes, telegramOverview.top_themes)
    : null;
  const warnings = comparisonReady && twitterRun && telegramRun
    ? comparisonWarnings({
      leftRun: twitterRun,
      rightRun: telegramRun,
      leftOverview: twitterOverview,
      rightOverview: telegramOverview,
      leftArtifacts: dashboard.twitterArtifacts.data?.artifacts ?? [],
      rightArtifacts: dashboard.telegramArtifacts.data?.artifacts ?? [],
    })
    : [];
  const findings = comparisonReady
    ? deterministicComparisonFindings(rows, 'Twitter/X', 'Telegram')
    : [];

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <header className="panel p-5">
        <h1 className="text-xl font-bold text-text-heading">Cross-platform comparison</h1>
        <p className="mt-1 max-w-4xl text-sm text-muted">
          Select one completed Twitter/X run and one completed Telegram run. No arbitrary catalog entries are compared automatically.
        </p>
        <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <RunSelector
            label="Twitter/X run"
            icon={Scale}
            value={twitterRunId}
            options={twitterOptions}
            onChange={(value) => updateRun(TWITTER_RUN_PARAM, value)}
          />
          <RunSelector
            label="Telegram run"
            icon={Send}
            value={telegramRunId}
            options={telegramOptions}
            onChange={(value) => updateRun(TELEGRAM_RUN_PARAM, value)}
          />
        </div>
        <p className="mt-3 text-xs text-muted">Selected affinity metric: <span className="font-semibold text-text-heading">{dashboard.metric.toUpperCase()}</span>. Change it in the global top bar.</p>
      </header>

      {!selectionComplete ? (
        <EmptyState
          title="Select both platform runs"
          message="The comparison remains empty until explicit Twitter/X and Telegram runs are selected."
        />
      ) : dashboard.isLoading ? (
        <LoadingState title="Loading selected run comparison" />
      ) : errors.length > 0 ? (
        <ErrorState error={errors[0]} title="Selected runs could not be compared" />
      ) : comparisonReady ? (
        <>
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <RunSummaryCard title="Twitter/X" run={twitterRun} overview={twitterOverview} metric={dashboard.metric} accent="text-blue-500" />
            <RunSummaryCard title="Telegram" run={telegramRun} overview={telegramOverview} metric={dashboard.metric} accent="text-purple-500" />
          </div>

          {warnings.length > 0 && (
            <section className="rounded-xl border border-warning/30 bg-warning/5 p-5" aria-label="Comparison compatibility warnings">
              <div className="flex items-center gap-2">
                <AlertTriangle size={18} className="text-warning" />
                <h2 className="text-sm font-bold text-text-heading">Compatibility warnings</h2>
              </div>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-muted">
                {warnings.map((warning) => <li key={warning.code}>{warning.message}</li>)}
              </ul>
            </section>
          )}

          <section className="panel p-5">
            <h2 className="text-sm font-bold text-text-heading">Supported overview fields</h2>
            <p className="mt-1 text-xs text-muted">Only fields exposed by both selected run overviews are compared. Missing values remain unavailable.</p>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-border text-xs text-muted">
                  <tr><th className="px-3 py-3">Field</th><th className="px-3 py-3">Twitter/X</th><th className="px-3 py-3">Telegram</th><th className="px-3 py-3">Absolute difference</th></tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.key} className="border-b border-border/40">
                      <td className="px-3 py-3 font-medium text-text-heading">{row.label}</td>
                      <td className="px-3 py-3 text-text-heading">{formatMetric(row.left, row.format)}</td>
                      <td className="px-3 py-3 text-text-heading">{formatMetric(row.right, row.format)}</td>
                      <td className="px-3 py-3 text-muted">{row.left === null || row.right === null ? 'Unavailable' : formatMetric(Math.abs(row.left - row.right), row.format)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <ThemeComparison title="Twitter/X top theme labels" themes={themes.left} />
            <ThemeComparison title="Telegram top theme labels" themes={themes.right} />
          </div>

          <section className="panel p-5">
            <h2 className="text-sm font-bold text-text-heading">Exact normalized theme-label overlap</h2>
            <p className="mt-1 text-xs text-muted">This is exact label overlap after case and surrounding-whitespace normalization. It is not message-volume overlap or semantic similarity.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {themes.sharedNames.length > 0 ? themes.sharedNames.map((name) => (
                <span key={name} className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">{name}</span>
              )) : <span className="text-sm text-muted">No exact labels overlap in the returned top-theme sets.</span>}
            </div>
          </section>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <ConfigurationPanel
              title="Twitter/X configuration"
              overview={twitterOverview}
              detail={dashboard.twitterDetail.data}
              artifactCount={dashboard.twitterArtifacts.data?.total ?? null}
            />
            <ConfigurationPanel
              title="Telegram configuration"
              overview={telegramOverview}
              detail={dashboard.telegramDetail.data}
              artifactCount={dashboard.telegramArtifacts.data?.total ?? null}
            />
          </div>

          <section className="panel p-5">
            <div className="flex items-center gap-2">
              <Lightbulb size={18} className="text-primary" />
              <h2 className="text-sm font-bold text-text-heading">Deterministic findings</h2>
            </div>
            {findings.length > 0 ? (
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-muted">
                {findings.map((finding) => <li key={finding}>{finding}</li>)}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-muted">No supported numeric fields contain unequal values in both selected runs.</p>
            )}
            <p className="mt-4 text-xs text-muted">These statements report visible arithmetic differences only and make no causal claims.</p>
          </section>
        </>
      ) : null}
    </div>
  );
}

function RunSelector({ label, icon: Icon, value, options, onChange }) {
  return (
    <label className="rounded-xl border border-border bg-bg/30 p-4 text-xs font-medium text-muted">
      <span className="flex items-center gap-2"><Icon size={16} className="text-primary" /> {label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
         className="mt-2 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-heading"
      >
        <option value="">Select a completed run</option>
        {options.map((run) => (
          <option key={run.run_id} value={run.run_id}>
            {run.content_type ?? 'unknown'} · {run.date_start ?? 'unknown'}–{run.date_end ?? 'unknown'} · {run.run_id}
          </option>
        ))}
      </select>
      {options.length === 0 && <span className="mt-2 block text-xs text-warning">No completed runs for this platform are available.</span>}
    </label>
  );
}

function RunSummaryCard({ title, run, overview, metric, accent }) {
  const communityCount = metric === 'if' ? overview.if_community_count : overview.wif_community_count;
    return (
      <section className="panel p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className={`text-lg font-bold ${accent}`}>{title}</h2>
        <span className="rounded-full border border-border px-2 py-1 text-[11px] text-muted">{run.status}</span>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <SummaryItem label="Content type" value={run.content_type} />
        <SummaryItem label="Date range" value={`${run.date_start ?? 'Unknown'}–${run.date_end ?? 'Unknown'}`} />
        <SummaryItem label="Run ID" value={run.run_id} mono />
        <SummaryItem label={`${metric.toUpperCase()} communities`} value={communityCount} />
      </dl>
    </section>
  );
}

function SummaryItem({ label, value, mono = false }) {
  return (
     <div className="rounded-lg border border-border bg-surface-soft/40 p-3">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className={`mt-1 break-words font-semibold text-text-heading ${mono ? 'font-mono text-xs' : ''}`}>{value ?? 'Unavailable'}</dd>
    </div>
  );
}

function ThemeComparison({ title, themes }) {
    return (
      <section className="panel p-5">
      <h2 className="text-sm font-bold text-text-heading">{title}</h2>
      <div className="mt-4 space-y-3">
        {themes.map((theme) => (
           <div key={theme.name} className="flex items-center justify-between gap-4 rounded-lg border border-border bg-surface-soft/40 px-3 py-2 text-sm">
            <span className="text-text-heading">{theme.name}</span>
            <span className="font-semibold text-muted">{theme.count}</span>
          </div>
        ))}
        {themes.length === 0 && <p className="text-sm text-muted">No top theme labels are available.</p>}
      </div>
    </section>
  );
}

function ConfigurationPanel({ title, overview, detail, artifactCount }) {
  const entries = [
    ...flattenMetadata(overview.config_metadata, 'config'),
    ...flattenMetadata(overview.model_metadata, 'model'),
    ['pipeline.mlflow_run_id', detail?.pipeline?.mlflow_run_id],
    ['pipeline.prefect_flow_run_id', detail?.pipeline?.prefect_flow_run_id],
    ['artifact_count', artifactCount],
  ].filter(([, value]) => value !== null && value !== undefined && value !== '');
    return (
      <section className="panel p-5">
      <div className="flex items-center gap-2"><Database size={17} className="text-primary" /><h2 className="text-sm font-bold text-text-heading">{title}</h2></div>
      {entries.length > 0 ? (
        <dl className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {entries.map(([key, value]) => (
             <div key={key} className="rounded-lg border border-border bg-surface-soft/40 p-3">
               <dt className="break-all text-[11px] text-muted">{key}</dt>
               <dd className="mt-1 break-words text-sm font-semibold text-text-heading"><ArtifactValue value={value} /></dd>
             </div>
          ))}
        </dl>
      ) : <p className="mt-4 text-sm text-muted">Configuration and model metadata are unavailable.</p>}
    </section>
  );
}

function flattenMetadata(metadata, prefix) {
  const entries = [];
  for (const [section, value] of Object.entries(metadata ?? {})) {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      for (const [key, item] of Object.entries(value)) entries.push([`${prefix}.${section}.${key}`, item]);
    } else entries.push([`${prefix}.${section}`, value]);
  }
  return entries;
}
