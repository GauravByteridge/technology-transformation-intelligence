import { useProjectControls } from '@/hooks';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';
import type { ControlAssessmentResponse } from '@/types';

interface ControlsSectionProps {
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

const COMPLIANCE_STATUS_COLORS: Record<string, string> = {
  compliant: 'bg-green-100 text-green-800',
  non_compliant: 'bg-red-100 text-red-800',
  partially_compliant: 'bg-amber-100 text-amber-800',
  not_assessed: 'bg-gray-100 text-gray-800',
};

const COMPLIANCE_STATUS_LABELS: Record<string, string> = {
  compliant: 'Compliant',
  non_compliant: 'Non-Compliant',
  partially_compliant: 'Partially Compliant',
  not_assessed: 'Not Assessed',
};

function ComplianceStatusBadge({ status }: { status: string }) {
  const colorClass = COMPLIANCE_STATUS_COLORS[status.toLowerCase()] ?? 'bg-gray-100 text-gray-800';
  const label = COMPLIANCE_STATUS_LABELS[status.toLowerCase()] ?? status;

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  );
}

function getComplianceColor(percentage: number): string {
  if (percentage >= 80) return 'text-green-600';
  if (percentage >= 60) return 'text-amber-600';
  return 'text-red-600';
}

export function ControlsSection({ projectId }: ControlsSectionProps) {
  const { data, isLoading, isError, refetch } = useProjectControls(projectId);

  if (isLoading) {
    return <LoadingState variant="skeleton" message="Loading IT controls..." />;
  }

  if (isError) {
    return (
      <ErrorState
        message="Failed to load IT controls data. Please try again."
        onRetry={() => void refetch()}
      />
    );
  }

  if (!data || data.assessments.length === 0) {
    return <EmptyState message="No control assessments recorded for this project." />;
  }

  const { assessments, compliance_percentage } = data;

  return (
    <div className="space-y-4">
      {/* Overall compliance metric */}
      <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
        <p className="text-xs font-medium text-gray-500 uppercase">Overall IT Control Compliance</p>
        <p className={`mt-1 text-3xl font-bold ${getComplianceColor(compliance_percentage)}`}>
          {compliance_percentage.toFixed(1)}%
        </p>
      </div>

      {/* Assessments table */}
      <div className="rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-700">
            Control Assessments ({assessments.length})
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Compliance Status</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Assessed Date</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Assessor</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Notes</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Next Assessment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {assessments.map((assessment: ControlAssessmentResponse) => (
                <tr key={assessment.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm">
                    <ComplianceStatusBadge status={assessment.compliance_status} />
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-700">
                    {formatDate(assessment.assessed_date)}
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-900">
                    {assessment.assessor ?? '—'}
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-700 max-w-xs truncate" title={assessment.notes ?? undefined}>
                    {assessment.notes ?? '—'}
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-700">
                    {formatDate(assessment.next_assessment_date)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
