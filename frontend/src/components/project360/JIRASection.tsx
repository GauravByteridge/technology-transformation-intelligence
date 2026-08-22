import { useProjectJIRA } from '../../hooks';
import { LoadingState } from '../common/LoadingState';
import { EmptyState } from '../common/EmptyState';
import type { JIRAIssue } from '../../types';

interface JIRASectionProps {
  projectId: string;
}

function PriorityBadge({ priority }: { priority: JIRAIssue['priority'] }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-amber-100 text-amber-800',
    low: 'bg-green-100 text-green-800',
  };

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[priority] ?? 'bg-gray-100 text-gray-800'}`}>
      {priority.charAt(0).toUpperCase() + priority.slice(1)}
    </span>
  );
}

function StatusBadge({ status }: { status: JIRAIssue['status'] }) {
  const colors: Record<string, string> = {
    open: 'bg-blue-100 text-blue-800',
    in_progress: 'bg-yellow-100 text-yellow-800',
    resolved: 'bg-green-100 text-green-800',
    closed: 'bg-gray-100 text-gray-800',
  };
  const labels: Record<string, string> = {
    open: 'Open',
    in_progress: 'In Progress',
    resolved: 'Resolved',
    closed: 'Closed',
  };

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] ?? 'bg-gray-100 text-gray-800'}`}>
      {labels[status] ?? status}
    </span>
  );
}

export function JIRASection({ projectId }: JIRASectionProps) {
  const { data: issues, isLoading } = useProjectJIRA(projectId);

  if (isLoading) {
    return <LoadingState message="Loading JIRA issues..." />;
  }

  if (!issues || issues.length === 0) {
    return <EmptyState dataType="JIRA issues" message="No issues found for this project." />;
  }

  // Show up to 50 issues
  const displayedIssues = issues.slice(0, 50);

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-700">
          JIRA Issues ({issues.length > 50 ? '50 of ' + issues.length : issues.length})
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Key</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Assignee</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {displayedIssues.map((issue) => (
              <tr key={issue.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-sm font-medium text-blue-600">{issue.issue_key}</td>
                <td className="px-4 py-2 text-sm"><StatusBadge status={issue.status} /></td>
                <td className="px-4 py-2 text-sm"><PriorityBadge priority={issue.priority} /></td>
                <td className="px-4 py-2 text-sm text-gray-700">{issue.assignee}</td>
                <td className="px-4 py-2 text-sm text-gray-700">
                  {issue.due_date ? new Date(issue.due_date).toLocaleDateString() : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
