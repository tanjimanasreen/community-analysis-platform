import { createContext } from 'react';
import type {
  HealthResponse,
  MetricName,
  RunDetail,
  RunSummary,
  VerificationResponse,
} from '../types/api';
import type { RunFacets } from './dashboardSearchParams';

export interface DashboardContextValue {
  health: HealthResponse | null;
  runs: RunSummary[];
  selectedRunId: string;
  selectedRun: RunSummary | null;
  selectedRunDetail: RunDetail | null;
  verification: VerificationResponse | null;
  metric: MetricName;
  facets: RunFacets;
  isLoading: boolean;
  isRunMetadataLoading: boolean;
  healthError: unknown;
  runsError: unknown;
  runDetailError: unknown;
  verificationError: unknown;
  setSelectedRunId: (runId: string) => void;
  selectedPlatform: string;
  setSelectedPlatform: (platform: string) => void;
  setMetric: (metric: MetricName) => void;
  retryInitial: () => void;
  retryRunMetadata: () => void;
}

export const DashboardContext = createContext<DashboardContextValue | null>(null);
