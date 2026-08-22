import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FileText } from 'lucide-react';
import { useProjectDetail } from '../hooks';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import {
  OverviewSection,
  FinancialsSection,
  JIRASection,
  AuditSection,
  ControlsSection,
  ResourcesSection,
  ProjectAITab,
} from '../components/project360';
import type { ProjectDetail } from '../types';

const TABS = [
  'Overview',
  'Financials',
  'SDLC',
  'JIRA',
  'Resources',
  'Audit',
  'Controls',
  'Remediation',
  'Documents',
  'AI',
] as const;

type TabName = (typeof TABS)[number];

function TabPlaceholder({ tab }: { tab: TabName }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <h2 className="text-lg font-medium text-gray-900">{tab}</h2>
      <p className="mt-2 text-sm text-gray-500">
        {tab} section content will be implemented in a future task.
      </p>
    </div>
  );
}

function TabContent({ tab, project }: { tab: TabName; project: ProjectDetail }) {
  switch (tab) {
    case 'Overview':
      return <OverviewSection project={project} />;
    case 'Financials':
      return <FinancialsSection projectId={project.id} />;
    case 'JIRA':
      return <JIRASection projectId={project.id} />;
    case 'Audit':
      return <AuditSection projectId={project.id} />;
    case 'Controls':
      return <ControlsSection projectId={project.id} />;
    case 'Resources':
      return <ResourcesSection projectId={project.id} />;
    case 'AI':
      return <ProjectAITab projectId={project.id} projectName={project.name} />;
    default:
      return <TabPlaceholder tab={tab} />;
  }
}

export default function Project360() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabName>('Overview');

  const {
    data: project,
    isLoading,
    isError,
    refetch,
  } = useProjectDetail(projectId ?? '');

  if (isLoading) {
    return <LoadingState message="Loading project details..." size="lg" />;
  }

  if (isError || !project) {
    return (
      <ErrorState
        message="Failed to load project details. Please try again."
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{project.name}</h1>
          <p className="mt-1 text-sm text-gray-500">
            Managed by {project.project_manager}
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate(`/projects/${projectId}/brief`)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          aria-label="Generate executive brief for this project"
        >
          <FileText className="w-4 h-4" />
          Generate Brief
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-1 overflow-x-auto" aria-label="Project tabs">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
              aria-selected={activeTab === tab}
              role="tab"
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div role="tabpanel" aria-label={`${activeTab} tab content`}>
        <TabContent tab={activeTab} project={project} />
      </div>
    </div>
  );
}
