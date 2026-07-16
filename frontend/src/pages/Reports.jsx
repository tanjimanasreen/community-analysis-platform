import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { FileText, Calendar, Download, Users, Search, Filter, MoreHorizontal, ArrowDown, Activity, TrendingUp, Shield, X, Star, ChevronLeft, ChevronRight, Share2, FilePlus, Settings, LayoutGrid } from 'lucide-react';

export default function ReportsPage() {
  const { summary } = useOutletContext() || {};

  const reports = [
    { id: 1, name: 'Community Overview Report', desc: 'Overview of key community metrics', type: 'Overview', dateRange: 'May 1 – May 31, 2024', authorInitials: 'AR', author: 'Aisha Rahman', status: 'Completed', updated: 'May 31, 2024\n10:30 AM', icon: <Activity size={16} />, iconColor: 'text-blue-500', iconBg: 'bg-blue-500/10' },
    { id: 2, name: 'Community Growth Analysis', desc: 'Growth trends and membership insights', type: 'Growth', dateRange: 'May 1 – May 31, 2024', authorInitials: 'AR', author: 'Aisha Rahman', status: 'Completed', updated: 'May 30, 2024\n4:15 PM', icon: <TrendingUp size={16} />, iconColor: 'text-purple-500', iconBg: 'bg-purple-500/10' },
    { id: 3, name: 'Thematic Diversity Report', desc: 'Topic diversity and distribution', type: 'Thematic', dateRange: 'May 1 – May 31, 2024', authorInitials: 'AR', author: 'Aisha Rahman', status: 'Completed', updated: 'May 29, 2024\n9:45 AM', icon: <Activity size={16} className="rotate-90" />, iconColor: 'text-green-500', iconBg: 'bg-green-500/10' },
    { id: 4, name: 'WIF Persistence Analysis', desc: 'Persistence and retention metrics', type: 'Persistence', dateRange: 'May 1 – May 31, 2024', authorInitials: 'AR', author: 'Aisha Rahman', status: 'Completed', updated: 'May 28, 2024\n1:20 PM', icon: <Shield size={16} />, iconColor: 'text-orange-500', iconBg: 'bg-orange-500/10' },
    { id: 5, name: 'Platform Comparison Report', desc: 'Cross-platform comparison insights', type: 'Comparison', dateRange: 'May 1 – May 31, 2024', authorInitials: 'AR', author: 'Aisha Rahman', status: 'In Progress', updated: 'May 27, 2024\n11:10 AM', icon: <X size={16} />, iconColor: 'text-blue-500', iconBg: 'bg-blue-500/10' },
    { id: 6, name: 'Community Network Report', desc: 'Network structure and key communities', type: 'Network', dateRange: 'Apr 1 – Apr 30, 2024', authorInitials: 'AR', author: 'Aisha Rahman', status: 'Completed', updated: 'May 25, 2024\n3:05 PM', icon: <Users size={16} />, iconColor: 'text-purple-500', iconBg: 'bg-purple-500/10' },
    { id: 7, name: 'Top Communities Report', desc: 'Top communities by engagement', type: 'Top Communities', dateRange: 'Apr 1 – Apr 30, 2024', authorInitials: 'AR', author: 'Aisha Rahman', status: 'Completed', updated: 'May 24, 2024\n2:40 PM', icon: <Star size={16} />, iconColor: 'text-orange-500', iconBg: 'bg-orange-500/10' },
    { id: 8, name: 'Executive Summary – May 2024', desc: 'Monthly executive summary', type: 'Summary', dateRange: 'May 1 – May 31, 2024', authorInitials: 'AR', author: 'Aisha Rahman', status: 'Completed', updated: 'May 24, 2024\n10:00 AM', icon: <Calendar size={16} />, iconColor: 'text-green-500', iconBg: 'bg-green-500/10' },
  ];

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-panel border border-border rounded-xl p-5 shadow-sm">
          <div className="flex gap-4 items-center">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-500 shrink-0">
              <FileText size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted mb-0.5">Total Reports</p>
              <h3 className="text-2xl font-bold text-text-heading leading-tight">42</h3>
              <p className="text-xs text-success font-medium mt-1">↑ 16.7% vs Apr 1 - Apr 30</p>
            </div>
          </div>
        </div>
        
        <div className="bg-panel border border-border rounded-xl p-5 shadow-sm">
          <div className="flex gap-4 items-center">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-500 shrink-0">
              <Calendar size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted mb-0.5">Scheduled Reports</p>
              <h3 className="text-2xl font-bold text-text-heading leading-tight">8</h3>
              <p className="text-xs text-success font-medium mt-1">↑ 14.3% vs Apr 1 - Apr 30</p>
            </div>
          </div>
        </div>
        
        <div className="bg-panel border border-border rounded-xl p-5 shadow-sm">
          <div className="flex gap-4 items-center">
            <div className="w-12 h-12 rounded-xl bg-green-500/10 flex items-center justify-center text-green-500 shrink-0">
              <Download size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted mb-0.5">Recent Exports</p>
              <h3 className="text-2xl font-bold text-text-heading leading-tight">21</h3>
              <p className="text-xs text-success font-medium mt-1">↑ 10.5% vs Apr 1 - Apr 30</p>
            </div>
          </div>
        </div>
        
        <div className="bg-panel border border-border rounded-xl p-5 shadow-sm">
          <div className="flex gap-4 items-center">
            <div className="w-12 h-12 rounded-xl bg-orange-500/10 flex items-center justify-center text-orange-500 shrink-0">
              <Users size={24} />
            </div>
            <div>
              <p className="text-sm font-medium text-muted mb-0.5">Shared Reports</p>
              <h3 className="text-2xl font-bold text-text-heading leading-tight">15</h3>
              <p className="text-xs text-success font-medium mt-1">↑ 25.0% vs Apr 1 - Apr 30</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Main Data Table */}
        <div className="xl:col-span-3 bg-panel border border-border rounded-xl flex flex-col shadow-sm">
          {/* Table Header Controls */}
          <div className="p-5 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <h2 className="text-lg font-bold text-text-heading">Report Library</h2>
            <div className="flex items-center gap-3">
              <div className="relative w-64">
                <Search size={16} className="absolute left-3 top-2.5 text-muted" />
                <input 
                  type="text" 
                  placeholder="Search reports..." 
                  className="w-full bg-panel border border-border rounded-lg text-sm text-text-heading font-medium pl-9 pr-3 py-2 outline-none placeholder-muted shadow-sm"
                />
              </div>
              <button className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-panel-soft transition-colors text-text-heading shadow-sm">
                <Filter size={16} className="text-muted" /> Filters
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead>
                <tr className="border-b border-border text-text-heading font-bold bg-panel-soft/50">
                  <th className="py-4 px-5 font-semibold">Report Name</th>
                  <th className="py-4 px-4 font-semibold">Type</th>
                  <th className="py-4 px-4 font-semibold">Date Range</th>
                  <th className="py-4 px-4 font-semibold">Created By</th>
                  <th className="py-4 px-4 font-semibold">Status</th>
                  <th className="py-4 px-4 font-semibold flex items-center gap-1 cursor-pointer">Updated <ArrowDown size={14} className="text-muted" /></th>
                  <th className="py-4 px-5 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="text-text font-medium text-sm">
                {reports.map((report) => (
                  <tr key={report.id} className="border-b border-border/30 hover:bg-panel-soft/50 transition-colors">
                    <td className="py-4 px-5">
                      <div className="flex items-start gap-3">
                        <div className={`mt-0.5 w-8 h-8 rounded-lg ${report.iconBg} ${report.iconColor} flex items-center justify-center shrink-0`}>
                          {report.icon}
                        </div>
                        <div>
                          <p className="font-bold text-text-heading leading-tight">{report.name}</p>
                          <p className="text-xs text-muted font-normal mt-0.5">{report.desc}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <span className="bg-panel-soft text-text-heading text-xs font-semibold px-2.5 py-1 rounded-md border border-border">
                        {report.type}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-text-heading font-normal">
                      {report.dateRange}
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-purple-600 text-white flex items-center justify-center text-[10px] font-bold">
                          {report.authorInitials}
                        </div>
                        <span className="text-text-heading font-normal text-sm">{report.author}</span>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      {report.status === 'Completed' ? (
                        <span className="bg-green-500/10 text-green-600 text-xs font-semibold px-2.5 py-1 rounded-full flex items-center w-fit gap-1.5 border border-green-500/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                          Completed
                        </span>
                      ) : (
                        <span className="bg-blue-500/10 text-blue-600 text-xs font-semibold px-2.5 py-1 rounded-full flex items-center w-fit gap-1.5 border border-blue-500/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                          In Progress
                        </span>
                      )}
                    </td>
                    <td className="py-4 px-4 text-text-heading font-normal text-xs leading-relaxed whitespace-pre-line">
                      {report.updated}
                    </td>
                    <td className="py-4 px-5 text-right">
                      <div className="flex items-center justify-end gap-2 text-muted">
                        <button className="p-1.5 hover:bg-panel-soft rounded-md transition-colors hover:text-text-heading">
                          <Download size={16} />
                        </button>
                        <button className="p-1.5 hover:bg-panel-soft rounded-md transition-colors hover:text-text-heading">
                          <MoreHorizontal size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="p-4 flex items-center justify-between text-xs text-muted font-medium bg-panel/50 rounded-b-xl border-t border-border">
            <span>Showing 1 to 8 of 42 reports</span>
            <div className="flex items-center gap-1">
              <button className="w-7 h-7 flex items-center justify-center hover:bg-panel-soft rounded-md text-muted border border-transparent hover:border-border"><ChevronLeft size={16} /></button>
              <button className="w-7 h-7 flex items-center justify-center bg-primary text-white font-bold rounded-md shadow-sm">1</button>
              <button className="w-7 h-7 flex items-center justify-center hover:bg-panel-soft rounded-md text-text-heading font-medium">2</button>
              <button className="w-7 h-7 flex items-center justify-center hover:bg-panel-soft rounded-md text-text-heading font-medium">3</button>
              <button className="w-7 h-7 flex items-center justify-center hover:bg-panel-soft rounded-md text-text-heading font-medium">4</button>
              <button className="w-7 h-7 flex items-center justify-center hover:bg-panel-soft rounded-md text-text-heading font-medium">5</button>
              <button className="w-7 h-7 flex items-center justify-center hover:bg-panel-soft rounded-md text-text-heading border border-transparent hover:border-border"><ChevronRight size={16} /></button>
            </div>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="xl:col-span-1 flex flex-col gap-6 h-full">
          {/* Scheduled Reports Card */}
          <div className="bg-panel border border-border rounded-xl shadow-sm p-5">
            <div className="flex justify-between items-center mb-5">
              <h3 className="text-base font-bold text-text-heading">Scheduled Reports</h3>
              <button className="text-primary text-sm font-semibold hover:underline">View all</button>
            </div>
            
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className="flex gap-3 items-center">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-500 flex items-center justify-center shrink-0">
                    <Calendar size={16} />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-text-heading leading-tight">Weekly Community Summary</p>
                    <p className="text-xs text-muted mt-0.5">Every Monday at 9:00 AM</p>
                  </div>
                </div>
                {/* Toggle Switch */}
                <div className="w-8 h-4.5 bg-primary rounded-full relative cursor-pointer">
                  <div className="absolute right-0.5 top-0.5 w-3.5 h-3.5 bg-white rounded-full"></div>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex gap-3 items-center">
                  <div className="w-8 h-8 rounded-lg bg-green-500/10 text-green-500 flex items-center justify-center shrink-0">
                    <TrendingUp size={16} />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-text-heading leading-tight">Growth Insights Report</p>
                    <p className="text-xs text-muted mt-0.5">1st of every month at 8:30 AM</p>
                  </div>
                </div>
                <div className="w-8 h-4.5 bg-primary rounded-full relative cursor-pointer flex items-center">
                  <div className="absolute right-0.5 w-3.5 h-3.5 bg-white rounded-full"></div>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex gap-3 items-center">
                  <div className="w-8 h-8 rounded-lg bg-orange-500/10 text-orange-500 flex items-center justify-center shrink-0">
                    <Shield size={16} />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-text-heading leading-tight">WIF Persistence Report</p>
                    <p className="text-xs text-muted mt-0.5">Every Monday at 10:00 AM</p>
                  </div>
                </div>
                <div className="w-8 h-4.5 bg-primary rounded-full relative cursor-pointer flex items-center">
                  <div className="absolute right-0.5 w-3.5 h-3.5 bg-white rounded-full"></div>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex gap-3 items-center">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0">
                    <Users size={16} />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-text-heading leading-tight">Top Communities Report</p>
                    <p className="text-xs text-muted mt-0.5">15th of every month at 9:00 AM</p>
                  </div>
                </div>
                <div className="w-8 h-4.5 bg-primary rounded-full relative cursor-pointer flex items-center">
                  <div className="absolute right-0.5 w-3.5 h-3.5 bg-white rounded-full"></div>
                </div>
              </div>
            </div>

            <button className="w-full mt-6 py-2 border border-border bg-panel text-text-heading rounded-lg text-sm font-semibold hover:bg-panel-soft transition-colors flex items-center justify-center gap-2 shadow-sm">
              <Settings size={16} className="text-muted" /> Manage Schedules
            </button>
          </div>

          {/* Recent Activity Card */}
          <div className="bg-panel border border-border rounded-xl shadow-sm p-5">
            <h3 className="text-base font-bold text-text-heading mb-5">Recent Activity</h3>
            
            <div className="flex flex-col gap-6">
              <div className="flex gap-3 relative">
                <div className="absolute top-8 bottom-[-16px] left-3.5 w-px bg-border"></div>
                <div className="w-7 h-7 rounded-full bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0 border border-blue-500/20 z-10 bg-panel">
                  <Download size={12} />
                </div>
                <div className="pt-0.5">
                  <p className="text-sm font-bold text-text-heading leading-snug">Community Overview Report exported</p>
                  <p className="text-xs text-muted mt-1 font-medium">May 31, 2024 10:30 AM • CSV</p>
                </div>
              </div>

              <div className="flex gap-3 relative">
                <div className="absolute top-8 bottom-[-16px] left-3.5 w-px bg-border"></div>
                <div className="w-7 h-7 rounded-full bg-purple-500/10 text-purple-500 flex items-center justify-center shrink-0 border border-purple-500/20 z-10 bg-panel">
                  <Share2 size={12} />
                </div>
                <div className="pt-0.5">
                  <p className="text-sm font-bold text-text-heading leading-snug">Growth Insights Report shared with 3 users</p>
                  <p className="text-xs text-muted mt-1 font-medium">May 30, 2024 4:15 PM</p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-full bg-green-500/10 text-green-500 flex items-center justify-center shrink-0 border border-green-500/20 z-10 bg-panel">
                  <FilePlus size={12} />
                </div>
                <div className="pt-0.5">
                  <p className="text-sm font-bold text-text-heading leading-snug">Thematic Diversity Report created</p>
                  <p className="text-xs text-muted mt-1 font-medium">May 29, 2024 9:45 AM</p>
                </div>
              </div>
            </div>

            <button className="text-primary text-sm font-semibold hover:underline mt-6 flex items-center gap-1">
              View all activity <ArrowDown size={14} className="-rotate-90" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
