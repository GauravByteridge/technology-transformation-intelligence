import { NavLink } from 'react-router-dom';

interface NavigationBarProps {
  projectExists: boolean;
}

const navLinks = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/data', label: 'Data Management' },
  { to: '/chat', label: 'AI Chat' },
  { to: '/visualize', label: 'AI Visualization' },
];

export default function NavigationBar({ projectExists }: NavigationBarProps) {
  if (!projectExists) {
    return null;
  }

  return (
    <nav style={styles.nav}>
      <span style={styles.brand}>Project Intelligence Hub</span>
      <ul style={styles.linkList}>
        {navLinks.map((link) => (
          <li key={link.to} style={styles.linkItem}>
            <NavLink
              to={link.to}
              style={({ isActive }) => ({
                ...styles.link,
                ...(isActive ? styles.activeLink : {}),
              })}
            >
              {link.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

const styles: Record<string, React.CSSProperties> = {
  nav: {
    display: 'flex',
    alignItems: 'center',
    gap: '2rem',
    padding: '0.75rem 1.5rem',
    backgroundColor: '#1e293b',
    color: '#f8fafc',
  },
  brand: {
    fontWeight: 700,
    fontSize: '1.1rem',
    whiteSpace: 'nowrap',
  },
  linkList: {
    display: 'flex',
    listStyle: 'none',
    margin: 0,
    padding: 0,
    gap: '0.25rem',
  },
  linkItem: {
    margin: 0,
  },
  link: {
    color: '#cbd5e1',
    textDecoration: 'none',
    padding: '0.5rem 0.75rem',
    borderRadius: '0.375rem',
    fontSize: '0.9rem',
    transition: 'background-color 0.15s, color 0.15s',
  },
  activeLink: {
    color: '#ffffff',
    backgroundColor: '#334155',
  },
};
