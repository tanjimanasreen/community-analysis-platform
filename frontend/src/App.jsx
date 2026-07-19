import React, { lazy, Suspense, useEffect, useState } from 'react';
import { Routes, Route, Outlet, BrowserRouter } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import LoadingState from './components/states/LoadingState';
import ErrorState from './components/states/ErrorState';
import EmptyState from './components/states/EmptyState';
import VerificationFailureState from './components/states/VerificationFailureState';
import { DashboardProvider } from './app/DashboardProvider';
import { useDashboardContext } from './hooks/useDashboardContext';

// Route pages are lazy so chart and graph vendors are not loaded on unrelated routes.
const Overview = lazy(() => import('./pages/Overview'));
const CommunityNetworkPage = lazy(() => import('./pages/CommunityNetwork'));
const ThematicAnalysisPage = lazy(() => import('./pages/ThematicAnalysis'));
const EvolutionOverTimePage = lazy(() => import('./pages/EvolutionOverTime'));
const ComparativeAnalysisPage = lazy(() => import('./pages/ComparativeAnalysis'));
const CommunityTransitionsPage = lazy(() => import('./pages/CommunityTransitions'));
const TopCommunitiesPage = lazy(() => import('./pages/TopCommunities'));
const DataExplorerPage = lazy(() => import('./pages/DataExplorer'));
const ReportsPage = lazy(() => import('./pages/Reports'));
const MethodologyPage = lazy(() => import('./pages/Methodology'));

function DashboardContent() {
  const {
    runs,
    selectedRun,
    verification,
    isLoading,
    isRunMetadataLoading,
    healthError,
    runsError,
    runDetailError,
    verificationError,
    retryInitial,
    retryRunMetadata,
  } = useDashboardContext();

  if (isLoading) {
    return <LoadingState title="Connecting to the dashboard API" />;
  }

  if (healthError || runsError) {
    return (
      <ErrorState
        error={healthError || runsError}
        title="Dashboard API unavailable"
        onRetry={retryInitial}
      />
    );
  }

  if (runs.length === 0) {
    return (
      <EmptyState
        title="No canonical runs found"
        message="Generate or publish a run bundle before opening analytical views."
      />
    );
  }

  if (selectedRun?.status === 'failed') {
    return (
      <EmptyState
        title="Selected run failed"
        message="This run did not complete, so analytical artifacts are unavailable. Select another run."
      />
    );
  }

  if (selectedRun?.status === 'running' || selectedRun?.status === 'pending') {
    return (
      <EmptyState
        title={`Selected run is ${selectedRun.status}`}
        message="Analytical artifacts become available only after the run completes."
      />
    );
  }

  if (isRunMetadataLoading) {
    return <LoadingState title="Verifying the selected run" />;
  }

  if (runDetailError || verificationError) {
    return (
      <ErrorState
        error={runDetailError || verificationError}
        title="Run metadata could not be loaded"
        onRetry={retryRunMetadata}
      />
    );
  }

  if (verification && !verification.ok) {
    return <VerificationFailureState verification={verification} />;
  }

  return <Outlet />;
}

function DashboardLayout() {
  const {
    runs,
    selectedRunId,
    metric,
    health,
    selectedRun,
    verification,
    setSelectedRunId,
    setMetric,
  } = useDashboardContext();

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

  return (
    <div className="flex h-screen w-full bg-bg overflow-hidden text-text font-sans">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[70] focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to main content
      </a>

      {!isSidebarCollapsed && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsSidebarCollapsed(true)}
        />
      )}

      <Sidebar
        isCollapsed={isSidebarCollapsed}
        toggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        onNavigate={() => {
          if (typeof window !== 'undefined' && window.innerWidth < 1024) {
            setIsSidebarCollapsed(true);
          }
        }}
      />

      <div className="flex-1 flex flex-col transition-all duration-300 overflow-hidden relative w-full">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-secondary/20 rounded-full blur-[100px] pointer-events-none" />

        <Topbar
          selectedRunId={selectedRunId}
          runs={runs}
          onRunChange={setSelectedRunId}
          metric={metric}
          onMetricChange={setMetric}
          health={health}
          selectedRun={selectedRun}
          verification={verification}
          toggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />

        <main id="main-content" tabIndex={-1} className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 z-10 w-full overflow-x-hidden">
          <Suspense fallback={<LoadingState title="Loading dashboard route" />}><DashboardContent /></Suspense>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <DashboardProvider>
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
      </DashboardProvider>
    </BrowserRouter>
  );
}
