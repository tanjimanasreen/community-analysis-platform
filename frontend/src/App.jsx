import { useEffect, useState } from 'react';
import { Routes, Route, Outlet, BrowserRouter } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import { api } from './api';

// Pages
import Overview from './pages/Overview';
import CommunityNetworkPage from './pages/CommunityNetwork';
import ThematicAnalysisPage from './pages/ThematicAnalysis';
import EvolutionOverTimePage from './pages/EvolutionOverTime';
import ComparativeAnalysisPage from './pages/ComparativeAnalysis';
import CommunityTransitionsPage from './pages/CommunityTransitions';
import TopCommunitiesPage from './pages/TopCommunities';
import DataExplorerPage from './pages/DataExplorer';
import ReportsPage from './pages/Reports';
import MethodologyPage from './pages/Methodology';

function DashboardLayout() {
  const [health, setHealth] = useState(null);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [facets, setFacets] = useState({ months: [] });
  const [selectedMonth, setSelectedMonth] = useState('');
  const [summary, setSummary] = useState(null);
  const [communities, setCommunities] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Sidebar state
  // Initialize sidebar collapsed state based on screen size
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth < 1024;
    }
    return false;
  });

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setIsSidebarCollapsed(true);
      } else {
        setIsSidebarCollapsed(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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
      } catch (err) {
        if (!cancelled) setError(`API unavailable: ${err?.message || 'Unknown error'}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadInitial();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!selectedRunId) return;
    let cancelled = false;
    async function loadRunMetadata() {
      try {
        const facetData = await api.getFacets(selectedRunId);
        if (cancelled) return;
        setFacets(facetData);
        setSelectedMonth((current) => (facetData.months || []).includes(current) ? current : facetData.months?.[0] || 'May \'24');
      } catch (err) {
        if (!cancelled) console.error("Facets error", err);
      }
    }
    loadRunMetadata();
    return () => { cancelled = true; };
  }, [selectedRunId]);

  useEffect(() => {
    if (!selectedRunId || !selectedMonth) return;
    let cancelled = false;
    async function loadMonthData() {
      try {
        const [summaryData, communitiesData] = await Promise.all([
          api.getCommunitySummary(selectedRunId, selectedMonth),
          api.getCommunities(selectedRunId, { month: selectedMonth, matchType: 'matched', limit: 10, offset: 0 })
        ]);
        if (cancelled) return;
        setSummary(summaryData);
        setCommunities(communitiesData);
      } catch (err) {
        if (!cancelled) console.error("Month data error", err);
      }
    }
    loadMonthData();
    return () => { cancelled = true; };
  }, [selectedRunId, selectedMonth]);

  return (
    <div className="flex h-screen w-full bg-bg overflow-hidden text-text font-sans">
      {/* Mobile Overlay */}
      {!isSidebarCollapsed && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsSidebarCollapsed(true)}
        ></div>
      )}

      {/* Sidebar handles its own fixed/static positioning */}
      <Sidebar isCollapsed={isSidebarCollapsed} toggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)} />

      <div className="flex-1 flex flex-col transition-all duration-300 overflow-hidden relative w-full">
        {/* Glow effects in the background */}
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 rounded-full blur-[120px] pointer-events-none"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-secondary/20 rounded-full blur-[100px] pointer-events-none"></div>

        <Topbar
          selectedMonth={selectedMonth}
          months={facets.months?.length ? facets.months : ['May 1 - May 31, 2024', 'Apr 1 - Apr 30, 2024']}
          onMonthChange={setSelectedMonth}
          health={health}
          dataToExport={communities}
          toggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />

        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 z-10 w-full overflow-x-hidden">
          <Outlet context={{ summary, communities, selectedMonth, selectedRunId }} />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardLayout />}>
          <Route index element={<Overview />} />
          <Route path="network" element={<CommunityNetworkPage />} />
          <Route path="thematic" element={<ThematicAnalysisPage />} />
          <Route path="evolution" element={<EvolutionOverTimePage />} />
          <Route path="comparative" element={<ComparativeAnalysisPage />} />
          <Route path="transitions" element={<CommunityTransitionsPage />} />
          <Route path="top-communities" element={<TopCommunitiesPage />} />
          <Route path="data" element={<DataExplorerPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="methodology" element={<MethodologyPage />} />
          <Route path="*" element={<Overview />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
