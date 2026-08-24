import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import ExecutiveDashboard from './pages/ExecutiveDashboard';
import ProjectPortfolio from './pages/ProjectPortfolio';
import Project360 from './pages/Project360';
import AIAssistant from './pages/AIAssistant';
import ExecutiveBrief from './pages/ExecutiveBrief';
import ExecutiveBriefs from './pages/ExecutiveBriefs';
import DataSourcesRegistry from './pages/DataSourcesRegistry';
import DataLineage from './pages/DataLineage';
import DatasetBrowser from './pages/DatasetBrowser';
import FileUpload from './pages/FileUpload';
import Catalog from './pages/Catalog';
import QueryHistory from './pages/QueryHistory';
import Settings from './pages/Settings';

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
          <Route path="/datasets" element={<DatasetBrowser />} />
          <Route path="/lineage" element={<DataLineage />} />
          <Route path="/upload" element={<FileUpload />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/history" element={<QueryHistory />} />
          <Route path="/briefs" element={<ExecutiveBriefs />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
