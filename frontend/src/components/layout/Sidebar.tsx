import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderKanban,
  Bot,
  Database,
  BookOpen,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  History,
  FileText,
  BarChart3,
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

const navItems = [
  { to: '/', label: 'PMO Overview', icon: LayoutDashboard },
  { to: '/portfolio', label: 'Projects', icon: FolderKanban },
  { to: '/ai', label: 'AI Query', icon: Bot },
  { to: '/dashboard', label: 'Analytics', icon: BarChart3 },
  { to: '/sources', label: 'Data Sources', icon: Database },
  { to: '/catalog', label: 'Data Catalog', icon: BookOpen },
  { to: '/history', label: 'Query History', icon: History },
  { to: '/briefs', label: 'Executive Briefs', icon: FileText },
];

const bottomNavItems = [
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

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
          transition-all duration-300 ease-in-out
          ${isDark ? 'bg-[#0f1729] text-gray-300' : 'bg-white text-gray-600 border-r border-gray-200'}
          ${collapsed ? 'w-14' : 'w-[220px]'}
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0 md:static md:z-auto
        `}
      >
        {/* Header with collapse toggle */}
        <div className={`flex items-center h-14 border-b ${collapsed ? 'justify-center px-2' : 'justify-between px-4'} ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          {!collapsed && (
            <span className={`text-sm font-semibold whitespace-nowrap overflow-hidden ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Navigation
            </span>
          )}
          {/* Desktop collapse toggle */}
          <button
            onClick={onToggle}
            className={`hidden md:flex items-center justify-center w-7 h-7 rounded transition-colors ${isDark ? 'hover:bg-gray-700/50 text-gray-400 hover:text-white' : 'hover:bg-gray-100 text-gray-400 hover:text-gray-900'}`}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
          {/* Mobile close button */}
          <button
            onClick={onMobileClose}
            className={`md:hidden flex items-center justify-center w-7 h-7 rounded transition-colors ${isDark ? 'hover:bg-gray-700/50 text-gray-400 hover:text-white' : 'hover:bg-gray-100 text-gray-400 hover:text-gray-900'}`}
            aria-label="Close sidebar"
          >
            <X size={16} />
          </button>
        </div>

        {/* Main navigation */}
        <nav className="flex-1 flex flex-col py-3 overflow-y-auto">
          <ul className="space-y-1 px-2 flex-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={to === '/'}
                  onClick={onMobileClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium transition-colors
                    ${isActive
                      ? isDark
                        ? 'bg-teal-600/20 text-teal-300'
                        : 'bg-teal-600/15 text-teal-700 font-semibold'
                      : isDark
                        ? 'text-gray-400 hover:bg-gray-700/40 hover:text-white'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
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

          {/* Bottom section: Settings */}
          <div className={`border-t pt-2 px-2 ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
            <ul className="space-y-1">
              {bottomNavItems.map(({ to, label, icon: Icon }) => (
                <li key={to}>
                  <NavLink
                    to={to}
                    onClick={onMobileClose}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium transition-colors
                      ${isActive
                        ? isDark
                          ? 'bg-teal-600/20 text-teal-300'
                          : 'bg-teal-600/15 text-teal-700 font-semibold'
                        : isDark
                          ? 'text-gray-400 hover:bg-gray-700/40 hover:text-white'
                          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
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
          </div>
        </nav>
      </aside>
    </>
  );
}

export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center justify-center w-9 h-9 rounded-md text-gray-300 hover:text-white hover:bg-gray-700/50 transition-colors"
      aria-label="Open menu"
    >
      <Menu size={20} />
    </button>
  );
}
