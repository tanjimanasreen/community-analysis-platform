import { useDashboardContext } from '../hooks/useDashboardContext';
import KPICards from '../components/KPICards';
import NetworkGraph from '../components/charts/NetworkGraph';
import EvolutionChart from '../components/charts/EvolutionChart';
import PlatformComparison from '../components/charts/PlatformComparison';
import TransitionsSankey from '../components/charts/TransitionsSankey';
import DataTable from '../components/DataTable';
import RightSidebar from '../components/RightSidebar';

export default function Overview() {
  const { selectedRunId } = useDashboardContext();
  const summary = undefined;
  const communities = undefined;

  return (
    <div data-run-id={selectedRunId || undefined} className="max-w-[1600px] mx-auto flex flex-col lg:flex-row gap-8">
      <div className="flex-1 flex flex-col gap-6 w-full overflow-hidden">

        <KPICards summary={summary} />

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-3">
            <NetworkGraph communities={communities} />
          </div>
          <div className="xl:col-span-2">
            <EvolutionChart />
          </div>
          <PlatformComparison />
          <div className="xl:col-span-3">
            <TransitionsSankey />
          </div>
        </div>

        <DataTable communities={communities} />

      </div>

      <div className="w-full lg:w-80 shrink-0">
        <RightSidebar summary={summary} />
      </div>
    </div>
  );
}
