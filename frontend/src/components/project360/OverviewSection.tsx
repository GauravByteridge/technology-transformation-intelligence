import { useProjectHealth } from '../../hooks';
import { LoadingState } from '../common/LoadingState';
import { ErrorState } from '../common/ErrorState';

interface OverviewSectionProps {
  projectId: string;
}

/** Status badge for overall/schedule status display */
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

/** Individual KPI metric card */
function KpiCard({ label, value, subtext }: { label: string; value: string; subtext?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-gray-900">{value}</p>
      {subtext && <p className="mt-0.5 text-xs text-gray-500">{subtext}</p>}
    </div>
  );
}

/**
 * Overview tab content for Project 360.
 * Fetches health KPIs via useProjectHealth and renders a grid of metric cards.
 */
export function OverviewSection({ projectId }: OverviewSectionProps) {
  const { data: health, isLoading, isError, refetch } = useProjectHealth(projectId);

  if (isLoading) {
    return <LoadingState variant="skeleton" message="Loading health metrics..." />;
  }

  if (isError || !health) {
    return (
      <ErrorState
        message="Failed to load project health metrics."
        onRetry={() => refetch()}
      />
    );
  }

  const variancePrefix = health.budget_variance >= 0 ? '+' : '';
  const varianceSubtext = health.budget_variance >= 0 ? 'Under budget' : 'Over budget';

  return (
    <div className="space-y-6">
      {/* Status Row */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Overall Status:</span>
          <StatusBadge status={health.overall_status} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Schedule:</span>
          <StatusBadge status={health.schedule_status} />
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Budget Total"
          value={`$${health.budget_total.toLocaleString()}`}
        />
        <KpiCard
          label="Budget Spent"
          value={`$${health.budget_spent.toLocaleString()}`}
        />
        <KpiCard
          label="Budget Variance"
          value={`${variancePrefix}$${Math.abs(health.budget_variance).toLocaleString()}`}
          subtext={varianceSubtext}
        />
        <KpiCard
          label="Variance %"
          value={`${(Number(health.budget_variance_percentage) || 0).toFixed(1)}%`}
        />
        <KpiCard
          label="Progress"
          value={`${health.progress_percentage}%`}
        />
        <KpiCard
          label="Resource Utilization"
          value={`${health.resource_utilization_percentage}%`}
        />
        <KpiCard
          label="Open Issues"
          value={String(health.open_issues_count)}
        />
        <KpiCard
          label="Open Risks"
          value={String(health.open_risks_count)}
        />
        <KpiCard
          label="Open Audit Findings"
          value={String(health.open_audit_findings_count)}
        />
        <KpiCard
          label="Open Remediation Items"
          value={String(health.open_remediation_items_count)}
        />
        <KpiCard
          label="IT Control Compliance"
          value={`${health.it_control_compliance_percentage}%`}
        />
      </div>
    </div>
  );
}
