import { useProjectRemediation } from '@/hooks';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';
import type { RemediationItemResponse } from '@/types';

interface RemediationSectionProps {
  projectId: string;
}

function formatDate(dateString: string | null): string {
  if (!dateString) return '—';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-green-100 text-green-800',
};

function PriorityBadge({ priority }: { priority: string }) {
  const colorClass = PRIORITY_COLORS[priority.toLowerCase()] ?? 'bg-gray-100 text-gray-800';

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}>
      {priority.charAt(0).toUpperCase() + priority.slice(1)}
    </span>
  );
}

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-red-100 text-red-800',
  in_progress: 'bg-yellow-100 text-yellow-800',
  completed: 'bg-green-100 text-green-800',
  closed: 'bg-green-100 text-green-800',
};

const STATUS_LABELS: Record<string, string> = {
  open: 'Open',
  in_progress: 'In Progress',
  completed: 'Completed',
  closed: 'Closed',
};

function StatusBadge({ status }: { status: string }) {
  const colorClass = STATUS_COLORS[status.toLowerCase()] ?? 'bg-gray-100 text-gray-800';
  const label = STATUS_LABELS[status.toLowerCase()] ?? status;

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  );
}

export function RemediationSection({ projectId }: RemediationSectionProps) {
  const { data, isLoading, isError, refetch } = useProjectRemediation(projectId);

  if (isLoading) {
    return <LoadingState variant="skeleton" message="Loading remediation items..." />;
  }

  if (isError) {
    return (
      <ErrorState
        message="Failed to load remediation items. Please try again."
        onRetry={() => void refetch()}
      />
    );
  }

  if (!data || data.items.length === 0) {
    return <EmptyState message="No remediation items recorded for this project." />;
  }

  const { items, overdue_count } = data;

  return (
    <div className="space-y-4">
      {/* Summary metrics */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
          <p className="text-xs font-medium text-gray-500 uppercase">Total Items</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{items.length}</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
          <p className="text-xs font-medium text-gray-500 uppercase">Overdue</p>
          <p className={`mt-1 text-2xl font-semibold ${overdue_count > 0 ? 'text-red-600' : 'text-gray-900'}`}>
            {overdue_count}
          </p>
        </div>
      </div>

      {/* Items table */}
      <div className="rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-700">
            Remediation Items
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Owner</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Completed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((item: RemediationItemResponse) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm text-gray-900">{item.title}</td>
                  <td className="px-4 py-2 text-sm text-gray-700">{item.owner ?? '—'}</td>
                  <td className="px-4 py-2 text-sm">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <PriorityBadge priority={item.priority} />
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-700">{formatDate(item.due_date)}</td>
                  <td className="px-4 py-2 text-sm text-gray-700">{formatDate(item.completion_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
