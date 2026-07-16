import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { Network, Star, X, Search, ChevronDown, Filter, ChevronLeft, ChevronRight, Settings, Info, MessageCircle, Send, MoreHorizontal, LayoutGrid } from 'lucide-react';

export default function DataExplorerPage() {
  const { summary } = useOutletContext() || {};
  const [selectedCommunity, setSelectedCommunity] = useState('C-1124');

  const communities = [
    { id: 'C-1124', platform: 'Telegram', theme: 'Personal Support', color: 'bg-purple-500', messages: '320,154', persistence: '0.82', trend: 1, updated: 'May 31, 2024 09:42' },
    { id: 'C-0789', platform: 'Twitter/X', theme: 'Current Events', color: 'bg-blue-500', messages: '410,982', persistence: '0.63', trend: 1, updated: 'May 31, 2024 09:21' },
    { id: 'C-0561', platform: 'Telegram', theme: 'Civic Discourse', color: 'bg-green-500', messages: '210,443', persistence: '0.74', trend: 1, updated: 'May 31, 2024 08:55' },
    { id: 'C-0312', platform: 'Twitter/X', theme: 'News Discussion', color: 'bg-orange-500', messages: '198,765', persistence: '0.58', trend: -1, updated: 'May 31, 2024 08:47' },
    { id: 'C-0098', platform: 'Telegram', theme: 'Education', color: 'bg-teal-500', messages: '156,332', persistence: '0.69', trend: 1, updated: 'May 31, 2024 08:31' },
    { id: 'C-1456', platform: 'Reddit', theme: 'Technology', color: 'bg-blue-600', messages: '98,721', persistence: '0.41', trend: -1, updated: 'May 31, 2024 08:12' },
    { id: 'C-2033', platform: 'Twitter/X', theme: 'Health & Wellness', color: 'bg-green-500', messages: '87,643', persistence: '0.72', trend: 1, updated: 'May 31, 2024 07:58' },
    { id: 'C-1770', platform: 'Telegram', theme: 'Finance', color: 'bg-orange-400', messages: '76,214', persistence: '0.45', trend: -1, updated: 'May 31, 2024 07:41' },
    { id: 'C-1922', platform: 'Discord', theme: 'Gaming', color: 'bg-indigo-600', messages: '65,987', persistence: '0.37', trend: -1, updated: 'May 31, 2024 07:22' },
    { id: 'C-0147', platform: 'Twitter/X', theme: 'Politics', color: 'bg-purple-600', messages: '54,391', persistence: '0.61', trend: 1, updated: 'May 31, 2024 07:11' },
    { id: 'C-0888', platform: 'Telegram', theme: 'Environment', color: 'bg-green-600', messages: '49,210', persistence: '0.53', trend: 1, updated: 'May 31, 2024 06:59' },
    { id: 'C-0675', platform: 'Reddit', theme: 'Science', color: 'bg-orange-600', messages: '41,672', persistence: '0.36', trend: -1, updated: 'May 31, 2024 06:44' },
    { id: 'C-1533', platform: 'Twitter/X', theme: 'Culture', color: 'bg-blue-600', messages: '38,105', persistence: '0.49', trend: 1, updated: 'May 31, 2024 06:30' },
    { id: 'C-0211', platform: 'Telegram', theme: 'Entrepreneurship', color: 'bg-purple-400', messages: '31,987', persistence: '0.42', trend: -1, updated: 'May 31, 2024 06:18' },
  ];

  const renderPlatformIcon = (platform) => {
    switch(platform) {
      case 'Telegram': return <Send size={12} className="text-blue-500" />;
      case 'Twitter/X': return <span className="font-serif italic font-bold">𝕏</span>;
      case 'Reddit': return <div className="w-3 h-3 rounded-full bg-orange-500 flex items-center justify-center text-white text-[8px] font-bold">R</div>;
      case 'Discord': return <div className="w-3 h-3 rounded-full bg-indigo-500 flex items-center justify-center text-white text-[8px] font-bold">D</div>;
      default: return <MessageCircle size={12} />;
    }
  };

  return (
    <div className="flex gap-4 max-w-[1800px] mx-auto w-full items-start">
      
      {/* Left Sidebar - Filters */}
      <div className="w-64 shrink-0 flex flex-col gap-5 sticky top-24">
        <div className="flex justify-between items-center">
          <h2 className="text-sm font-bold text-text-heading">Filters</h2>
          <button className="text-xs text-primary font-medium hover:underline">Reset all</button>
        </div>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-heading flex items-center gap-1">Platform <Info size={10} className="text-muted" /></label>
            <div className="relative">
              <select className="w-full bg-panel border border-border rounded-lg text-xs text-text-heading font-medium focus:outline-none appearance-none px-3 py-2">
                <option>All Platforms</option>
              </select>
              <ChevronDown size={14} className="absolute right-3 top-2.5 text-muted pointer-events-none" />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-heading flex items-center gap-1">Theme <Info size={10} className="text-muted" /></label>
            <div className="relative">
              <select className="w-full bg-panel border border-border rounded-lg text-xs text-text-heading font-medium focus:outline-none appearance-none px-3 py-2">
                <option>All Themes</option>
              </select>
              <ChevronDown size={14} className="absolute right-3 top-2.5 text-muted pointer-events-none" />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-heading flex items-center gap-1">Community Size <Info size={10} className="text-muted" /></label>
            <div className="flex gap-2">
              <input type="text" placeholder="Min" className="w-1/2 bg-panel border border-border rounded-lg text-xs text-text-heading font-medium px-3 py-2 outline-none" />
              <input type="text" placeholder="Max" className="w-1/2 bg-panel border border-border rounded-lg text-xs text-text-heading font-medium px-3 py-2 outline-none" />
            </div>
            <div className="mt-2 mb-1 px-1">
              <div className="h-1 bg-border rounded-full relative">
                <div className="absolute left-[10%] right-[30%] h-full bg-primary rounded-full"></div>
                <div className="absolute left-[10%] top-1/2 -translate-y-1/2 w-3 h-3 bg-primary rounded-full border-2 border-bg"></div>
                <div className="absolute right-[30%] top-1/2 -translate-y-1/2 w-3 h-3 bg-primary rounded-full border-2 border-bg"></div>
              </div>
            </div>
            <div className="flex justify-between text-[10px] text-muted font-medium px-1">
              <span>10</span>
              <span>100K+</span>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-heading flex items-center gap-1">Persistence (WIF) <Info size={10} className="text-muted" /></label>
            <div className="flex gap-2">
              <input type="text" placeholder="Min" className="w-1/2 bg-panel border border-border rounded-lg text-xs text-text-heading font-medium px-3 py-2 outline-none" />
              <input type="text" placeholder="Max" className="w-1/2 bg-panel border border-border rounded-lg text-xs text-text-heading font-medium px-3 py-2 outline-none" />
            </div>
            <div className="mt-2 mb-1 px-1">
              <div className="h-1 bg-border rounded-full relative">
                <div className="absolute left-[20%] right-[10%] h-full bg-primary rounded-full"></div>
                <div className="absolute left-[20%] top-1/2 -translate-y-1/2 w-3 h-3 bg-primary rounded-full border-2 border-bg"></div>
                <div className="absolute right-[10%] top-1/2 -translate-y-1/2 w-3 h-3 bg-primary rounded-full border-2 border-bg"></div>
              </div>
            </div>
            <div className="flex justify-between text-[10px] text-muted font-medium px-1">
              <span>0.00</span>
              <span>1.00</span>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-heading flex items-center gap-1">Time Window <Info size={10} className="text-muted" /></label>
            <div className="relative">
              <select className="w-full bg-panel border border-border rounded-lg text-xs text-text-heading font-medium focus:outline-none appearance-none px-3 py-2">
                <option>Last 30 Days</option>
              </select>
              <ChevronDown size={14} className="absolute right-3 top-2.5 text-muted pointer-events-none" />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-heading flex items-center gap-1">Community Status <Info size={10} className="text-muted" /></label>
            <div className="relative">
              <select className="w-full bg-panel border border-border rounded-lg text-xs text-text-heading font-medium focus:outline-none appearance-none px-3 py-2">
                <option>All Statuses</option>
              </select>
              <ChevronDown size={14} className="absolute right-3 top-2.5 text-muted pointer-events-none" />
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-2 mt-2">
          <button className="w-full py-2 bg-primary text-white rounded-lg text-sm font-semibold hover:bg-primary/90 transition-colors shadow-sm">
            Apply Filters
          </button>
          <button className="w-full py-2 border border-border bg-panel text-primary rounded-lg text-sm font-semibold hover:bg-panel-soft transition-colors flex items-center justify-center gap-2">
            <Filter size={14} /> Save Filter Set
          </button>
        </div>
      </div>

      {/* Main Center Table Area */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Active Filters Row */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 bg-panel border border-border rounded-full px-3 py-1 text-xs font-medium text-text-heading shadow-sm">
              Time: May 1 - May 31, 2024 <X size={12} className="text-muted cursor-pointer hover:text-text-heading ml-1" />
            </div>
            <div className="flex items-center gap-1 bg-panel border border-border rounded-full px-3 py-1 text-xs font-medium text-text-heading shadow-sm">
              Platforms: Both <X size={12} className="text-muted cursor-pointer hover:text-text-heading ml-1" />
            </div>
            <div className="flex items-center gap-1 bg-panel border border-border rounded-full px-3 py-1 text-xs font-medium text-text-heading shadow-sm">
              Min Size: 50 <X size={12} className="text-muted cursor-pointer hover:text-text-heading ml-1" />
            </div>
            <button className="text-xs text-primary font-semibold hover:underline ml-2">Clear all</button>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <select className="bg-panel border border-border rounded-lg text-xs text-text-heading font-medium focus:outline-none appearance-none pl-3 pr-8 py-1.5 shadow-sm">
                <option>Saved Views</option>
              </select>
              <ChevronDown size={14} className="absolute right-2 top-2 text-muted pointer-events-none" />
            </div>
            <button className="p-1.5 bg-panel border border-border rounded-lg text-muted hover:text-text-heading shadow-sm">
              <LayoutGrid size={16} />
            </button>
          </div>
        </div>

        {/* Results Header */}
        <div className="flex justify-between items-center mb-4">
          <p className="text-xs font-medium text-muted">1,248 results</p>
          <div className="relative w-48">
            <Search size={14} className="absolute left-3 top-2 text-muted" />
            <input 
              type="text" 
              placeholder="Search table..." 
              className="w-full bg-panel border border-border rounded-lg text-xs text-text-heading font-medium pl-8 pr-3 py-1.5 outline-none shadow-sm placeholder-muted"
            />
          </div>
        </div>

        {/* Table */}
        <div className="bg-panel border border-border rounded-xl flex flex-col overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs whitespace-nowrap">
              <thead>
                <tr className="border-b border-border text-text-heading font-bold bg-panel-soft">
                  <th className="py-3 px-4 w-10">
                    <input type="checkbox" className="rounded border-muted bg-transparent cursor-pointer" />
                  </th>
                  <th className="py-3 px-2 w-10"></th>
                  <th className="py-3 px-4 font-semibold">Community ID</th>
                  <th className="py-3 px-4 font-semibold">Platform</th>
                  <th className="py-3 px-4 font-semibold">Theme</th>
                  <th className="py-3 px-4 font-semibold text-center">Messages (May)</th>
                  <th className="py-3 px-4 font-semibold text-center">Persistence (WIF)</th>
                  <th className="py-3 px-4 font-semibold flex items-center gap-1 justify-end">Updated <ArrowRight size={12} className="rotate-90 text-muted" /></th>
                </tr>
              </thead>
              <tbody className="text-text font-medium">
                {communities.map((community, index) => (
                  <tr 
                    key={community.id} 
                    className={`border-b border-border/30 hover:bg-panel-soft transition-colors cursor-pointer ${selectedCommunity === community.id ? 'bg-primary/10' : ''}`}
                    onClick={() => setSelectedCommunity(community.id)}
                  >
                    <td className="py-3 px-4">
                      <input 
                        type="checkbox" 
                        className="rounded border-muted bg-transparent cursor-pointer" 
                        checked={selectedCommunity === community.id}
                        onChange={() => {}}
                      />
                    </td>
                    <td className="py-3 px-2 text-muted text-center">
                      {index === 0 ? <Star size={14} className="text-orange-400 fill-orange-400" /> : <Star size={14} />}
                    </td>
                    <td className="py-3 px-4 text-text-heading">{community.id}</td>
                    <td className="py-3 px-4 text-muted flex items-center gap-1.5 mt-0.5">
                      {renderPlatformIcon(community.platform)}
                      {community.platform}
                    </td>
                    <td className="py-3 px-4 text-text-heading">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${community.color}`}></div>
                        {community.theme}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-muted text-center">{community.messages}</td>
                    <td className="py-3 px-4 text-muted text-center">
                      <span className={community.trend > 0 ? 'text-success' : 'text-danger'}>
                        {community.trend > 0 ? '↑' : '↓'}
                      </span> {community.persistence}
                    </td>
                    <td className="py-3 px-4 text-muted text-right">{community.updated}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="p-3 flex items-center justify-between text-xs text-muted font-medium">
            <div className="flex items-center gap-2">
              Rows per page: 
              <select className="bg-transparent border border-border rounded text-text-heading outline-none cursor-pointer px-1 py-0.5">
                <option>25</option>
                <option>50</option>
                <option>100</option>
              </select>
            </div>
            <div className="flex items-center gap-1">
              <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded text-muted">←</button>
              <button className="w-6 h-6 flex items-center justify-center bg-primary/10 text-primary font-bold rounded">1</button>
              <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded">2</button>
              <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded">3</button>
              <span className="px-1">...</span>
              <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded">50</button>
              <button className="w-6 h-6 flex items-center justify-center hover:bg-panel-soft rounded text-text-heading">→</button>
            </div>
          </div>
        </div>
      </div>

      {/* Right Sidebar - Selected Record */}
      <div className="w-[320px] shrink-0 sticky top-24 h-[calc(100vh-120px)] overflow-y-auto hide-scrollbar pb-8">
        {selectedCommunity && (
          <div className="bg-panel border border-border rounded-xl shadow-sm flex flex-col p-5">
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
              <div className="flex gap-4">
                <div className="w-12 h-12 rounded-full bg-purple-500 text-white flex items-center justify-center shrink-0">
                  <Send size={24} />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-text-heading flex items-center gap-2">
                    {selectedCommunity} <Star size={14} className="text-orange-400 fill-orange-400" />
                  </h2>
                  <p className="text-xs text-muted font-medium mb-1.5">Telegram Community</p>
                  <span className="text-[10px] bg-purple-500/10 text-purple-500 font-semibold px-2 py-0.5 rounded-full border border-purple-500/20">
                    Personal Support
                  </span>
                </div>
              </div>
              <button onClick={() => setSelectedCommunity(null)} className="p-1 hover:bg-panel-soft rounded-lg text-muted transition-colors">
                <X size={16} />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-y-6 gap-x-4 mb-6 border-b border-border pb-6">
              <div>
                <p className="text-[10px] text-muted font-medium mb-1">Messages (May)</p>
                <p className="text-lg font-bold text-text-heading">320,154</p>
              </div>
              <div>
                <p className="text-[10px] text-muted font-medium mb-1">Persistence (WIF)</p>
                <p className="text-lg font-bold text-text-heading flex items-end gap-1">
                  0.82 <span className="text-[10px] text-success font-medium mb-1">↑ 15.3% vs Apr</span>
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted font-medium mb-1">Members</p>
                <p className="text-lg font-bold text-text-heading flex flex-col">
                  12,458
                  <span className="text-[10px] text-success font-medium mt-1">↑ 8.7% vs Apr</span>
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted font-medium mb-1">Avg Community Size</p>
                <p className="text-lg font-bold text-text-heading flex flex-col">
                  693
                  <span className="text-[10px] text-success font-medium mt-1">↑ 5.6% vs Apr</span>
                </p>
              </div>
            </div>

            <div className="mb-6">
              <h3 className="text-xs font-bold text-text-heading mb-2">About this community</h3>
              <p className="text-xs text-muted leading-relaxed">
                This Telegram community focuses on personal well-being, mental health support, and peer encouragement. Members share experiences, resources, and advice in a supportive environment.
              </p>
            </div>

            <div className="mb-6 border-b border-border pb-6">
              <h3 className="text-xs font-bold text-text-heading mb-3">Top Themes</h3>
              <div className="flex flex-col gap-2.5">
                <div className="flex items-center text-[10px]">
                  <div className="w-24 text-muted">Personal Support</div>
                  <div className="flex-1 mx-2 h-1.5 bg-bg rounded-full overflow-hidden">
                    <div className="h-full bg-purple-500 rounded-full" style={{ width: '52%' }}></div>
                  </div>
                  <div className="w-8 text-right font-medium text-text-heading">52%</div>
                </div>
                <div className="flex items-center text-[10px]">
                  <div className="w-24 text-muted">Emotional Topics</div>
                  <div className="flex-1 mx-2 h-1.5 bg-bg rounded-full overflow-hidden">
                    <div className="h-full bg-orange-400 rounded-full" style={{ width: '18%' }}></div>
                  </div>
                  <div className="w-8 text-right font-medium text-text-heading">18%</div>
                </div>
                <div className="flex items-center text-[10px]">
                  <div className="w-24 text-muted">Health & Wellness</div>
                  <div className="flex-1 mx-2 h-1.5 bg-bg rounded-full overflow-hidden">
                    <div className="h-full bg-teal-500 rounded-full" style={{ width: '14%' }}></div>
                  </div>
                  <div className="w-8 text-right font-medium text-text-heading">14%</div>
                </div>
                <div className="flex items-center text-[10px]">
                  <div className="w-24 text-muted">Motivation</div>
                  <div className="flex-1 mx-2 h-1.5 bg-bg rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: '9%' }}></div>
                  </div>
                  <div className="w-8 text-right font-medium text-text-heading">9%</div>
                </div>
                <div className="flex items-center text-[10px]">
                  <div className="w-24 text-muted">Other</div>
                  <div className="flex-1 mx-2 h-1.5 bg-bg rounded-full overflow-hidden">
                    <div className="h-full bg-gray-400 rounded-full" style={{ width: '7%' }}></div>
                  </div>
                  <div className="w-8 text-right font-medium text-text-heading">7%</div>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-2 mb-6">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-muted">Last Updated</span>
                <span className="font-medium text-text-heading">May 31, 2024 09:42</span>
              </div>
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-muted">First Seen</span>
                <span className="font-medium text-text-heading">Dec 12, 2023 14:33 {'>'}</span>
              </div>
            </div>

            <button className="w-full flex items-center justify-center gap-2 bg-primary/5 hover:bg-primary/10 text-primary py-2.5 rounded-lg text-xs font-semibold transition-colors mt-auto">
              <Network size={14} /> View in Network
            </button>
          </div>
        )}
      </div>

    </div>
  );
}
