import {
  Briefcase,
  AlertTriangle,
  TrendingDown,
  Search,
  Wrench,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { KPICard } from './KPICard';
import type { KPIFormat } from './KPICard';
import type { ReactNode } from 'react';

interface KPIDefinition {
  label: string;
  key: string;
  format: KPIFormat;
  icon: ReactNode;
  color: string;
}

const kpiDefinitions: KPIDefinition[] = [
  {
    label: 'Total Projects',
    key: 'totalProjects',
    format: 'number',
    icon: <Briefcase className="h-5 w-5" />,
    color: 'bg-blue-100 text-blue-600',
  },
  {
    label: 'Projects At Risk',
    key: 'projectsAtRisk',
    format: 'number',
    icon: <AlertTriangle className="h-5 w-5" />,
    color: 'bg-amber-100 text-amber-600',
  },
  {
    label: 'Budget Variance',
    key: 'budgetVariance',
    format: 'currency',
    icon: <TrendingDown className="h-5 w-5" />,
    color: 'bg-red-100 text-red-600',
  },
  {
    label: 'Open Audit Findings',
    key: 'openAuditFindings',
    format: 'number',
    icon: <Search className="h-5 w-5" />,
    color: 'bg-purple-100 text-purple-600',
  },
  {
    label: 'Open Remediation Items',
    key: 'openRemediationItems',
    format: 'number',
    icon: <Wrench className="h-5 w-5" />,
    color: 'bg-orange-100 text-orange-600',
  },
  {
    label: 'IT Control Compliance',
    key: 'itControlCompliance',
    format: 'percent',
    icon: <ShieldCheck className="h-5 w-5" />,
    color: 'bg-teal-100 text-teal-600',
  },
  {
    label: 'Resource Utilization',
    key: 'resourceUtilization',
    format: 'percent',
    icon: <Users className="h-5 w-5" />,
    color: 'bg-indigo-100 text-indigo-600',
  },
];

export interface KPIGridProps {
  /** KPI values keyed by metric name */
  data: Record<string, number | null | undefined> | null;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

/**
 * KPIGrid — renders KPI cards in a responsive grid.
 * Accepts derived KPI data as props.
 */
export function KPIGrid({ data, isLoading, isError, onRetry }: KPIGridProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {kpiDefinitions.map((kpi) => (
        <KPICard
          key={kpi.key}
          label={kpi.label}
          value={data ? data[kpi.key] ?? undefined : undefined}
          format={kpi.format}
          icon={kpi.icon}
          color={kpi.color}
          isLoading={isLoading}
          isError={isError}
          onRetry={onRetry}
        />
      ))}
    </div>
  );
}
