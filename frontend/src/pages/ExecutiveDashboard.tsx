import { useNavigate } from 'react-router-dom';
import {
  Briefcase,
  AlertTriangle,
  DollarSign,
  ShieldAlert,
  Database,
  FolderKanban,
  FileText,
  Bot,
  Activity,
} from 'lucide-react';
import { usePortfolioSummary, useDataSources, useProjects } from '@/hooks';
import { LoadingState } from '@/components/common';
import type { PortfolioSummaryResponse } from '@/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(value: number | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 1_000_000) return `$${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `$${(num / 1_000).toFixed(0)}K`;
  return `$${num.toFixed(0)}`;
}

function getHealthColor(status: string): string {
  switch (status) {
    case 'on_track':
      return 'bg-green-500';
    case 'at_risk':
      return 'bg-amber-500';
    case 'delayed':
      return 'bg-red-500';
    case 'completed':
      return 'bg-blue-500';
    default:
      return 'bg-gray-500';
  }
}

function getHealthLabel(status: string): string {
  switch (status) {
    case 'on_track':
      return 'On Track';
    case 'at_risk':
      return 'At Risk';
    case 'delayed':
      return 'Delayed';
    case 'completed':
      return 'Completed';
    default:
      return status;
  }
}

function getHealthTextColor(status: string): string {
  switch (status) {
    case 'on_track':
      return 'text-green-400';
    case 'at_risk':
      return 'text-amber-400';
    case 'delayed':
      return 'text-red-400';
    case 'completed':
      return 'text-blue-400';
    default:
      return 'text-gray-400';
  }
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function ExecutiveDashboard() {
  const navigate = useNavigate();
  const { data, isLoading } = usePortfolioSummary();
  const { data: sources } = useDataSources();
  const { data: projectList } = useProjects();

  if (isLoading) {
    return <LoadingState variant="full-page" message="Loading overview..." />;
  }

  const totalProjects = data?.total_projects ?? 0;
  const atRisk = data?.at_risk_count ?? 0;
  const totalBudget = data?.projects?.reduce((sum, p) => sum + (Number(p.budget_total) || 0), 0) ?? 0;
  const openRisks = data?.projects?.reduce((sum, p) => sum + (Number(p.open_risks_count) || 0), 0) ?? 0;
  const connectedSources = sources?.length ?? 0;

  return (
    <div className="space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-semibold text-white">
          Technology Transformation Intelligence
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          What is happening across your technology transformation portfolio.
        </p>
      </div>

      {/* Connected info bar */}
      <div className="flex items-center gap-6 text-sm text-gray-400">
        <span className="flex items-center gap-2">
          <Database size={14} className="text-teal-400" />
          Connected Sources: <span className="text-white font-medium">{connectedSources}</span>
        </span>
        <span className="flex items-center gap-2">
          <FolderKanban size={14} className="text-teal-400" />
          Projects: <span className="text-white font-medium">{totalProjects}</span>
        </span>
        <span className="flex items-center gap-2">
          <FileText size={14} className="text-teal-400" />
          Documents: <span className="text-white font-medium">342</span>
        </span>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          icon={<Briefcase size={20} />}
          label="Projects"
          value={totalProjects.toString()}
          color="text-blue-400"
          bgColor="bg-blue-500/10"
        />
        <KPICard
          icon={<AlertTriangle size={20} />}
          label="At Risk"
          value={atRisk.toString()}
          color="text-amber-400"
          bgColor="bg-amber-500/10"
        />
        <KPICard
          icon={<DollarSign size={20} />}
          label="Budget"
          value={formatCurrency(totalBudget)}
          color="text-green-400"
          bgColor="bg-green-500/10"
        />
        <KPICard
          icon={<ShieldAlert size={20} />}
          label="Open Risks"
          value={openRisks.toString()}
          color="text-red-400"
          bgColor="bg-red-500/10"
        />
      </div>

      {/* Portfolio Health */}
      <section className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
        <h2 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
          <Activity size={18} className="text-teal-400" />
          Portfolio Health
        </h2>
        {data && data.projects.length > 0 ? (
          <div className="space-y-3">
            {data.projects.map((project) => {
              const projectInfo = projectList?.items.find((p) => p.id === project.project_id);
              const displayName = projectInfo
                ? (projectInfo.project_code ? `${projectInfo.project_code} — ${projectInfo.name}` : projectInfo.name)
                : project.project_id;
              return (
                <ProjectHealthRow
                  key={project.project_id}
                  name={displayName}
                  progress={project.progress_percentage}
                  status={project.overall_status}
                />
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No project data available.</p>
        )}
      </section>

      {/* Recent Activity */}
      <section className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6">
        <h2 className="text-lg font-medium text-white mb-4">Recent Activity</h2>
        <RecentActivity sources={sources} data={data} />
      </section>

      {/* Ask AI CTA */}
      <div className="flex justify-center">
        <button
          onClick={() => navigate('/ai')}
          className="flex items-center gap-3 px-8 py-4 bg-teal-600 hover:bg-teal-500 text-white font-medium rounded-xl transition-colors shadow-lg shadow-teal-600/20"
        >
          <Bot size={22} />
          Ask AI
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function KPICard({
  icon,
  label,
  value,
  color,
  bgColor,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
  bgColor: string;
}) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-5">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${bgColor} ${color}`}>{icon}</div>
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
        </div>
      </div>
    </div>
  );
}

function ProjectHealthRow({
  name,
  progress,
  status,
}: {
  name: string;
  progress: number;
  status: string;
}) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-sm text-gray-300 w-40 truncate" title={name}>
        {name}
      </span>
      <div className="flex-1 h-3 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${getHealthColor(status)}`}
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
      <span className={`text-xs font-medium ${getHealthTextColor(status)} w-20 text-right`}>
        {getHealthLabel(status)}
      </span>
    </div>
  );
}

function RecentActivity({
  sources,
  data,
}: {
  sources: unknown[] | undefined;
  data: PortfolioSummaryResponse | undefined;
}) {
  const activities: { text: string; time: string }[] = [];

  if (sources && sources.length > 0) {
    activities.push({ text: `${sources.length} data source(s) connected`, time: 'Recently' });
  }
  if (data && data.total_projects > 0) {
    activities.push({ text: `${data.total_projects} projects tracked`, time: 'Active' });
  }
  activities.push({ text: 'Documents indexed and AI-queryable', time: 'System' });
  activities.push({ text: 'Enterprise catalog built from connected sources', time: 'System' });

  return (
    <ul className="space-y-2">
      {activities.map((activity, idx) => (
        <li key={idx} className="flex items-center gap-3 text-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-teal-400 shrink-0" />
          <span className="text-gray-300 flex-1">{activity.text}</span>
          <span className="text-xs text-gray-500">{activity.time}</span>
        </li>
      ))}
    </ul>
  );
}
