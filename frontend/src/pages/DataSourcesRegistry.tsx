import { useDataSources } from '../hooks';
import { LoadingState } from '../components/common/LoadingState';
import { StatusBadge } from '../components/common/StatusBadge';
import type { DataSourceStatus } from '../types';

/**
 * Format a timestamp as relative (e.g. "2 hours ago") if within 24 hours,
 * or absolute (e.g. "Jan 15, 2025 9:30 AM") if 24 hours or older.
 */
export function formatLastUpdated(isoTimestamp: string): string {
  const updated = new Date(isoTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - updated.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  if (diffHours < 24) {
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    if (diffMinutes < 1) {
      return 'just now';
    }
    if (diffMinutes < 60) {
      return diffMinutes === 1 ? '1 minute ago' : `${diffMinutes} minutes ago`;
    }
    const hours = Math.floor(diffHours);
    return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
  }

  return updated.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export default function DataSourcesRegistry() {
  const { data: sources, isLoading, isError } = useDataSources();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Data Sources</h1>
      <p className="text-gray-500">
        Connected enterprise data sources and their current health status.
      </p>

      {isLoading && <LoadingState message="Loading data sources..." size="lg" />}

      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load data sources. Please try again later.
        </div>
      )}

      {sources && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Source Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Type
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Records Count
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Last Updated
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {sources.map((source: DataSourceStatus) => (
                <tr key={source.name} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                    {source.name}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600 capitalize">
                    {source.type}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-600">
                    {source.records_count.toLocaleString()}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                    {formatLastUpdated(source.last_updated)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm">
                    <StatusBadge status={source.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
