import { NavLink } from 'react-router-dom';

interface SidebarProps {
  projectExists: boolean;
}

// SVG Icons as components
const DashboardIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
  </svg>
);

const FolderIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  </svg>
);

const ChatIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

const ChartIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" />
  </svg>
);

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: DashboardIcon },
  { to: '/data', label: 'Data Management', icon: FolderIcon },
  { to: '/chat', label: 'AI Chat', icon: ChatIcon },
  { to: '/visualize', label: 'Visualization', icon: ChartIcon },
];

export default function Sidebar({ projectExists }: SidebarProps) {
  if (!projectExists) {
    return null;
  }

  return (
    <aside style={styles.sidebar}>
      {/* Logo / Brand */}
      <div style={styles.brand}>
        <div style={styles.logoIcon}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4M12 8h.01" />
          </svg>
        </div>
        <span style={styles.brandText}>Intelligence Hub</span>
      </div>

      {/* Navigation */}
      <nav style={styles.nav}>
        <ul style={styles.navList}>
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                style={({ isActive }) => ({
                  ...styles.navLink,
                  ...(isActive ? styles.navLinkActive : {}),
                })}
              >
                <span style={styles.navIcon}><item.icon /></span>
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div style={styles.footer}>
        <div style={styles.footerText}>Project Intelligence Hub</div>
        <div style={styles.footerVersion}>v1.0.0</div>
      </div>
    </aside>
  );
}

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    width: '240px',
    minWidth: '240px',
    height: '100vh',
    backgroundColor: '#0f172a',
    display: 'flex',
    flexDirection: 'column',
    borderRight: '1px solid #1e293b',
    position: 'fixed',
    left: 0,
    top: 0,
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '1.25rem 1rem',
    borderBottom: '1px solid #1e293b',
  },
  logoIcon: {
    fontSize: '1.5rem',
    width: '36px',
    height: '36px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1e40af',
    borderRadius: '8px',
  },
  brandText: {
    color: '#f8fafc',
    fontSize: '1rem',
    fontWeight: 600,
  },
  nav: {
    flex: 1,
    padding: '1rem 0.5rem',
    overflowY: 'auto',
  },
  navList: {
    listStyle: 'none',
    margin: 0,
    padding: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
  },
  navLink: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.625rem 0.75rem',
    borderRadius: '6px',
    color: '#94a3b8',
    textDecoration: 'none',
    fontSize: '0.875rem',
    transition: 'all 0.15s ease',
  },
  navLinkActive: {
    backgroundColor: '#1e3a8a',
    color: '#ffffff',
  },
  navIcon: {
    fontSize: '1rem',
    width: '20px',
    textAlign: 'center',
  },
  footer: {
    padding: '1rem',
    borderTop: '1px solid #1e293b',
  },
  footerText: {
    color: '#64748b',
    fontSize: '0.75rem',
  },
  footerVersion: {
    color: '#475569',
    fontSize: '0.7rem',
    marginTop: '0.25rem',
  },
};
