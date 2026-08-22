import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import ExecutiveDashboard from './pages/ExecutiveDashboard';
import ProjectPortfolio from './pages/ProjectPortfolio';
import Project360 from './pages/Project360';
import AIAssistant from './pages/AIAssistant';
import ExecutiveBrief from './pages/ExecutiveBrief';
import DataSourcesRegistry from './pages/DataSourcesRegistry';
import DataLineage from './pages/DataLineage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<ExecutiveDashboard />} />
          <Route path="/portfolio" element={<ProjectPortfolio />} />
          <Route path="/projects/:projectId" element={<Project360 />} />
          <Route path="/projects/:projectId/brief" element={<ExecutiveBrief />} />
          <Route path="/ai" element={<AIAssistant />} />
          <Route path="/sources" element={<DataSourcesRegistry />} />
          <Route path="/lineage" element={<DataLineage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
