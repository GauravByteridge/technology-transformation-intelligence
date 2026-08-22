import {
  Briefcase,
  AlertTriangle,
  DollarSign,
  TrendingDown,
  Search,
  Wrench,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { useDashboardKPIs } from '../../hooks';
import { KPICard } from './KPICard';
import type { KPIFormat } from './KPICard';
import type { DashboardKPIs } from '../../types';
import type { ReactNode } from 'react';

interface KPIDefinition {
  label: string;
  key: keyof DashboardKPIs;
  format: KPIFormat;
  icon: ReactNode;
  color: string;
}

const kpiDefinitions: KPIDefinition[] = [
  {
    label: 'Total Projects',
    key: 'total_projects',
    format: 'number',
    icon: <Briefcase className="h-5 w-5" />,
    color: 'bg-blue-100 text-blue-600',
  },
  {
    label: 'Projects At Risk',
    key: 'projects_at_risk',
    format: 'number',
    icon: <AlertTriangle className="h-5 w-5" />,
    color: 'bg-amber-100 text-amber-600',
  },
  {
    label: 'Total Budget',
    key: 'total_budget',
    format: 'currency',
    icon: <DollarSign className="h-5 w-5" />,
    color: 'bg-green-100 text-green-600',
  },
  {
    label: 'Budget Variance',
    key: 'budget_variance',
    format: 'currency',
    icon: <TrendingDown className="h-5 w-5" />,
    color: 'bg-red-100 text-red-600',
  },
  {
    label: 'Open Audit Findings',
    key: 'open_audit_findings',
    format: 'number',
    icon: <Search className="h-5 w-5" />,
    color: 'bg-purple-100 text-purple-600',
  },
  {
    label: 'Open Remediation Items',
    key: 'open_remediation_items',
    format: 'number',
    icon: <Wrench className="h-5 w-5" />,
    color: 'bg-orange-100 text-orange-600',
  },
  {
    label: 'IT Control Compliance',
    key: 'it_control_compliance',
    format: 'percent',
    icon: <ShieldCheck className="h-5 w-5" />,
    color: 'bg-teal-100 text-teal-600',
  },
  {
    label: 'Resource Utilization',
    key: 'resource_utilization',
    format: 'percent',
    icon: <Users className="h-5 w-5" />,
    color: 'bg-indigo-100 text-indigo-600',
  },
];

/**
 * KPIGrid — renders 8 KPI cards in a responsive grid.
 * Uses the useDashboardKPIs hook for data fetching.
 * Each card independently shows loading, error, or data state.
 */
export function KPIGrid() {
  const { data, isLoading, isError, refetch } = useDashboardKPIs();

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {kpiDefinitions.map((kpi) => (
        <KPICard
          key={kpi.key}
          label={kpi.label}
          value={data ? data[kpi.key] : undefined}
          format={kpi.format}
          icon={kpi.icon}
          color={kpi.color}
          isLoading={isLoading}
          isError={isError}
          onRetry={() => refetch()}
        />
      ))}
    </div>
  );
}
