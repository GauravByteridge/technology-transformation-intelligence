import {
  KPIGrid,
  ProjectHealthChart,
  BudgetVsActualChart,
  BurnDownChart,
  AuditRemediationChart,
  ResourceForecastChart,
} from '../components/dashboard';

/**
 * ExecutiveDashboard — assembles KPI cards and all 5 dashboard charts.
 * Each child component is self-contained with its own React Query data fetching,
 * loading, error, and empty states. Charts are isolated via error boundaries so
 * a single failure does not crash the entire page.
 */
export default function ExecutiveDashboard() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">
        Executive Dashboard
      </h1>

      {/* KPI cards grid */}
      <KPIGrid />

      {/* Charts in a responsive 2-column grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <ProjectHealthChart />
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <BudgetVsActualChart />
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <BurnDownChart />
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <AuditRemediationChart />
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <ResourceForecastChart />
        </div>
      </div>
    </div>
  );
}
