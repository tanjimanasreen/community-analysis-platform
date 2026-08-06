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
    selectedPlatform,
    setSelectedPlatform,
    facets,
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
    <div className="h-screen max-h-screen w-full bg-bg text-text font-sans flex overflow-hidden relative selection:bg-primary/30 selection:text-white">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[110] focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to main content
      </a>

      {!isSidebarCollapsed && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[90] lg:hidden transition-all duration-300 animate-fade-in-up"
          onClick={() => setIsSidebarCollapsed(true)}
        />
      )}

      <div className="flex-1 flex w-full max-w-[1720px] mx-auto h-screen overflow-hidden">
        <Sidebar
          isCollapsed={isSidebarCollapsed}
          toggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          onNavigate={() => {
            if (typeof window !== 'undefined' && window.innerWidth < 1024) {
              setIsSidebarCollapsed(true);
            }
          }}
        />

        <div className="main-content flex-1 flex flex-col min-w-0 h-screen overflow-hidden relative w-full">
          <div className="absolute top-[-5%] left-[-5%] w-[45%] h-[45%] bg-primary/10 rounded-full blur-[140px] pointer-events-none" />
          <div className="absolute bottom-[-5%] right-[-5%] w-[35%] h-[35%] bg-secondary/10 rounded-full blur-[120px] pointer-events-none" />

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
            isSidebarCollapsed={isSidebarCollapsed}
            selectedPlatform={selectedPlatform}
            onPlatformChange={setSelectedPlatform}
            facets={facets}
          />

          <main id="main-content" tabIndex={-1} className="flex-1 overflow-y-auto p-3 sm:p-5 lg:p-6 z-10 w-full animate-fade-in-up">
            <Suspense fallback={<LoadingState title="Loading dashboard route" />}><DashboardContent /></Suspense>
          </main>
        </div>
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
