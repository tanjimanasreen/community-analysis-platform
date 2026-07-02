import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Database,
  FileText,
  ShieldCheck,
} from 'lucide-react';
import { api, API_BASE_URL } from './api';
import './index.css';

const PAGE_LIMIT = 100;

function formatValue(value) {
  if (value === null || value === undefined || value === '') return '—';
  if (Array.isArray(value)) return value.length ? value.join(', ') : '[]';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function numberValue(value) {
  if (typeof value === 'number') return value.toLocaleString();
  if (value && typeof value === 'object') {
    const firstNumber = Object.values(value).find((item) => typeof item === 'number');
    return firstNumber === undefined ? '0' : firstNumber.toLocaleString();
  }
  return value ? String(value) : '0';
}

function parseError(error) {
  return error?.response?.data?.detail || error?.message || 'Unknown error';
}

function StatusBadge({ ok, children }) {
  return (
    <span className={`status-badge ${ok ? 'ok' : 'warn'}`}>
      {ok ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
      {children}
    </span>
  );
}

function EmptyState({ title, detail }) {
  return (
    <div className="empty-state">
      <FileText size={24} />
      <strong>{title}</strong>
      {detail && <span>{detail}</span>}
    </div>
  );
}

function PaginationControls({ table, onPrev, onNext }) {
  const total = table?.total || 0;
  const offset = table?.offset || 0;
  const limit = table?.limit || PAGE_LIMIT;
  const canPrev = offset > 0;
  const canNext = offset + limit < total;

  return (
    <div className="pagination">
      <span>
        {total === 0 ? '0 records' : `${offset + 1}-${Math.min(offset + limit, total)} of ${total}`}
      </span>
      <button type="button" onClick={onPrev} disabled={!canPrev}>
        Previous
      </button>
      <button type="button" onClick={onNext} disabled={!canNext}>
        Next
      </button>
    </div>
  );
}

function DataTable({ data, columns, emptyTitle = 'No records available' }) {
  const records = data?.records || [];
  const visibleColumns = columns || Array.from(new Set(records.flatMap((record) => Object.keys(record))));

  if (data?.missing) {
    return <EmptyState title="Optional artifact missing" detail={`${data.artifact || 'Artifact'} was not generated for this run.`} />;
  }
  if (!records.length) {
    return <EmptyState title={emptyTitle} detail="The artifact exists but contains no rows for this selection." />;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {visibleColumns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((record, index) => (
            <tr key={`${record.id || record.absolute_community || record.start_month_community || index}`}>
              {visibleColumns.map((column) => (
                <td key={column}>{formatValue(record[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <div className="panel metric-card">
      <span className="metric-title">{label}</span>
      <span className="metric-value">{numberValue(value)}</span>
    </div>
  );
}

function ModeSelector({ label, value, options, onChange }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function App() {
  const [health, setHealth] = useState(null);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [facets, setFacets] = useState({ months: [] });
  const [selectedMonth, setSelectedMonth] = useState('');
  const [verification, setVerification] = useState(null);
  const [summary, setSummary] = useState(null);
  const [communities, setCommunities] = useState(null);
  const [topics, setTopics] = useState(null);
  const [themes, setThemes] = useState(null);
  const [transitions, setTransitions] = useState(null);
  const [artifacts, setArtifacts] = useState([]);
  const [files, setFiles] = useState([]);
  const [communityMode, setCommunityMode] = useState('matched');
  const [topicMode, setTopicMode] = useState('matched');
  const [offsets, setOffsets] = useState({ communities: 0, topics: 0, themes: 0, transitions: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function loadInitial() {
      setLoading(true);
      setError('');
      try {
        const [healthData, runsData] = await Promise.all([api.getHealth(), api.getRuns()]);
        if (cancelled) return;
        setHealth(healthData);
        setRuns(runsData.runs || []);
        setSelectedRunId((runsData.runs || [])[0]?.run_id || '');
      } catch (initialError) {
        if (!cancelled) setError(`API unavailable: ${parseError(initialError)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadInitial();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedRunId) return;
    let cancelled = false;
    async function loadRunMetadata() {
      setLoading(true);
      setError('');
      try {
        const [facetData, verificationData, artifactData, fileData] = await Promise.all([
          api.getFacets(selectedRunId),
          api.getVerification(selectedRunId),
          api.getArtifacts(selectedRunId),
          api.getFiles(selectedRunId),
        ]);
        if (cancelled) return;
        setFacets(facetData);
        setVerification(verificationData);
        setArtifacts(artifactData.artifacts || []);
        setFiles(fileData.files || []);
        setSelectedMonth((current) => (facetData.months || []).includes(current) ? current : facetData.months?.[0] || '');
        setOffsets({ communities: 0, topics: 0, themes: 0, transitions: 0 });
      } catch (runError) {
        if (!cancelled) setError(`Could not load run metadata: ${parseError(runError)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadRunMetadata();
    return () => {
      cancelled = true;
    };
  }, [selectedRunId]);

  useEffect(() => {
    if (!selectedRunId || !selectedMonth) return;
    let cancelled = false;
    async function loadMonthData() {
      setLoading(true);
      setError('');
      try {
        const [summaryData, communitiesData, topicsData, themesData, transitionsData] = await Promise.all([
          api.getCommunitySummary(selectedRunId, selectedMonth),
          api.getCommunities(selectedRunId, {
            month: selectedMonth,
            matchType: communityMode,
            limit: PAGE_LIMIT,
            offset: offsets.communities,
          }),
          api.getTopics(selectedRunId, {
            month: selectedMonth,
            type: topicMode,
            limit: PAGE_LIMIT,
            offset: offsets.topics,
          }),
          api.getThemes(selectedRunId, {
            month: selectedMonth,
            limit: PAGE_LIMIT,
            offset: offsets.themes,
          }),
          api.getTransitions(selectedRunId, {
            limit: PAGE_LIMIT,
            offset: offsets.transitions,
          }),
        ]);
        if (cancelled) return;
        setSummary(summaryData);
        setCommunities(communitiesData);
        setTopics(topicsData);
        setThemes(themesData);
        setTransitions(transitionsData);
      } catch (dataError) {
        if (!cancelled) setError(`Could not load dashboard data: ${parseError(dataError)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadMonthData();
    return () => {
      cancelled = true;
    };
  }, [selectedRunId, selectedMonth, communityMode, topicMode, offsets]);

  const selectedRun = useMemo(
    () => runs.find((run) => run.run_id === selectedRunId),
    [runs, selectedRunId],
  );

  const changeOffset = useCallback((table, direction) => {
    setOffsets((current) => ({
      ...current,
      [table]: Math.max(0, current[table] + direction * PAGE_LIMIT),
    }));
  }, []);

  const resetTable = useCallback((tableSetter, value, tableName) => {
    tableSetter(value);
    setOffsets((current) => ({ ...current, [tableName]: 0 }));
  }, []);

  const matchedSummary = summary?.matched_summary || {};
  const userMessageCounts = summary?.user_message_counts || {};
  const messages = userMessageCounts.messages || {};
  const users = userMessageCounts.user || {};
  const transitionRows = transitions?.records || [];
  const availableFiles = files.filter((file) => file.exists);
  const missingFiles = files.filter((file) => !file.exists);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Community Analysis</p>
          <h1>Artifact Dashboard</h1>
        </div>
        <div className="status-row">
          <StatusBadge ok={Boolean(health)}>
            {health ? `API ${health.status}` : 'API offline'}
          </StatusBadge>
          <StatusBadge ok={health?.read_only !== false}>Read-only</StatusBadge>
          {verification && (
            <StatusBadge ok={verification.ok}>
              {verification.ok ? 'Contract verified' : 'Verification failed'}
            </StatusBadge>
          )}
        </div>
      </header>

      <main className="main-content">
        <section className="panel controls-panel">
          <ModeSelector
            label="Run"
            value={selectedRunId}
            options={runs.map((run) => ({ value: run.run_id, label: run.run_id }))}
            onChange={setSelectedRunId}
          />
          <ModeSelector
            label="Month"
            value={selectedMonth}
            options={(facets.months || []).map((month) => ({ value: month, label: month }))}
            onChange={(value) => {
              setSelectedMonth(value);
              setOffsets({ communities: 0, topics: 0, themes: 0, transitions: 0 });
            }}
          />
          <div className="run-meta">
            <Database size={18} />
            <span>{selectedRun?.data_type || '—'}</span>
            <span>{selectedRun?.content_type || '—'}</span>
            <span>{selectedRun?.year || '—'}</span>
          </div>
          <div className="api-base">
            <Activity size={18} />
            <span>{API_BASE_URL}</span>
          </div>
        </section>

        {loading && <div className="panel loading">Loading generated artifacts…</div>}
        {error && (
          <div className="panel error-panel">
            <AlertTriangle size={20} />
            <span>{error}</span>
          </div>
        )}
        {!loading && !error && !runs.length && (
          <EmptyState title="No configured runs" detail="Start the read-only API with configured sample outputs." />
        )}

        {selectedRunId && (
          <>
            <section className="grid-overview">
              <MetricCard label="Users (absolute)" value={users.absolute} />
              <MetricCard label="Messages (absolute)" value={messages.absolute} />
              <MetricCard label="Absolute communities" value={matchedSummary.total_absolute} />
              <MetricCard label="Matched communities" value={matchedSummary.total_matched} />
            </section>

            <section className="panel verification-panel">
              <div>
                <h2>Output Contract</h2>
                <p>
                  {verification?.ok
                    ? `${verification.checked_count} artifacts checked; ${verification.skipped_optional_count} optional artifacts missing.`
                    : verification?.error || 'Verification has not completed.'}
                </p>
              </div>
              <ShieldCheck size={28} className={verification?.ok ? 'icon-ok' : 'icon-warn'} />
            </section>

            <section className="panel">
              <div className="section-header">
                <h2>Communities</h2>
                <ModeSelector
                  label="Match type"
                  value={communityMode}
                  options={[
                    { value: 'matched', label: 'Matched' },
                    { value: 'partial', label: 'Partial' },
                  ]}
                  onChange={(value) => resetTable(setCommunityMode, value, 'communities')}
                />
              </div>
              <DataTable data={communities} />
              <PaginationControls
                table={communities}
                onPrev={() => changeOffset('communities', -1)}
                onNext={() => changeOffset('communities', 1)}
              />
            </section>

            <section className="panel">
              <div className="section-header">
                <h2>LDA Topics</h2>
                <ModeSelector
                  label="Topic output"
                  value={topicMode}
                  options={[
                    { value: 'matched', label: 'Matched' },
                    { value: 'partial', label: 'Partial' },
                    { value: 'scores', label: 'Scores' },
                  ]}
                  onChange={(value) => resetTable(setTopicMode, value, 'topics')}
                />
              </div>
              <DataTable data={topics} />
              <PaginationControls
                table={topics}
                onPrev={() => changeOffset('topics', -1)}
                onNext={() => changeOffset('topics', 1)}
              />
            </section>

            <section className="panel">
              <div className="section-header">
                <h2>GPT Themes</h2>
                <span className="muted">Downstream of LDA keywords</span>
              </div>
              <DataTable
                data={themes}
                columns={[
                  'absolute_community',
                  'weighted_community',
                  'members',
                  'general_theme_names',
                  'absolute_theme_names',
                  'weighted_theme_names',
                  'all_keywords',
                ]}
              />
              <PaginationControls
                table={themes}
                onPrev={() => changeOffset('themes', -1)}
                onNext={() => changeOffset('themes', 1)}
              />
            </section>

            <section className="panel">
              <div className="section-header">
                <h2>Community Transitions</h2>
                <span className="muted">{transitionRows.length} rows loaded</span>
              </div>
              <DataTable
                data={transitions}
                columns={[
                  'start_month',
                  'end_month',
                  'start_month_community',
                  'end_month_community',
                  'jaccard_score',
                  'common_members',
                  'start_month_general_theme',
                  'end_month_general_theme',
                ]}
              />
              <PaginationControls
                table={transitions}
                onPrev={() => changeOffset('transitions', -1)}
                onNext={() => changeOffset('transitions', 1)}
              />
            </section>

            <section className="panel">
              <div className="section-header">
                <h2>Artifact Metadata</h2>
                <span className="muted">{artifacts.length} known artifacts</span>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Class</th>
                      <th>Path</th>
                      <th>Status</th>
                      <th>Size</th>
                    </tr>
                  </thead>
                  <tbody>
                    {artifacts.map((artifact) => (
                      <tr key={`${artifact.name}-${artifact.relative_path}`}>
                        <td>{artifact.name}</td>
                        <td>{artifact.classification}</td>
                        <td>{artifact.relative_path}</td>
                        <td>{artifact.exists ? 'available' : artifact.required ? 'missing' : 'optional missing'}</td>
                        <td>{artifact.size_bytes ? `${artifact.size_bytes} B` : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="panel">
              <div className="section-header">
                <h2>Optional Visualization Files</h2>
                <span className="muted">{availableFiles.length} available</span>
              </div>
              <div className="file-grid">
                {files.map((file) => (
                  <div key={`${file.category}-${file.relative_path}`} className={`file-card ${file.exists ? 'available' : ''}`}>
                    <strong>{file.category}</strong>
                    <span>{file.exists ? file.relative_path : 'Not generated for this sample'}</span>
                  </div>
                ))}
              </div>
              {missingFiles.length > 0 && (
                <p className="muted">Missing optional files are expected when visual rendering is disabled.</p>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
