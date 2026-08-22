import type { ProjectDetail } from '../../types';
import { EmptyState } from '../common/EmptyState';

interface OverviewSectionProps {
  project: ProjectDetail;
}

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
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] ?? 'bg-gray-100 text-gray-800'}`}>
      {labels[status] ?? status}
    </span>
  );
}

function MetricCard({ label, value, subtext }: { label: string; value: string; subtext?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-gray-900">{value}</p>
      {subtext && <p className="mt-0.5 text-xs text-gray-500">{subtext}</p>}
    </div>
  );
}

export function OverviewSection({ project }: OverviewSectionProps) {
  if (!project) {
    return <EmptyState dataType="project overview" />;
  }

  const variancePrefix = project.budget_variance >= 0 ? '+' : '';

  return (
    <div className="space-y-6">
      {/* Health & Schedule Row */}
      <div className="flex items-center gap-4">
        <div>
          <span className="text-sm text-gray-500">Health Status:</span>{' '}
          <StatusBadge status={project.status} />
        </div>
        <div>
          <span className="text-sm text-gray-500">Schedule:</span>{' '}
          <span className="text-sm font-medium text-gray-900">{project.schedule_status}</span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Total Budget"
          value={`$${project.total_budget.toLocaleString()}`}
        />
        <MetricCard
          label="Actual Spend"
          value={`$${project.actual_cost.toLocaleString()}`}
        />
        <MetricCard
          label="Budget Variance"
          value={`${variancePrefix}$${Math.abs(project.budget_variance).toLocaleString()}`}
          subtext={project.budget_variance >= 0 ? 'Under budget' : 'Over budget'}
        />
        <MetricCard
          label="Progress"
          value={`${project.progress}%`}
        />
        <MetricCard
          label="Resource Utilization"
          value={`${project.resource_utilization}%`}
        />
        <MetricCard
          label="Open Issues"
          value={String(project.open_issues)}
        />
      </div>
    </div>
  );
}
