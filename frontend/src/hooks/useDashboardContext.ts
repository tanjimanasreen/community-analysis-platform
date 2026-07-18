import { useContext } from 'react';
import { DashboardContext } from '../app/dashboardContext';

export function useDashboardContext() {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error('useDashboardContext must be used inside DashboardProvider.');
  }
  return context;
}
