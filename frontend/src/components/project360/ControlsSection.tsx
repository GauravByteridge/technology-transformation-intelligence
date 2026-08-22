import { useProjectControls } from '../../hooks';
import { LoadingState } from '../common/LoadingState';
import { EmptyState } from '../common/EmptyState';
import type { ITControl } from '../../types';

interface ControlsSectionProps {
  projectId: string;
}

function ComplianceBadge({ status }: { status: ITControl['compliance_status'] }) {
  const colors: Record<string, string> = {
    compliant: 'bg-green-100 text-green-800',
    non_compliant: 'bg-red-100 text-red-800',
    not_assessed: 'bg-gray-100 text-gray-800',
  };
  const labels: Record<string, string> = {
    compliant: 'Compliant',
    non_compliant: 'Non-Compliant',
    not_assessed: 'Not Assessed',
  };

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] ?? 'bg-gray-100 text-gray-800'}`}>
      {labels[status] ?? status}
    </span>
  );
}

export function ControlsSection({ projectId }: ControlsSectionProps) {
  const { data: controls, isLoading } = useProjectControls(projectId);

  if (isLoading) {
    return <LoadingState message="Loading IT controls..." />;
  }

  if (!controls || controls.length === 0) {
    return <EmptyState dataType="IT controls" message="No controls data available for this project." />;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-700">
          IT Controls ({controls.length})
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Control Name</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Compliance Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Last Assessment Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {controls.map((control) => (
              <tr key={control.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-sm text-gray-900">{control.control_name}</td>
                <td className="px-4 py-2 text-sm"><ComplianceBadge status={control.compliance_status} /></td>
                <td className="px-4 py-2 text-sm text-gray-700">
                  {control.last_assessment_date
                    ? new Date(control.last_assessment_date).toLocaleDateString()
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
