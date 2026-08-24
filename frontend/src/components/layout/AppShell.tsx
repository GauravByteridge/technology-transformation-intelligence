import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar, MobileMenuButton } from './Sidebar';
import { User, Zap, FlaskConical } from 'lucide-react';
import { useEnvironmentStore } from '../../stores/environmentStore';

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const mode = useEnvironmentStore((state) => state.mode);

  return (
    <div className="flex h-screen overflow-hidden bg-[#0a0f1e] text-gray-100">
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((prev) => !prev)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navigation Bar */}
        <header className="h-14 border-b border-gray-800 bg-[#0f1729] flex items-center justify-between px-4 md:px-6 shrink-0">
          <div className="flex items-center gap-3">
            {/* Mobile hamburger menu button */}
            <div className="md:hidden">
              <MobileMenuButton onClick={() => setMobileOpen(true)} />
            </div>
            <h1 className="text-sm font-semibold text-white">
              Enterprise Intelligence
            </h1>
          </div>

          <div className="flex items-center gap-4">
            {/* Environment indicator — reflects current mode from store */}
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
              className="flex items-center gap-2 px-2 py-1 rounded-md hover:bg-gray-800 transition-colors"
              aria-label="User menu"
            >
              <div className="w-7 h-7 rounded-full bg-teal-600/30 flex items-center justify-center">
                <User size={14} className="text-teal-300" />
              </div>
              <span className="hidden md:block text-sm text-gray-300">Admin</span>
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
