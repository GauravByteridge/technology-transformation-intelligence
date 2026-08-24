import { useProjectAudit } from '@/hooks';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';
import type { AuditFindingResponse } from '@/types';

interface AuditSectionProps {
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

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-green-100 text-green-800',
};

function SeverityBadge({ severity }: { severity: string }) {
  const colorClass = SEVERITY_COLORS[severity.toLowerCase()] ?? 'bg-gray-100 text-gray-800';

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}>
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
}

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-red-100 text-red-800',
  in_progress: 'bg-yellow-100 text-yellow-800',
  closed: 'bg-green-100 text-green-800',
  remediated: 'bg-green-100 text-green-800',
};

const STATUS_LABELS: Record<string, string> = {
  open: 'Open',
  in_progress: 'In Progress',
  closed: 'Closed',
  remediated: 'Remediated',
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

export function AuditSection({ projectId }: AuditSectionProps) {
  const { data, isLoading, isError, refetch } = useProjectAudit(projectId);

  if (isLoading) {
    return <LoadingState variant="skeleton" message="Loading audit findings..." />;
  }

  if (isError) {
    return (
      <ErrorState
        message="Failed to load audit findings. Please try again."
        onRetry={() => void refetch()}
      />
    );
  }

  if (!data || data.findings.length === 0) {
    return <EmptyState message="No audit findings recorded for this project." />;
  }

  const { findings, overdue_count } = data;

  return (
    <div className="space-y-4">
      {/* Summary metrics */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
          <p className="text-xs font-medium text-gray-500 uppercase">Total Findings</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{findings.length}</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
          <p className="text-xs font-medium text-gray-500 uppercase">Overdue</p>
          <p className={`mt-1 text-2xl font-semibold ${overdue_count > 0 ? 'text-red-600' : 'text-gray-900'}`}>
            {overdue_count}
          </p>
        </div>
      </div>

      {/* Findings table */}
      <div className="rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-700">
            Audit Findings
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Reference</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Identified</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Target Remediation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {findings.map((finding: AuditFindingResponse) => (
                <tr key={finding.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm font-mono text-gray-700">{finding.finding_reference}</td>
                  <td className="px-4 py-2 text-sm text-gray-900">{finding.title}</td>
                  <td className="px-4 py-2 text-sm">
                    <SeverityBadge severity={finding.severity} />
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <StatusBadge status={finding.status} />
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-700">{formatDate(finding.identified_date)}</td>
                  <td className="px-4 py-2 text-sm text-gray-700">{formatDate(finding.target_remediation_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
