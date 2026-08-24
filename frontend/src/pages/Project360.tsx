import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  DollarSign,
  TrendingUp,
  ShieldAlert,
  Activity,
  Bot,
} from 'lucide-react';
import { useProjectDetail, useProjectHealth } from '../hooks';
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
  'Progress',
  'Risks',
  'Audit',
  'Resources',
  'AI',
] as const;

type TabName = (typeof TABS)[number];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getStatusEmoji(status: string): string {
  switch (status) {
    case 'on_track': return '🟢';
    case 'at_risk': return '🔴';
    case 'delayed': return '🟠';
    case 'completed': return '🔵';
    default: return '⚪';
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'on_track': return 'On Track';
    case 'at_risk': return 'At Risk';
    case 'delayed': return 'Delayed';
    case 'completed': return 'Completed';
    default: return status;
  }
}

function formatCurrency(value: number | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 1_000_000) return `$${(num / 1_000_000).toFixed(2)}M`;
  if (num >= 1_000) return `$${(num / 1_000).toFixed(0)}K`;
  return `$${num.toFixed(0)}`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function KPICard({ icon, label, value, color }: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-1">
        <span className={color}>{icon}</span>
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <p className="text-xl font-bold text-white">{value}</p>
    </div>
  );
}

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
    case 'Progress':
      return (
        <SectionErrorBoundary sectionName="JIRA">
          <JIRASection projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'Risks':
      return (
        <SectionErrorBoundary sectionName="Risks">
          <RisksOverview projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'Audit':
      return (
        <SectionErrorBoundary sectionName="Audit">
          <AuditSection projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'Resources':
      return (
        <SectionErrorBoundary sectionName="Resources">
          <ResourcesSection projectId={projectId} />
        </SectionErrorBoundary>
      );
    case 'AI':
      return (
        <SectionErrorBoundary sectionName="AI">
          <ProjectAITab projectId={projectId} projectName={projectName} />
        </SectionErrorBoundary>
      );
    default:
      return null;
  }
}

/** Inline risk + documents view for the Risks tab */
function RisksOverview({ projectId }: { projectId: string }) {
  return (
    <div className="space-y-6">
      {/* Risk Summary */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
        <h3 className="text-lg font-medium text-white mb-4">Risk Summary</h3>
        <div className="space-y-3">
          <RiskItem severity="high" title="UAT Delay" description="User acceptance testing behind schedule" />
          <RiskItem severity="medium" title="Resource Constraint" description="Key developer availability limited" />
          <RiskItem severity="medium" title="Budget Variance" description="Projected overrun on infrastructure costs" />
        </div>
      </div>

      {/* Recent Documents */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
        <h3 className="text-lg font-medium text-white mb-4">Recent Documents</h3>
        <div className="space-y-2">
          <DocumentItem name="Meeting Notes.pdf" />
          <DocumentItem name="Risk_Report.xlsx" />
          <DocumentItem name="Audit_Report.pdf" />
        </div>
      </div>
    </div>
  );
}

function RiskItem({ severity, title, description }: { severity: string; title: string; description: string }) {
  const colorMap: Record<string, string> = {
    high: '🔴',
    medium: '🟠',
    low: '🟡',
  };
  return (
    <div className="flex items-start gap-3 p-3 bg-gray-900/50 rounded-lg">
      <span className="text-sm mt-0.5">{colorMap[severity] ?? '⚪'}</span>
      <div>
        <p className="text-sm font-medium text-white">{title}</p>
        <p className="text-xs text-gray-400">{description}</p>
      </div>
    </div>
  );
}

function DocumentItem({ name }: { name: string }) {
  return (
    <div className="flex items-center gap-3 p-2 rounded hover:bg-gray-700/30 transition-colors cursor-pointer">
      <span className="text-gray-400">📄</span>
      <span className="text-sm text-gray-300">{name}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function Project360() {
  const { projectId } = useParams<{ projectId: string }>();
  const id = projectId ?? '';
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabName>('Overview');

  const { data: project, isLoading, isError, error, refetch } = useProjectDetail(id);
  const { data: health } = useProjectHealth(id);

  if (isLoading) {
    return <LoadingState variant="full-page" message="Loading project details..." />;
  }

  if (isError || !project) {
    const is404 = (error as { status?: number })?.status === 404;
    return (
      <ErrorState
        variant="full-page"
        message={is404 ? 'Project not found.' : 'Failed to load project details.'}
        onRetry={is404 ? undefined : () => refetch()}
      />
    );
  }

  const status = health?.overall_status ?? project.status;
  const budgetTotal = health?.budget_total ?? 0;
  const budgetSpent = health?.budget_spent ?? 0;
  const progress = health?.progress_percentage ?? 0;
  const openRisks = health?.open_risks_count ?? 0;

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/portfolio')}
          className="p-1.5 rounded hover:bg-gray-700/50 text-gray-400 hover:text-white transition-colors"
          aria-label="Back to projects"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex items-center gap-3">
          {project.project_code && (
            <span className="text-xs font-mono text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded">
              {project.project_code}
            </span>
          )}
          <h1 className="text-2xl font-semibold text-white">{project.name}</h1>
          <span className="text-sm font-medium">
            {getStatusEmoji(status)} {getStatusLabel(status)}
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          icon={<DollarSign size={16} />}
          label="Budget"
          value={formatCurrency(budgetTotal)}
          color="text-blue-400"
        />
        <KPICard
          icon={<TrendingUp size={16} />}
          label="Actual"
          value={formatCurrency(budgetSpent)}
          color="text-green-400"
        />
        <KPICard
          icon={<Activity size={16} />}
          label="Progress"
          value={`${progress}%`}
          color="text-teal-400"
        />
        <KPICard
          icon={<ShieldAlert size={16} />}
          label="Open Risks"
          value={openRisks.toString()}
          color="text-red-400"
        />
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-700/50">
        <nav className="-mb-px flex space-x-1 overflow-x-auto" role="tablist" aria-label="Project tabs">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'border-teal-400 text-teal-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600'
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
        <TabContent tab={activeTab} projectId={id} projectName={project.name} />
      </div>

      {/* Ask AI CTA */}
      {activeTab !== 'AI' && (
        <div className="flex justify-center pt-4">
          <button
            onClick={() => setActiveTab('AI')}
            className="flex items-center gap-2 px-6 py-3 bg-teal-600 hover:bg-teal-500 text-white font-medium rounded-lg transition-colors"
          >
            <Bot size={18} />
            Ask AI about {project.name}
          </button>
        </div>
      )}
    </div>
  );
}
