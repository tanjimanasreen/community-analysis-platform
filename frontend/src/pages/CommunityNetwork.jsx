import { useOutletContext } from 'react-router-dom';
import { Network, Share2, Users, GitCommit, X, ExternalLink } from 'lucide-react';
import NetworkGraph from '../components/charts/NetworkGraph';
import NotableCommunitiesTable from '../components/NotableCommunitiesTable';

export default function CommunityNetworkPage() {
  const { communities } = useOutletContext();

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric Cards */}
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500">
              <Network size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted">Total Nodes</p>
              <h3 className="text-2xl font-bold text-text-heading">12,458</h3>
            </div>
          </div>
          <p className="text-xs text-muted">Unique accounts</p>
        </div>
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-500">
              <Share2 size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted">Total Edges</p>
              <h3 className="text-2xl font-bold text-text-heading">78,932</h3>
            </div>
          </div>
          <p className="text-xs text-muted">Connections</p>
        </div>
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center text-green-500">
              <Users size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted">Detected Communities</p>
              <h3 className="text-2xl font-bold text-text-heading">32</h3>
            </div>
          </div>
          <p className="text-xs text-muted">Communities</p>
        </div>
        <div className="bg-panel border border-border rounded-xl p-4 flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-500">
              <GitCommit size={20} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted">Average Degree</p>
              <h3 className="text-2xl font-bold text-text-heading">12.68</h3>
            </div>
          </div>
          <p className="text-xs text-muted">Connections per node</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 lg:h-[600px]">
        <div className="xl:col-span-2 h-[400px] lg:h-full">
          <NetworkGraph communities={communities} />
        </div>
        <div className="bg-panel border border-border rounded-xl p-6 lg:h-full flex flex-col overflow-y-auto">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-text-heading flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-purple-500"></span> Selected Community
            </h3>
            <button className="text-muted hover:text-text-heading"><X size={16} /></button>
          </div>
          
          <div className="flex items-center gap-4 mb-6">
            <div className="w-14 h-14 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400">
              <Users size={24} />
            </div>
            <div>
              <h4 className="text-xl font-bold text-text-heading">Personal Support</h4>
              <p className="text-sm text-muted">Community ID: C-1124</p>
            </div>
          </div>

          <div className="flex flex-col gap-3 text-sm flex-1">
            <div className="flex justify-between border-b border-border/50 pb-2">
              <span className="text-muted">Theme</span>
              <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 font-medium text-xs">Personal Support</span>
            </div>
            <div className="flex justify-between border-b border-border/50 pb-2">
              <span className="text-muted">Primary Platform</span>
              <span className="text-text-heading flex items-center gap-2">
                <span className="text-primary text-base leading-none">✈</span> Telegram
              </span>
            </div>
            <div className="flex justify-between border-b border-border/50 pb-2">
              <span className="text-muted">Size (Nodes)</span>
              <span className="text-text-heading font-medium">1,892</span>
            </div>
            <div className="flex justify-between border-b border-border/50 pb-2">
              <span className="text-muted">Persistence Score (WIF)</span>
              <span className="text-text-heading font-medium flex items-center gap-2">
                0.82 <span className="text-success text-xs font-medium">↑ 15.3%</span>
              </span>
            </div>
            <div className="flex justify-between pb-2">
              <span className="text-muted">Total Messages</span>
              <span className="text-text-heading font-medium">320,154 <span className="text-muted font-normal text-xs ml-1">18.6% of total</span></span>
            </div>
            
            <div className="mt-4 border-t border-border/50 pt-4">
              <p className="text-sm font-bold text-text-heading mb-3">Platform Mix</p>
              <div className="h-3 rounded-full bg-panel-soft flex overflow-hidden">
                <div className="h-full bg-purple-500" style={{ width: '72%' }}></div>
                <div className="h-full bg-blue-500" style={{ width: '18%' }}></div>
                <div className="h-full bg-gray-500" style={{ width: '10%' }}></div>
              </div>
              <div className="flex justify-between mt-3 text-xs text-muted font-medium">
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-purple-500"></span> Telegram 72%</span>
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-500"></span> Twitter/X 18%</span>
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-gray-500"></span> Other 10%</span>
              </div>
            </div>
            
            <div className="mt-6">
              <p className="text-sm font-bold text-text-heading mb-3">Top Linked Communities</p>
              <div className="flex flex-col gap-3">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full border border-purple-500/30 text-purple-500 flex items-center justify-center text-[10px] font-bold">1</div>
                    <span className="text-text-heading">Current Events (C-0789)</span>
                  </div>
                  <span className="font-bold">0.74</span>
                </div>
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full border border-blue-500/30 text-blue-500 flex items-center justify-center text-[10px] font-bold">2</div>
                    <span className="text-text-heading">News Discussion (C-0312)</span>
                  </div>
                  <span className="font-bold">0.62</span>
                </div>
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full border border-green-500/30 text-green-500 flex items-center justify-center text-[10px] font-bold">3</div>
                    <span className="text-text-heading">Civic Discourse (C-0561)</span>
                  </div>
                  <span className="font-bold">0.58</span>
                </div>
              </div>
            </div>
            
            <button className="w-full mt-6 flex items-center justify-center gap-2 py-2.5 border border-border rounded-lg text-sm font-semibold text-primary hover:bg-panel-soft transition-colors">
              View Community Details <ExternalLink size={14} />
            </button>
          </div>
        </div>
      </div>

      <div>
        <NotableCommunitiesTable />
      </div>
    </div>
  );
}
