import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderKanban,
  Bot,
  Database,
  GitBranch,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
} from 'lucide-react';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/portfolio', label: 'Portfolio', icon: FolderKanban },
  { to: '/ai', label: 'AI Assistant', icon: Bot },
  { to: '/sources', label: 'Data Sources', icon: Database },
  { to: '/lineage', label: 'Data Lineage', icon: GitBranch },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 h-full z-50 flex flex-col
          bg-[#0f1729] text-gray-300 transition-all duration-300 ease-in-out
          ${collapsed ? 'w-12' : 'w-[200px]'}
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0 md:static md:z-auto
        `}
      >
        {/* Header */}
        <div className={`flex items-center h-14 border-b border-gray-700/50 ${collapsed ? 'justify-center px-2' : 'justify-between px-4'}`}>
          {!collapsed && (
            <span className="text-sm font-semibold text-white whitespace-nowrap overflow-hidden">
              TTI Platform
            </span>
          )}
          {/* Desktop collapse toggle */}
          <button
            onClick={onToggle}
            className="hidden md:flex items-center justify-center w-7 h-7 rounded hover:bg-gray-700/50 text-gray-400 hover:text-white transition-colors"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
          {/* Mobile close button */}
          <button
            onClick={onMobileClose}
            className="md:hidden flex items-center justify-center w-7 h-7 rounded hover:bg-gray-700/50 text-gray-400 hover:text-white transition-colors"
            aria-label="Close sidebar"
          >
            <X size={16} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-3 overflow-y-auto">
          <ul className="space-y-1 px-2">
            {navItems.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={to === '/'}
                  onClick={onMobileClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors
                    ${isActive
                      ? 'bg-teal-600/20 text-teal-300'
                      : 'text-gray-400 hover:bg-gray-700/40 hover:text-white'
                    }
                    ${collapsed ? 'justify-center' : ''}`
                  }
                  title={collapsed ? label : undefined}
                >
                  <Icon size={18} className="shrink-0" />
                  {!collapsed && <span className="whitespace-nowrap overflow-hidden">{label}</span>}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
    </>
  );
}

export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="md:hidden fixed top-3 left-3 z-30 flex items-center justify-center w-9 h-9 rounded-md bg-[#0f1729] text-gray-300 hover:text-white shadow-lg"
      aria-label="Open menu"
    >
      <Menu size={20} />
    </button>
  );
}
