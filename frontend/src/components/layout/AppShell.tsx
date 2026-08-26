import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar, MobileMenuButton } from './Sidebar';
import { User, Zap, FlaskConical, Sun, Moon } from 'lucide-react';
import { useEnvironmentStore } from '../../stores/environmentStore';
import { useTheme } from '../../context/ThemeContext';

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const mode = useEnvironmentStore((state) => state.mode);
  const { theme, toggleTheme } = useTheme();

  return (
    <div className={`flex h-screen overflow-hidden ${
      theme === 'dark' ? 'bg-[#0a0f1e] text-gray-100' : 'bg-slate-50 text-gray-900'
    }`}>
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((prev) => !prev)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navigation Bar */}
        <header className={`h-14 border-b flex items-center justify-between px-4 md:px-6 shrink-0 ${
          theme === 'dark'
            ? 'border-gray-800 bg-[#0f1729]'
            : 'border-gray-200 bg-white shadow-sm'
        }`}>
          <div className="flex items-center gap-3">
            <div className="md:hidden">
              <MobileMenuButton onClick={() => setMobileOpen(true)} />
            </div>
            <h1 className={`text-sm font-semibold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
              Enterprise Intelligence
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className={`flex items-center justify-center w-8 h-8 rounded-lg transition-colors ${
                theme === 'dark'
                  ? 'hover:bg-gray-700/50 text-gray-400 hover:text-white'
                  : 'hover:bg-gray-100 text-gray-500 hover:text-gray-900'
              }`}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>

            {/* Environment indicator */}
            {mode === 'real' ? (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-green-500/15 text-green-400 text-xs font-medium">
                <Zap size={12} />
                REAL
              </span>
            ) : (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-400 text-xs font-medium">
                <FlaskConical size={12} />
                DEMO
              </span>
            )}

            {/* User menu */}
            <button
              className={`flex items-center gap-2 px-2 py-1 rounded-md transition-colors ${
                theme === 'dark' ? 'hover:bg-gray-800' : 'hover:bg-gray-100'
              }`}
              aria-label="User menu"
            >
              <div className="w-7 h-7 rounded-full bg-teal-600/30 flex items-center justify-center">
                <User size={14} className="text-teal-300" />
              </div>
              <span className={`hidden md:block text-sm ${theme === 'dark' ? 'text-gray-300' : 'text-gray-700'}`}>Admin</span>
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className={`flex-1 overflow-y-auto app-shell-content ${
          theme === 'dark' ? '' : 'bg-slate-50'
        }`}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
