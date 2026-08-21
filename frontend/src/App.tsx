import { useEffect, useState, useCallback } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { getProject } from './api/client';
import NavigationBar from './components/NavigationBar';
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

  // Show nothing while checking project status
  if (projectExists === null) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>Loading...</div>;
  }

  return (
    <div>
      <NavigationBar projectExists={projectExists} />
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
    </div>
  );
}
