import { useEffect, useState, useCallback } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { getProject } from './api/client';
import Layout from './components/Layout';
import CreateProjectScreen from './screens/CreateProjectScreen';
import DashboardScreen from './screens/DashboardScreen';
import DataManagementScreen from './screens/DataManagementScreen';
import AIChatScreen from './screens/AIChatScreen';
import AIVisualizationScreen from './screens/AIVisualizationScreen';

export default function App() {
  const [projectExists, setProjectExists] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    getProject()
      .then((project) => {
        if (!cancelled) setProjectExists(project !== null);
      })
      .catch(() => {
        if (!cancelled) setProjectExists(false);
      });
    return () => { cancelled = true; };
  }, []);

  // Called by CreateProjectScreen after successful creation
  const onProjectCreated = useCallback(() => {
    setProjectExists(true);
  }, []);

  // Called by DashboardScreen after reset
  const onProjectReset = useCallback(() => {
    setProjectExists(false);
  }, []);

  // Show loading spinner while checking project status
  if (projectExists === null) {
    return (
      <div style={styles.loadingContainer}>
        <div style={styles.loadingSpinner} />
        <span style={styles.loadingText}>Loading...</span>
      </div>
    );
  }

  return (
    <Layout projectExists={projectExists}>
      <Routes>
        <Route
          path="/"
          element={
            projectExists ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <CreateProjectScreen onProjectCreated={onProjectCreated} />
            )
          }
        />
        <Route
          path="/dashboard"
          element={
            projectExists ? (
              <DashboardScreen onProjectReset={onProjectReset} />
            ) : (
              <Navigate to="/" replace />
            )
          }
        />
        <Route
          path="/data"
          element={
            projectExists ? <DataManagementScreen /> : <Navigate to="/" replace />
          }
        />
        <Route
          path="/chat"
          element={
            projectExists ? <AIChatScreen /> : <Navigate to="/" replace />
          }
        />
        <Route
          path="/visualize"
          element={
            projectExists ? <AIVisualizationScreen /> : <Navigate to="/" replace />
          }
        />
      </Routes>
    </Layout>
  );
}

const styles: Record<string, React.CSSProperties> = {
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    backgroundColor: '#0f172a',
    gap: '1rem',
  },
  loadingSpinner: {
    width: '40px',
    height: '40px',
    border: '3px solid #1e293b',
    borderTop: '3px solid #3b82f6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  loadingText: {
    color: '#94a3b8',
    fontSize: '0.9rem',
  },
};
