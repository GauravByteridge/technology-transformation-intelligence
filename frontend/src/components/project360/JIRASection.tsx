import { useProjectJira } from '@/hooks';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';
import type { SprintResponse, JiraIssueResponse } from '@/types';

interface JIRASectionProps {
  projectId: string;
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-amber-100 text-amber-800',
    low: 'bg-green-100 text-green-800',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[priority.toLowerCase()] ?? 'bg-gray-100 text-gray-800'}`}
    >
      {priority.charAt(0).toUpperCase() + priority.slice(1)}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    open: 'bg-blue-100 text-blue-800',
    in_progress: 'bg-yellow-100 text-yellow-800',
    'in progress': 'bg-yellow-100 text-yellow-800',
    resolved: 'bg-green-100 text-green-800',
    done: 'bg-green-100 text-green-800',
    closed: 'bg-gray-100 text-gray-800',
    active: 'bg-blue-100 text-blue-800',
    planned: 'bg-purple-100 text-purple-800',
    completed: 'bg-green-100 text-green-800',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[status.toLowerCase()] ?? 'bg-gray-100 text-gray-800'}`}
    >
      {status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
    </span>
  );
}

function SprintMetrics({
  openIssues,
  overdueIssues,
  completionPercentage,
}: {
  openIssues: number;
  overdueIssues: number;
  completionPercentage: number;
}) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-xs font-medium text-gray-500 uppercase">Open Issues</p>
        <p className="mt-1 text-2xl font-semibold text-gray-900">{openIssues}</p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-xs font-medium text-gray-500 uppercase">Overdue Issues</p>
        <p className={`mt-1 text-2xl font-semibold ${overdueIssues > 0 ? 'text-red-600' : 'text-gray-900'}`}>
          {overdueIssues}
        </p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-xs font-medium text-gray-500 uppercase">Completion</p>
        <p className="mt-1 text-2xl font-semibold text-gray-900">{(Number(completionPercentage) || 0).toFixed(1)}%</p>
      </div>
    </div>
  );
}

function SprintsList({ sprints }: { sprints: SprintResponse[] }) {
  if (sprints.length === 0) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-700">Sprints ({sprints.length})</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Start Date</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">End Date</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Velocity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {sprints.map((sprint) => (
              <tr key={sprint.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-sm font-medium text-gray-900">{sprint.name}</td>
                <td className="px-4 py-2 text-sm">
                  <StatusBadge status={sprint.status} />
                </td>
                <td className="px-4 py-2 text-sm text-gray-700">
                  {new Date(sprint.start_date).toLocaleDateString()}
                </td>
                <td className="px-4 py-2 text-sm text-gray-700">
                  {new Date(sprint.end_date).toLocaleDateString()}
                </td>
                <td className="px-4 py-2 text-sm text-right text-gray-700">
                  {sprint.velocity != null ? sprint.velocity : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function IssuesTable({ issues }: { issues: JiraIssueResponse[] }) {
  if (issues.length === 0) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-700">Issues ({issues.length})</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Key</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Summary</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Assignee</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Points</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {issues.map((issue) => (
              <tr key={issue.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-sm font-medium text-blue-600">{issue.issue_key}</td>
                <td className="px-4 py-2 text-sm text-gray-700">{issue.issue_type}</td>
                <td className="px-4 py-2 text-sm text-gray-900 max-w-xs truncate" title={issue.summary}>
                  {issue.summary}
                </td>
                <td className="px-4 py-2 text-sm">
                  <StatusBadge status={issue.status} />
                </td>
                <td className="px-4 py-2 text-sm">
                  <PriorityBadge priority={issue.priority} />
                </td>
                <td className="px-4 py-2 text-sm text-gray-700">{issue.assignee ?? '—'}</td>
                <td className="px-4 py-2 text-sm text-right text-gray-700">
                  {issue.story_points != null ? issue.story_points : '—'}
                </td>
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

export function JIRASection({ projectId }: JIRASectionProps) {
  const { data, isLoading, isError, refetch } = useProjectJira(projectId);

  if (isLoading) {
    return <LoadingState variant="skeleton" message="Loading JIRA data..." />;
  }

  if (isError) {
    return (
      <ErrorState
        message="Failed to load JIRA data. Please try again."
        onRetry={() => void refetch()}
      />
    );
  }

  if (!data || (data.sprints.length === 0 && data.issues.length === 0)) {
    return <EmptyState message="No sprints or issues found for this project." />;
  }

  return (
    <div className="space-y-6">
      <SprintMetrics
        openIssues={data.open_issues_count}
        overdueIssues={data.overdue_issues_count}
        completionPercentage={data.completion_percentage}
      />

      <SprintsList sprints={data.sprints} />

      <IssuesTable issues={data.issues} />
    </div>
  );
}
