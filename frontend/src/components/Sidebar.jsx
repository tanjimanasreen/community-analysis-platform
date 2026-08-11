import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Activity,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Database,
  GitMerge,
  LayoutDashboard,
  Network,
  TrendingUp,
  X,
} from 'lucide-react';

const navItems = [
  { name: 'Overview', icon: LayoutDashboard, path: '/' },
  { name: 'Communities', icon: Network, path: '/communities' },
  { name: 'Thematic Analysis', icon: Activity, path: '/thematic' },
  { name: 'Community Evolution', icon: TrendingUp, path: '/evolution' },
  { name: 'Comparative Analysis', icon: GitMerge, path: '/comparative' },
  { name: 'Data & Reports', icon: Database, path: '/data-reports' },
  { name: 'Methodology', icon: BookOpen, path: '/methodology' },
];

export default function Sidebar({ isCollapsed, toggleSidebar, onNavigate }) {
  const location = useLocation();

  return (
    <aside
      aria-label="Primary navigation"
      className={`bg-surface border-r border-border/80 flex flex-col transition-all duration-300 shrink-0 h-screen sticky top-0 ${
        isCollapsed
          ? 'hidden lg:flex lg:w-20'
          : 'fixed inset-y-0 left-0 z-[100] w-[85vw] max-w-xs sm:w-72 lg:w-64 lg:static lg:z-auto shadow-2xl lg:shadow-none bg-surface/95 backdrop-blur-xl'
      }`}
    >
      <div className={`p-5 flex items-center justify-between border-b border-border/40 ${isCollapsed ? 'lg:justify-center' : ''}`}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-primary to-secondary flex items-center justify-center shadow-[0_0_15px_rgba(122,162,247,0.4)] shrink-0">
            <Network size={20} className="text-white" aria-hidden="true" />
          </div>
          {!isCollapsed && (
            <div className="whitespace-nowrap overflow-hidden">
              <h1 className="text-text-heading font-bold text-base leading-tight">Digital Community</h1>
              <h2 className="text-primary font-semibold text-xs">Dynamics</h2>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label="Close navigation"
          className="lg:hidden p-1.5 text-muted hover:text-text-heading rounded-lg hover:bg-surface-soft transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      <div className="px-3 pb-4 mt-3 flex-1 overflow-y-auto">
        {!isCollapsed && <p className="text-[11px] text-muted/80 mb-3 px-3 uppercase tracking-wider font-bold">Dashboards</p>}
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const destination = `${item.path}${location.search}`;
            return (
              <NavLink
                key={item.name}
                to={destination}
                onClick={onNavigate}
                aria-label={isCollapsed ? item.name : undefined}
                title={isCollapsed ? item.name : undefined}
                className={({ isActive }) => `flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'} px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
                  isActive
                    ? 'bg-primary/15 text-primary shadow-[inset_3px_0_0_var(--color-primary)]'
                    : 'text-text/90 hover:bg-surface-soft hover:text-text-heading'
                }`}
              >
                {({ isActive }) => (
                  <>
                    <Icon size={18} className={isActive ? 'text-primary' : 'text-muted/80'} aria-hidden="true" />
                    {!isCollapsed && <span className="whitespace-nowrap overflow-hidden">{item.name}</span>}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="mt-auto p-4 border-t border-border/50">
        <div className={`rounded-xl border border-border/60 bg-surface-soft/80 p-3 ${isCollapsed ? 'text-center' : ''}`}>
          <Database size={18} className="text-primary mx-auto" aria-hidden="true" />
          {!isCollapsed && (
            <div className="mt-2 text-center">
              <p className="text-xs font-semibold text-text-heading">Read-only analytics</p>
              <p className="text-[11px] text-muted">Canonical run artifacts</p>
            </div>
          )}
        </div>
      </div>

      <button
        type="button"
        onClick={toggleSidebar}
        aria-label={isCollapsed ? 'Expand navigation' : 'Collapse navigation'}
        className="hidden lg:flex absolute -right-3 top-7 bg-surface border border-border rounded-full p-1 text-muted hover:text-text-heading hover:bg-surface-soft transition-colors shadow-md z-50"
      >
        {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </aside>
  );
}
