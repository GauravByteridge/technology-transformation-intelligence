import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useProjectResources } from '@/hooks';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';

interface ResourcesSectionProps {
  projectId: string;
}

/**
 * ResourcesSection — displays resource allocations, utilization metrics,
 * and capacity forecast for a project using live backend data.
 */
export function ResourcesSection({ projectId }: ResourcesSectionProps) {
  const { data, isLoading, isError, refetch } = useProjectResources(projectId);

  if (isLoading) {
    return <LoadingState variant="skeleton" message="Loading resource data..." />;
  }

  if (isError) {
    return (
      <ErrorState
        message="Failed to load resource data. Please try again."
        onRetry={() => refetch()}
      />
    );
  }

  if (!data || data.allocations.length === 0) {
    return <EmptyState message="No resource allocations available for this project." />;
  }

  const { allocations, utilization_percentage, capacity_gap, forecasts } = data;

  return (
    <div className="space-y-6">
      {/* Summary Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs font-medium uppercase text-gray-500">Utilization</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            {utilization_percentage != null ? `${utilization_percentage}%` : '—'}
          </p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs font-medium uppercase text-gray-500">Capacity Gap</p>
          <p
            className={`mt-1 text-2xl font-bold ${
              capacity_gap > 0 ? 'text-red-600' : capacity_gap < 0 ? 'text-green-600' : 'text-gray-900'
            }`}
          >
            {capacity_gap > 0 ? `+${capacity_gap}` : capacity_gap} FTE
          </p>
        </div>
      </div>

      {/* Allocations Table */}
      <div className="rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-700">
            Resource Allocations ({allocations.length})
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                  Role
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">
                  Allocation %
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                  Start Date
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                  End Date
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {allocations.map((alloc) => (
                <tr key={alloc.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm text-gray-900">
                    {alloc.role_on_project ?? '—'}
                  </td>
                  <td className="px-4 py-2 text-sm text-right text-gray-700">
                    {alloc.allocation_percentage}%
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-700">
                    {formatDate(alloc.start_date)}
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-700">
                    {alloc.end_date ? formatDate(alloc.end_date) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Capacity Forecast */}
      {forecasts.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h3 className="mb-4 text-sm font-semibold text-gray-700">Capacity Forecast</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={forecasts}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="year_month"
                tick={{ fontSize: 12 }}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                label={{ value: 'FTE', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                formatter={(value, name) => [
                  Number(value).toFixed(1),
                  name === 'demand_fte'
                    ? 'Demand'
                    : name === 'capacity_fte'
                    ? 'Capacity'
                    : 'Gap',
                ]}
              />
              <Legend
                formatter={(value: string) =>
                  value === 'demand_fte'
                    ? 'Demand'
                    : value === 'capacity_fte'
                    ? 'Capacity'
                    : 'Gap'
                }
              />
              <Bar dataKey="demand_fte" fill="#3b82f6" name="demand_fte" />
              <Bar dataKey="capacity_fte" fill="#10b981" name="capacity_fte" />
              <Bar dataKey="gap_fte" fill="#f59e0b" name="gap_fte" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

/** Format an ISO date string to a short locale date */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}
