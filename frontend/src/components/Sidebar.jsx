import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Network,
  FileSearch,
  TrendingUp,
  GitMerge,
  Users,
  BarChart2,
  Settings,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  FileText,
  Activity,
  ArrowRightLeft,
  Star,
  Database
} from 'lucide-react';

const navItems = [
  { name: 'Overview', icon: LayoutDashboard, path: '/' },
  { name: 'Community Network', icon: Network, path: '/network' },
  { name: 'Thematic Analysis', icon: Activity, path: '/thematic' },
  { name: 'Evolution Over Time', icon: TrendingUp, path: '/evolution' },
  { name: 'Comparative Analysis', icon: GitMerge, path: '/comparative' },
  { name: 'Community Transitions', icon: ArrowRightLeft, path: '/transitions' },
  { name: 'Top Communities', icon: Users, path: '/top-communities' },
  { name: 'Data Explorer', icon: Database, path: '/data' },
  { name: 'Reports', icon: FileText, path: '/reports' },
];

export default function Sidebar({ isCollapsed, toggleSidebar }) {
  return (
    <aside className={`bg-panel border-r border-border h-screen flex flex-col fixed top-0 lg:static z-50 lg:shrink-0 transition-all duration-300 ${isCollapsed ? '-left-80 w-64 lg:left-0 lg:w-20' : 'left-0 w-64'}`}>
      <div className={`p-6 flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'}`}>
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary to-secondary flex items-center justify-center shadow-[0_0_15px_rgba(122,162,247,0.5)] shrink-0">
          <Network size={20} className="text-white" />
        </div>
        {!isCollapsed && (
          <div className="whitespace-nowrap overflow-hidden">
            <h1 className="text-text-heading font-bold text-lg leading-tight">Digital Community</h1>
            <h2 className="text-primary font-semibold text-sm">Dynamics</h2>
          </div>
        )}
      </div>

      <div className="px-4 pb-4 mt-2 flex-1">
        {!isCollapsed && <p className="text-xs text-muted mb-4 px-2 uppercase tracking-wider font-semibold">Dashboards</p>}
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.path}
                className={({ isActive }) => `flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'} px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-primary/10 text-primary shadow-[inset_2px_0_0_var(--color-primary)]'
                    : 'text-text hover:bg-panel-soft hover:text-text-heading'
                }`}
                title={isCollapsed ? item.name : undefined}
              >
                {({ isActive }) => (
                  <>
                    <Icon size={20} className={isActive ? 'text-primary' : 'text-muted'} />
                    {!isCollapsed && <span className="whitespace-nowrap overflow-hidden">{item.name}</span>}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="mt-auto p-4 border-t border-border/50">
        <nav className="flex flex-col gap-1 mb-4">
          <button className={`flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'} px-3 py-2 rounded-lg text-sm font-medium text-text hover:bg-panel-soft transition-colors`} title={isCollapsed ? "Methodology" : undefined}>
            <BookOpen size={20} className="text-muted" />
            {!isCollapsed && "Methodology"}
          </button>
          <button className={`flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'} px-3 py-2 rounded-lg text-sm font-medium text-text hover:bg-panel-soft transition-colors`} title={isCollapsed ? "Settings" : undefined}>
            <Settings size={20} className="text-muted" />
            {!isCollapsed && "Settings"}
          </button>
        </nav>

        <div className={`flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'} bg-panel-soft p-2 rounded-xl border border-border/50 relative group`}>
          <div className="w-8 h-8 rounded-full bg-gradient-to-r from-accent to-primary flex items-center justify-center text-white font-bold text-xs shadow-lg shrink-0">
            AR
          </div>
          {!isCollapsed && (
            <div className="whitespace-nowrap overflow-hidden">
              <p className="text-sm font-semibold text-text-heading">Aisha Rahman</p>
              <p className="text-xs text-muted">Researcher</p>
            </div>
          )}
        </div>
      </div>

      {/* Collapse Toggle Button */}
      <button
        onClick={toggleSidebar}
        className="absolute -right-3 top-8 bg-panel border border-border rounded-full p-1 text-muted hover:text-text-heading hover:bg-panel-soft transition-colors shadow-md z-50"
      >
        {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </aside>
  );
}
