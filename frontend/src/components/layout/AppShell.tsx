import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar, MobileMenuButton } from './Sidebar';

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 text-gray-900">
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((prev) => !prev)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile menu button - visible only on small screens when sidebar is closed */}
        {!mobileOpen && <MobileMenuButton onClick={() => setMobileOpen(true)} />}

        <main className="flex-1 overflow-y-auto p-4 md:p-6 pt-14 md:pt-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
