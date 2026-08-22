import { useProjectResources } from '../../hooks';
import { LoadingState } from '../common/LoadingState';
import { EmptyState } from '../common/EmptyState';

interface ResourcesSectionProps {
  projectId: string;
}

export function ResourcesSection({ projectId }: ResourcesSectionProps) {
  const { data: resources, isLoading } = useProjectResources(projectId);

  if (isLoading) {
    return <LoadingState message="Loading resources..." />;
  }

  if (!resources || resources.length === 0) {
    return <EmptyState dataType="resource data" message="No resource allocation data available for this project." />;
  }

  // Generate next 3 months forecast stub per team member
  const now = new Date();
  const forecastMonths = Array.from({ length: 3 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() + i + 1, 1);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
  });

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-700">
          Resource Allocation ({resources.length} members)
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Team Member</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Allocation %</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Utilization %</th>
              {forecastMonths.map((month) => (
                <th key={month} className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                  {month}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {resources.map((resource) => {
              // Forecast uses utilization as baseline with slight variance
              const forecasts = forecastMonths.map((_, i) => {
                const base = resource.utilization_percent;
                const variance = (i - 1) * 2; // simple projection
                return Math.min(100, Math.max(0, base + variance));
              });

              return (
                <tr key={resource.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm font-medium text-gray-900">{resource.team_member}</td>
                  <td className="px-4 py-2 text-sm text-gray-700">{resource.role}</td>
                  <td className="px-4 py-2 text-sm text-right text-gray-700">{resource.allocation_percent}%</td>
                  <td className="px-4 py-2 text-sm text-right text-gray-700">
                    <span className={resource.utilization_percent > 90 ? 'text-red-600 font-medium' : ''}>
                      {resource.utilization_percent}%
                    </span>
                  </td>
                  {forecasts.map((val, i) => (
                    <td key={i} className="px-4 py-2 text-sm text-right text-gray-600">
                      {val}%
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
