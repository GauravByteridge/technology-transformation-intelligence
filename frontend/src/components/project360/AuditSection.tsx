import { useProjectAudit } from '../../hooks';
import { LoadingState } from '../common/LoadingState';
import { EmptyState } from '../common/EmptyState';
import type { AuditFinding } from '../../types';

interface AuditSectionProps {
  projectId: string;
}

function SeverityBadge({ severity }: { severity: AuditFinding['severity'] }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-amber-100 text-amber-800',
    low: 'bg-green-100 text-green-800',
  };

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[severity] ?? 'bg-gray-100 text-gray-800'}`}>
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
}

function FindingStatusBadge({ status }: { status: AuditFinding['status'] }) {
  const colors: Record<string, string> = {
    open: 'bg-red-100 text-red-800',
    in_progress: 'bg-yellow-100 text-yellow-800',
    closed: 'bg-green-100 text-green-800',
  };
  const labels: Record<string, string> = {
    open: 'Open',
    in_progress: 'In Progress',
    closed: 'Closed',
  };

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] ?? 'bg-gray-100 text-gray-800'}`}>
      {labels[status] ?? status}
    </span>
  );
}

export function AuditSection({ projectId }: AuditSectionProps) {
  const { data: findings, isLoading } = useProjectAudit(projectId);

  if (isLoading) {
    return <LoadingState message="Loading audit findings..." />;
  }

  if (!findings || findings.length === 0) {
    return <EmptyState dataType="audit findings" message="No audit findings recorded for this project." />;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-700">
          Audit Findings ({findings.length})
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {findings.map((finding) => (
              <tr key={finding.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-sm text-gray-900">{finding.title}</td>
                <td className="px-4 py-2 text-sm"><SeverityBadge severity={finding.severity} /></td>
                <td className="px-4 py-2 text-sm"><FindingStatusBadge status={finding.status} /></td>
                <td className="px-4 py-2 text-sm text-gray-700">
                  {finding.target_remediation_date
                    ? new Date(finding.target_remediation_date).toLocaleDateString()
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
