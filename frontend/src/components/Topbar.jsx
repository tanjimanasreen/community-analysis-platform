import { Calendar, Layers, Activity, Users, Filter, Download, Bell, HelpCircle, Menu, Search, Plus, FileText } from 'lucide-react';
import Papa from 'papaparse';
import { useLocation } from 'react-router-dom';

export default function Topbar({ selectedRunId, runs, onRunChange, metric, onMetricChange, health, dataToExport, toggleSidebar }) {
  const location = useLocation();
  const path = location.pathname;

  let title = "Overview Dashboard";
  let subtitle = "Monitor key metrics and explore the dynamics of online communities.";
  let showAffinity = true;
  let showMinSize = true;
  let showTopicGranularity = false;
  let showTimeGranularity = false;
  let showTransitionWindow = false;
  let showSortBy = false;
  let showSearch = false;
  let showReportTypes = false;
  let showCreateReport = false;
  let showFiltersRow = true;
  let filterCount = 2;

  if (path.includes('network')) {
    title = "Community Network";
    subtitle = "Explore the structure of online communities and how they are connected.";
  } else if (path.includes('thematic')) {
    title = "Thematic Analysis";
    subtitle = "Discover and analyze the key themes and topics that shape online conversations.";
    showAffinity = false;
    showMinSize = false;
    showTopicGranularity = true;
  } else if (path.includes('evolution')) {
    title = "Evolution Over Time";
    subtitle = "Track how communities, engagement, and persistence evolve across time.";
    showMinSize = false;
    showTimeGranularity = true;
  } else if (path.includes('transitions')) {
    title = "Community Transitions";
    subtitle = "Track how members move between communities over time and identify emerging or declining groups.";
    showAffinity = false;
    showTransitionWindow = true;
  } else if (path.includes('top-communities')) {
    title = "Top Communities";
    subtitle = "Discover and monitor the most influential communities across platforms.";
    showAffinity = false;
    showMinSize = false;
    showSortBy = true;
  } else if (path.includes('data')) {
    title = "Data Explorer";
    subtitle = "Explore community data, apply filters, and inspect detailed records.";
    showAffinity = false;
    showMinSize = false;
    showSearch = true;
    filterCount = 3;
  } else if (path.includes('reports')) {
    title = "Reports";
    subtitle = "Create, manage, and export insights about your community data.";
    showAffinity = false;
    showMinSize = false;
    showReportTypes = true;
    showCreateReport = true;
  } else if (path.includes('methodology')) {
    title = "Methodology";
    subtitle = "Understand the analytical pipeline, data model, and methods used to detect, compare, and track digital communities.";
    showFiltersRow = false;
  }

  const handleExport = () => {
    if (!dataToExport || !dataToExport.communities) {
      alert("No data available to export.");
      return;
    }

    // Flatten data for CSV
    const csvData = dataToExport.communities.map(c => ({
      CommunityID: c.community_id,
      Platform: c.platform,
      DominantTheme: c.dominant_theme,
      Size: c.size,
      Messages: c.metrics?.total_messages || 0,
      PersistenceWIF: c.metrics?.persistence_score_wif || 0,
      PersistenceAbs: c.metrics?.persistence_score_abs || 0,
      ThematicDiversity: c.metrics?.thematic_diversity || 0
    }));

    const csv = Papa.unparse(csvData);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `community_report_${selectedRunId || 'run'}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <header className="flex flex-col gap-4 py-4 px-4 lg:px-8 border-b border-border bg-bg/80 backdrop-blur-md sticky top-0 z-10">

      {/* Top Row: Title and Global Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button onClick={toggleSidebar} className="lg:hidden p-2 text-muted hover:text-text-heading bg-panel border border-border rounded-lg">
            <Menu size={20} />
          </button>
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-text-heading">{title}</h1>
            <div className="flex items-center gap-2 mt-1">
              <p className="text-xs md:text-sm text-muted hidden sm:block">{subtitle}</p>
              {health && (
                <span className="hidden md:inline-flex items-center rounded-full border border-border bg-panel px-2 py-0.5 text-[10px] font-medium text-muted">
                  API {health.status}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-4 self-end sm:self-auto">
          {showCreateReport ? (
            <>
              <button className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-semibold hover:bg-primary/90 transition-colors shadow-sm">
                <Plus size={16} />
                Create Report
              </button>
              <button onClick={handleExport} className="flex items-center gap-2 px-4 py-2 bg-white text-gray-900 border border-gray-200 rounded-lg text-sm font-semibold hover:bg-gray-100 transition-colors shadow-sm">
                <Download size={16} />
                Export All
              </button>
            </>
          ) : (
            <button onClick={handleExport} className="flex items-center gap-2 px-4 py-2 bg-white text-gray-900 border border-gray-200 rounded-lg text-sm font-semibold hover:bg-gray-100 transition-colors shadow-sm">
              <Download size={16} />
              Export Report
            </button>
          )}

          <button className="p-2 text-muted hover:text-text-heading hover:bg-panel-soft rounded-lg transition-colors relative">
            <Bell size={20} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-danger rounded-full"></span>
          </button>

          <button className="p-2 text-muted hover:text-text-heading hover:bg-panel-soft rounded-lg transition-colors">
            <HelpCircle size={20} />
          </button>
        </div>
      </div>

      {/* Bottom Row: Filters */}
      {showFiltersRow && (
        <div className="flex flex-col md:flex-row md:flex-wrap items-start md:items-center gap-2 md:gap-4 pb-2 md:pb-0">
          <div className="flex flex-wrap bg-panel border border-border rounded-lg p-1 shadow-sm w-full md:w-auto">
            {showSearch && (
              <div className="flex items-center px-3 py-1.5 gap-2 border-r border-border">
                <Search size={16} className="text-muted" />
                <input
                  type="text"
                  placeholder="Search communities..."
                  className="bg-transparent border-none text-sm text-text-heading placeholder-muted font-medium focus:outline-none w-48"
                />
              </div>
            )}

            <div className="flex items-center px-3 py-1.5 gap-2 border-r border-border">
              <Calendar size={16} className="text-muted" />
              <select
                aria-label="Analysis run"
                className="bg-transparent border-none text-sm text-text-heading font-medium focus:outline-none cursor-pointer appearance-none pr-4 max-w-[18rem]"
                value={selectedRunId}
                onChange={(e) => onRunChange(e.target.value)}
                disabled={runs.length === 0}
              >
                {runs.map((run) => (
                  <option key={run.run_id} value={run.run_id}>
                    {formatRunLabel(run)}
                  </option>
                ))}
              </select>
            </div>

            {showTransitionWindow && (
              <div className={`flex items-center px-3 py-1.5 gap-2 border-r border-border`}>
                <Activity size={16} className="text-blue-500" />
                <select className="bg-transparent border-none text-sm text-text-heading font-medium focus:outline-none cursor-pointer appearance-none pr-4">
                  <option>Transition Window: Monthly</option>
                  <option>Transition Window: Weekly</option>
                </select>
              </div>
            )}

            {!showReportTypes && (
              <div className={`flex items-center px-3 py-1.5 gap-2 ${showAffinity || showTopicGranularity || (showMinSize && !showTransitionWindow && !showSortBy) ? 'border-r border-border' : ''}`}>
                <Layers size={16} className="text-primary" />
                <select className="bg-transparent border-none text-sm text-text-heading font-medium focus:outline-none cursor-pointer appearance-none pr-4">
                  <option>Platforms: Both</option>
                  <option>Twitter/X</option>
                  <option>Telegram</option>
                </select>
              </div>
            )}

            {showReportTypes && (
              <div className={`flex items-center px-3 py-1.5 gap-2`}>
                <FileText size={16} className="text-primary" />
                <select className="bg-transparent border-none text-sm text-text-heading font-medium focus:outline-none cursor-pointer appearance-none pr-4">
                  <option>All Report Types</option>
                  <option>Overview</option>
                  <option>Growth</option>
                </select>
              </div>
            )}

            {showSortBy && (
              <div className={`flex items-center px-3 py-1.5 gap-2 border-r border-border`}>
                <Activity size={16} className="text-muted" />
                <select className="bg-transparent border-none text-sm text-text-heading font-medium focus:outline-none cursor-pointer appearance-none pr-4">
                  <option>Sort by: Messages (High to Low)</option>
                  <option>Sort by: Size (High to Low)</option>
                  <option>Sort by: Persistence (High to Low)</option>
                </select>
              </div>
            )}

            {showAffinity && (
              <div className={`flex items-center px-3 py-1.5 gap-2 hidden md:flex ${showMinSize || showTimeGranularity ? 'border-r border-border' : ''}`}>
                <Activity size={16} className="text-secondary" />
                <select
                  aria-label="Affinity metric"
                  className="bg-transparent border-none text-sm text-text-heading font-medium focus:outline-none cursor-pointer appearance-none pr-4"
                  value={metric}
                  onChange={(e) => onMetricChange(e.target.value)}
                >
                  <option value="if">Affinity Metric: IF</option>
                  <option value="wif">Affinity Metric: WIF</option>
                </select>
              </div>
            )}

            {showTopicGranularity && (
              <div className="flex items-center px-3 py-1.5 gap-2 hidden md:flex">
                <Activity size={16} className="text-secondary" />
                <select className="bg-transparent border-none text-sm text-text-heading font-medium focus:outline-none cursor-pointer appearance-none pr-4">
                  <option>Topic Granularity: Topics</option>
                  <option>Topic Granularity: Themes</option>
                </select>
              </div>
            )}

            {showTimeGranularity && (
              <div className="flex items-center px-3 py-1.5 gap-2 hidden lg:flex">
                <Calendar size={16} className="text-accent" />
                <select className="bg-transparent border-none text-sm text-text-heading font-medium focus:outline-none cursor-pointer appearance-none pr-4">
                  <option>Time Granularity: Day</option>
                  <option>Time Granularity: Week</option>
                  <option>Time Granularity: Month</option>
                </select>
              </div>
            )}

            {showMinSize && (
              <div className="flex items-center px-3 py-1.5 gap-2 hidden lg:flex">
                <Users size={16} className="text-accent" />
                <select className="bg-transparent border-none text-sm text-text-heading font-medium focus:outline-none cursor-pointer appearance-none pr-4">
                  <option>Min Community Size: 50</option>
                  <option>Min Community Size: 100</option>
                </select>
              </div>
            )}
          </div>

          {!showReportTypes && (
            <button className="flex items-center gap-2 px-4 py-2 bg-panel border border-border rounded-lg text-sm font-medium hover:bg-panel-soft transition-colors shadow-sm">
              <Filter size={16} className="text-muted" />
              Filters
              <span className="bg-primary text-white text-xs rounded-full w-5 h-5 flex items-center justify-center ml-1">{filterCount}</span>
            </button>
          )}
        </div>
      )}
    </header>
  );
}

function formatRunLabel(run) {
  const platform = run.platform || 'unknown platform';
  const contentType = run.content_type || 'unknown content';
  const period = run.year && run.month
    ? `${run.year}-${String(run.month).padStart(2, '0')}`
    : run.date_start || 'undated';
  return `${platform} · ${contentType} · ${period} · ${run.status}`;
}
