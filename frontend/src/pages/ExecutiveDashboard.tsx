import {
  Briefcase,
  AlertTriangle,
  TrendingDown,
  Search,
  Wrench,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { usePortfolioSummary } from '@/hooks';
import { LoadingState, ErrorState, EmptyState } from '@/components/common';
import { KPICard } from '@/components/dashboard/KPICard';
import { ChartErrorBoundary } from '@/components/dashboard/ChartErrorBoundary';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { PortfolioSummaryResponse } from '@/types';

// ---------------------------------------------------------------------------
// KPI derivation — compute card values from the single portfolio summary
// ---------------------------------------------------------------------------

interface DerivedKPIs {
  totalProjects: number;
  projectsAtRisk: number;
  budgetVariance: number;
  openAuditFindings: number;
  openRemediationItems: number;
  itControlCompliance: number | null;
  resourceUtilization: number | null;
}

function deriveKPIs(data: PortfolioSummaryResponse): DerivedKPIs {
  const projects = data.projects;

  const budgetVariance = projects.reduce((sum, p) => sum + p.budget_variance, 0);
  const openAuditFindings = projects.reduce((sum, p) => sum + p.open_audit_findings_count, 0);
  const openRemediationItems = projects.reduce((sum, p) => sum + p.open_remediation_items_count, 0);

  const itControlCompliance =
    projects.length > 0
      ? projects.reduce((sum, p) => sum + p.it_control_compliance_percentage, 0) / projects.length
      : null;

  const resourceUtilization =
    projects.length > 0
      ? projects.reduce((sum, p) => sum + p.resource_utilization_percentage, 0) / projects.length
      : null;

  return {
    totalProjects: data.total_projects,
    projectsAtRisk: data.at_risk_count,
    budgetVariance,
    openAuditFindings,
    openRemediationItems,
    itControlCompliance,
    resourceUtilization,
  };
}

// ---------------------------------------------------------------------------
// Chart data derivation
// ---------------------------------------------------------------------------

interface HealthDistribution {
  on_track: number;
  at_risk: number;
  delayed: number;
  completed: number;
}

interface BudgetVsActualItem {
  name: string;
  budget: number;
  actual: number;
}

interface AuditRemediationData {
  openAuditFindings: number;
  openRemediationItems: number;
}

function deriveHealthDistribution(data: PortfolioSummaryResponse): HealthDistribution {
  return {
    on_track: data.on_track_count,
    at_risk: data.at_risk_count,
    delayed: data.delayed_count,
    completed: data.completed_count,
  };
}

function deriveBudgetVsActual(data: PortfolioSummaryResponse): BudgetVsActualItem[] {
  return data.projects.map((p) => ({
    name: p.project_id,
    budget: p.budget_total,
    actual: p.budget_spent,
  }));
}

function deriveAuditRemediation(data: PortfolioSummaryResponse): AuditRemediationData {
  return {
    openAuditFindings: data.projects.reduce((sum, p) => sum + p.open_audit_findings_count, 0),
    openRemediationItems: data.projects.reduce((sum, p) => sum + p.open_remediation_items_count, 0),
  };
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

/**
 * ExecutiveDashboard — derives all KPI cards and chart data from the single
 * usePortfolioSummary() hook. No N+1 API calls.
 * Each section renders its own loading/error/empty states independently.
 */
export default function ExecutiveDashboard() {
  const { data, isLoading, isError, refetch } = usePortfolioSummary();

  const kpis = data ? deriveKPIs(data) : null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Executive Dashboard</h1>

      {/* KPI cards row */}
      <KPISection kpis={kpis} isLoading={isLoading} isError={isError} onRetry={() => refetch()} />

      {/* Charts grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartErrorBoundary>
          <HealthDistributionChart data={data} isLoading={isLoading} isError={isError} onRetry={() => refetch()} />
        </ChartErrorBoundary>

        <ChartErrorBoundary>
          <BudgetVsActualChartCard data={data} isLoading={isLoading} isError={isError} onRetry={() => refetch()} />
        </ChartErrorBoundary>

        <ChartErrorBoundary>
          <AuditRemediationChartCard data={data} isLoading={isLoading} isError={isError} onRetry={() => refetch()} />
        </ChartErrorBoundary>

        <ChartErrorBoundary>
          <ResourceUtilizationChartCard data={data} isLoading={isLoading} isError={isError} onRetry={() => refetch()} />
        </ChartErrorBoundary>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// KPI Section
// ---------------------------------------------------------------------------

interface KPISectionProps {
  kpis: DerivedKPIs | null;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

function KPISection({ kpis, isLoading, isError, onRetry }: KPISectionProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KPICard
        label="Total Projects"
        value={kpis?.totalProjects ?? undefined}
        format="number"
        icon={<Briefcase className="h-5 w-5" />}
        color="bg-blue-100 text-blue-600"
        isLoading={isLoading}
        isError={isError}
        onRetry={onRetry}
      />
      <KPICard
        label="Projects At Risk"
        value={kpis?.projectsAtRisk ?? undefined}
        format="number"
        icon={<AlertTriangle className="h-5 w-5" />}
        color="bg-amber-100 text-amber-600"
        isLoading={isLoading}
        isError={isError}
        onRetry={onRetry}
      />
      <KPICard
        label="Budget Variance"
        value={kpis?.budgetVariance ?? undefined}
        format="currency"
        icon={<TrendingDown className="h-5 w-5" />}
        color="bg-red-100 text-red-600"
        isLoading={isLoading}
        isError={isError}
        onRetry={onRetry}
      />
      <KPICard
        label="Open Audit Findings"
        value={kpis?.openAuditFindings ?? undefined}
        format="number"
        icon={<Search className="h-5 w-5" />}
        color="bg-purple-100 text-purple-600"
        isLoading={isLoading}
        isError={isError}
        onRetry={onRetry}
      />
      <KPICard
        label="Open Remediation Items"
        value={kpis?.openRemediationItems ?? undefined}
        format="number"
        icon={<Wrench className="h-5 w-5" />}
        color="bg-orange-100 text-orange-600"
        isLoading={isLoading}
        isError={isError}
        onRetry={onRetry}
      />
      <KPICard
        label="IT Control Compliance"
        value={kpis?.itControlCompliance ?? undefined}
        format="percent"
        icon={<ShieldCheck className="h-5 w-5" />}
        color="bg-teal-100 text-teal-600"
        isLoading={isLoading}
        isError={isError}
        onRetry={onRetry}
      />
      <KPICard
        label="Resource Utilization"
        value={kpis?.resourceUtilization ?? undefined}
        format="percent"
        icon={<Users className="h-5 w-5" />}
        color="bg-indigo-100 text-indigo-600"
        isLoading={isLoading}
        isError={isError}
        onRetry={onRetry}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chart Card components — placeholder visualizations (Task 6.2 adds full charts)
// ---------------------------------------------------------------------------

interface ChartCardProps {
  data: PortfolioSummaryResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

function HealthDistributionChart({ data, isLoading, isError, onRetry }: ChartCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle>Health Distribution</CardTitle></CardHeader>
        <CardContent><LoadingState variant="skeleton" message="Loading health distribution" /></CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader><CardTitle>Health Distribution</CardTitle></CardHeader>
        <CardContent><ErrorState message="Failed to load health distribution" onRetry={onRetry} /></CardContent>
      </Card>
    );
  }

  if (!data || data.total_projects === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>Health Distribution</CardTitle></CardHeader>
        <CardContent><EmptyState message="No project health data available" /></CardContent>
      </Card>
    );
  }

  const distribution = deriveHealthDistribution(data);

  return (
    <Card>
      <CardHeader><CardTitle>Health Distribution</CardTitle></CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <DistributionItem label="On Track" value={distribution.on_track} color="bg-green-500" />
          <DistributionItem label="At Risk" value={distribution.at_risk} color="bg-amber-500" />
          <DistributionItem label="Delayed" value={distribution.delayed} color="bg-red-500" />
          <DistributionItem label="Completed" value={distribution.completed} color="bg-blue-500" />
        </div>
      </CardContent>
    </Card>
  );
}

function DistributionItem({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className={`h-3 w-3 rounded-full ${color}`} aria-hidden="true" />
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-lg font-semibold text-gray-900">{value}</p>
      </div>
    </div>
  );
}

function BudgetVsActualChartCard({ data, isLoading, isError, onRetry }: ChartCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle>Budget vs Actual</CardTitle></CardHeader>
        <CardContent><LoadingState variant="skeleton" message="Loading budget data" /></CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader><CardTitle>Budget vs Actual</CardTitle></CardHeader>
        <CardContent><ErrorState message="Failed to load budget data" onRetry={onRetry} /></CardContent>
      </Card>
    );
  }

  if (!data || data.projects.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>Budget vs Actual</CardTitle></CardHeader>
        <CardContent><EmptyState message="No budget data available" /></CardContent>
      </Card>
    );
  }

  const budgetData = deriveBudgetVsActual(data);

  return (
    <Card>
      <CardHeader><CardTitle>Budget vs Actual</CardTitle></CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {budgetData.map((item) => (
            <div key={item.name} className="flex items-center justify-between border-b border-gray-100 pb-2 last:border-0">
              <span className="text-sm font-medium text-gray-700 truncate max-w-[120px]" title={item.name}>
                {item.name}
              </span>
              <div className="flex gap-4 text-sm">
                <span className="text-gray-500">
                  Budget: <span className="font-medium text-gray-900">${(item.budget / 1_000_000).toFixed(1)}M</span>
                </span>
                <span className="text-gray-500">
                  Actual: <span className="font-medium text-gray-900">${(item.actual / 1_000_000).toFixed(1)}M</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function AuditRemediationChartCard({ data, isLoading, isError, onRetry }: ChartCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle>Audit & Remediation</CardTitle></CardHeader>
        <CardContent><LoadingState variant="skeleton" message="Loading audit data" /></CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader><CardTitle>Audit & Remediation</CardTitle></CardHeader>
        <CardContent><ErrorState message="Failed to load audit data" onRetry={onRetry} /></CardContent>
      </Card>
    );
  }

  if (!data || data.projects.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>Audit & Remediation</CardTitle></CardHeader>
        <CardContent><EmptyState message="No audit data available" /></CardContent>
      </Card>
    );
  }

  const auditData = deriveAuditRemediation(data);

  return (
    <Card>
      <CardHeader><CardTitle>Audit & Remediation</CardTitle></CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-6">
          <div className="text-center">
            <p className="text-3xl font-bold text-purple-600">{auditData.openAuditFindings}</p>
            <p className="mt-1 text-sm text-gray-500">Open Audit Findings</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-orange-600">{auditData.openRemediationItems}</p>
            <p className="mt-1 text-sm text-gray-500">Open Remediation Items</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ResourceUtilizationChartCard({ data, isLoading, isError, onRetry }: ChartCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle>Resource Utilization</CardTitle></CardHeader>
        <CardContent><LoadingState variant="skeleton" message="Loading resource data" /></CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader><CardTitle>Resource Utilization</CardTitle></CardHeader>
        <CardContent><ErrorState message="Failed to load resource data" onRetry={onRetry} /></CardContent>
      </Card>
    );
  }

  if (!data || data.projects.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>Resource Utilization</CardTitle></CardHeader>
        <CardContent><EmptyState message="No resource data available" /></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader><CardTitle>Resource Utilization</CardTitle></CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {data.projects.map((project) => (
            <div key={project.project_id} className="flex items-center gap-3">
              <span className="text-sm text-gray-700 truncate w-28" title={project.project_id}>
                {project.project_id}
              </span>
              <div className="flex-1 h-4 rounded-full bg-gray-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-indigo-500 transition-all"
                  style={{ width: `${Math.min(project.resource_utilization_percentage, 100)}%` }}
                />
              </div>
              <span className="text-sm font-medium text-gray-900 w-12 text-right">
                {project.resource_utilization_percentage.toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
