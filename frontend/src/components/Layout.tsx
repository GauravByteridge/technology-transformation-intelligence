import { ReactNode } from 'react';
import Sidebar from './Sidebar';

interface LayoutProps {
  children: ReactNode;
  projectExists: boolean;
}

export default function Layout({ children, projectExists }: LayoutProps) {
  if (!projectExists) {
    return <>{children}</>;
  }

  return (
    <div style={styles.container}>
      <Sidebar projectExists={projectExists} />
      <main style={styles.main}>
        {children}
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    minHeight: '100vh',
    backgroundColor: '#0f172a',
  },
  main: {
    flex: 1,
    marginLeft: '240px',
    backgroundColor: '#0f172a',
    minHeight: '100vh',
  },
};
