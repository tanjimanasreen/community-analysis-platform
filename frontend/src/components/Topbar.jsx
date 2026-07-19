import React from 'react';
import { Activity, Calendar, HelpCircle, Menu } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import ArtifactStatusBadge from './ArtifactStatusBadge';
import { conciseRunId } from '../features/overview/overviewUtils';

const routeCopy = {
  '/': ['Overview Dashboard', 'Monitor validated run metrics and community structure.'],
  '/network': ['Community Network', 'Explore the structure of online communities and how they are connected.'],
  '/thematic': ['Thematic Analysis', 'Inspect LDA topics and downstream theme labels for the selected run.'],
  '/evolution': ['Evolution Over Time', 'Track compatible completed runs and longitudinal artifacts.'],
  '/comparative': ['Comparative Analysis', 'Compare compatible platform runs using shared analytical definitions.'],
  '/transitions': ['Community Transitions', 'Inspect member overlap and community paths across time.'],
  '/top-communities': ['Top Communities', 'Rank communities using canonical structural fields.'],
  '/data': ['Data Explorer', 'Inspect run-scoped analytical records and artifacts.'],
  '/reports': ['Reports', 'Browse read-only generated reports and artifacts.'],
  '/methodology': ['Methodology', 'Understand the analytical pipeline, data model, and configured methods.'],
};

export default function Topbar({
  selectedRunId,
  selectedRun,
  runs,
  onRunChange,
  metric,
  onMetricChange,
  health,
  verification,
  toggleSidebar,
}) {
  const location = useLocation();
  const [title, subtitle] = routeCopy[location.pathname] || routeCopy['/'];
  const showMetric = !['/thematic', '/transitions', '/reports', '/methodology'].includes(location.pathname);
  const helpTarget = `/methodology${location.search}`;

  return (
    <header className="flex flex-col gap-4 py-4 px-4 lg:px-8 border-b border-border bg-bg/80 backdrop-blur-md sticky top-0 z-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={toggleSidebar}
            aria-label="Open navigation"
            className="lg:hidden p-2 text-muted hover:text-text-heading bg-panel border border-border rounded-lg"
          >
            <Menu size={20} />
          </button>
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-text-heading">{title}</h1>
            <p className="text-xs md:text-sm text-muted mt-1 hidden sm:block">{subtitle}</p>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2 self-end sm:self-auto">
          {health && (
            <ArtifactStatusBadge
              label={`API ${health.status}`}
              status={health.status === 'ok' || health.status === 'healthy' ? 'healthy' : 'neutral'}
              title={`Read-only API schema ${health.schema_version}`}
            />
          )}
          {verification && (
            <ArtifactStatusBadge
              label={verification.ok ? 'Run verified' : 'Verification failed'}
              status={verification.ok ? 'verified' : 'warning'}
              title={verification.ok
                ? `${verification.checked_artifacts} artifacts verified`
                : verification.error || 'Artifact integrity verification failed'}
            />
          )}
          <Link
            to={helpTarget}
            aria-label="Open methodology help"
            className="p-2 text-muted hover:text-text-heading hover:bg-panel-soft rounded-lg transition-colors"
          >
            <HelpCircle size={20} />
          </Link>
        </div>
      </div>

      <div className="flex flex-col md:flex-row md:flex-wrap items-start md:items-center gap-2 pb-2 md:pb-0">
        <div className="flex flex-wrap bg-panel border border-border rounded-lg p-1 shadow-sm w-full md:w-auto">
          <label className={`flex items-center px-3 py-1.5 gap-2 ${showMetric ? 'border-r border-border' : ''}`}>
            <Calendar size={16} className="text-muted" aria-hidden="true" />
            <span className="sr-only">Analysis run</span>
            <select
              aria-label="Analysis run"
              className="bg-transparent border-none text-sm text-text-heading font-medium focus:outline-none cursor-pointer pr-4 max-w-[22rem]"
              value={selectedRunId}
              onChange={(event) => onRunChange(event.target.value)}
              disabled={runs.length === 0}
            >
              {runs.length === 0 && <option value="">No completed runs available</option>}
              {runs.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {formatRunLabel(run)}
                </option>
              ))}
            </select>
          </label>

          {showMetric && (
            <label className="flex items-center px-3 py-1.5 gap-2">
              <Activity size={16} className="text-secondary" aria-hidden="true" />
              <span className="sr-only">Affinity metric</span>
              <select
                aria-label="Affinity metric"
                className="bg-transparent border-none text-sm text-text-heading font-medium focus:outline-none cursor-pointer pr-4"
                value={metric}
                onChange={(event) => onMetricChange(event.target.value)}
              >
                <option value="if">Interaction Frequency (IF)</option>
                <option value="wif">Weighted Interaction Frequency (WIF)</option>
              </select>
            </label>
          )}
        </div>
        {selectedRun && (
          <span className="text-xs text-muted" title={selectedRun.run_id} aria-live="polite">
            Selected run: {conciseRunId(selectedRun.run_id)}
          </span>
        )}
      </div>
    </header>
  );
}

function formatRunLabel(run) {
  const platform = run.platform || 'unknown platform';
  const contentType = run.content_type || 'unknown content';
  const dateRange = run.date_start || run.date_end
    ? `${run.date_start || 'unknown'} → ${run.date_end || 'unknown'}`
    : run.year && run.month
      ? `${run.year}-${String(run.month).padStart(2, '0')}`
      : 'undated';
  return `${platform} · ${contentType} · ${dateRange} · ${conciseRunId(run.run_id)}`;
}
