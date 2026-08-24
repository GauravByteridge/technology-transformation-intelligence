import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useProjectDetail } from '../hooks';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { SectionErrorBoundary } from '../components/common/SectionErrorBoundary';
import {
  OverviewSection,
  FinancialsSection,
  JIRASection,
  AuditSection,
  ControlsSection,
  ResourcesSection,
  RemediationSection,
  SdlcSection,
  DocumentsSection,
  ProjectAITab,
} from '../components/project360';

const TABS = [
  'Overview',
  'Financials',
  'JIRA',
  'Resources',
  'Audit',
  'Controls',
  'Remediation',
  'SDLC',
  'Documents',
  'AI',
] as const;

type TabName = (typeof TABS)[number];

/** Status badge for project overall status */
function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    on_track: 'bg-green-100 text-green-800',
    at_risk: 'bg-amber-100 text-amber-800',
    delayed: 'bg-red-100 text-red-800',
    completed: 'bg-blue-100 text-blue-800',
  };
  const labels: Record<string, string> = {
    on_track: 'On Track',
    at_risk: 'At Risk',
    delayed: 'Delayed',
    completed: 'Completed',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] ?? 'bg-gray-100 text-gray-800'}`}
    >
      {labels[status] ?? status}
    </span>
  );
}

/** Placeholder content for tabs not yet implemented */
function TabPlaceholder({ tab: _tab }: { tab: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <p className="text-sm text-gray-500">Tab content coming soon</p>
    </div>
  );
}

/** Renders the active tab's content — lazy: only the active tab is mounted */
function TabContent({ tab, projectId, projectName }: { tab: TabName; projectId: string; projectName: string }) {
  switch (tab) {
    case 'Overview':
      return (
        <SectionErrorBoundary sectionName="Overview">
          <OverviewSection projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'Financials':
      return (
        <SectionErrorBoundary sectionName="Financials">
          <FinancialsSection projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'JIRA':
      return (
        <SectionErrorBoundary sectionName="JIRA">
          <JIRASection projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'Resources':
      return (
        <SectionErrorBoundary sectionName="Resources">
          <ResourcesSection projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'Audit':
      return (
        <SectionErrorBoundary sectionName="Audit">
          <AuditSection projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'Controls':
      return (
        <SectionErrorBoundary sectionName="Controls">
          <ControlsSection projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'Remediation':
      return (
        <SectionErrorBoundary sectionName="Remediation">
          <RemediationSection projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'AI':
      return (
        <SectionErrorBoundary sectionName="AI">
          <ProjectAITab projectId={projectId} projectName={projectName} />
        </SectionErrorBoundary>
      );
    case 'SDLC':
      return (
        <SectionErrorBoundary sectionName="SDLC">
          <SdlcSection projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'Documents':
      return (
        <SectionErrorBoundary sectionName="Documents">
          <DocumentsSection projectId={projectId} />
        </SectionErrorBoundary>
      );
    default:
      return <TabPlaceholder tab={tab} />;
  }
}

export default function Project360() {
  const { projectId } = useParams<{ projectId: string }>();
  const id = projectId ?? '';
  const [activeTab, setActiveTab] = useState<TabName>('Overview');

  const {
    data: project,
    isLoading,
    isError,
    error,
    refetch,
  } = useProjectDetail(id);

  // Full-page loading while project detail loads
  if (isLoading) {
    return <LoadingState variant="full-page" message="Loading project details..." />;
  }

  // 404 error state if project not found
  if (isError || !project) {
    const is404 = (error as { status?: number })?.status === 404;
    return (
      <ErrorState
        variant="full-page"
        message={
          is404
            ? 'Project not found. It may have been removed or you may not have access.'
            : 'Failed to load project details. Please try again.'
        }
        onRetry={is404 ? undefined : () => refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Project Header */}
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold text-gray-900">{project.name}</h1>
          <StatusBadge status={project.status} />
        </div>
        {project.description && (
          <p className="mt-1 text-sm text-gray-500">{project.description}</p>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav
          className="-mb-px flex space-x-1 overflow-x-auto"
          aria-label="Project tabs"
          role="tablist"
        >
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

      {/* Tab Content — only active tab renders */}
      <div role="tabpanel" aria-label={`${activeTab} tab content`}>
        <TabContent tab={activeTab} projectId={id} projectName={project.name} />
      </div>
    </div>
  );
}
