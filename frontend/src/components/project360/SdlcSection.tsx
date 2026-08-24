import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useProjectSdlc } from '@/hooks';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';
import type { SdlcPhaseResponse, SdlcMilestoneResponse, SdlcDeliverableResponse } from '@/types';

interface SdlcSectionProps {
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

const STATUS_COLORS: Record<string, string> = {
  not_started: 'bg-gray-100 text-gray-800',
  in_progress: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  delayed: 'bg-red-100 text-red-800',
  at_risk: 'bg-amber-100 text-amber-800',
  on_hold: 'bg-purple-100 text-purple-800',
};

const STATUS_LABELS: Record<string, string> = {
  not_started: 'Not Started',
  in_progress: 'In Progress',
  completed: 'Completed',
  delayed: 'Delayed',
  at_risk: 'At Risk',
  on_hold: 'On Hold',
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

/** Deliverables table for a single milestone */
function DeliverablesList({ deliverables }: { deliverables: SdlcDeliverableResponse[] }) {
  if (deliverables.length === 0) {
    return (
      <p className="py-2 pl-6 text-xs text-gray-400 italic">No deliverables</p>
    );
  }

  return (
    <div className="overflow-x-auto pl-6">
      <table className="min-w-full divide-y divide-gray-100 text-xs">
        <thead>
          <tr className="text-gray-500">
            <th className="px-3 py-1.5 text-left font-medium uppercase">Name</th>
            <th className="px-3 py-1.5 text-left font-medium uppercase">Status</th>
            <th className="px-3 py-1.5 text-left font-medium uppercase">Owner</th>
            <th className="px-3 py-1.5 text-left font-medium uppercase">Due Date</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {deliverables.map((deliverable: SdlcDeliverableResponse) => (
            <tr key={deliverable.id} className="hover:bg-gray-50">
              <td className="px-3 py-1.5 text-gray-900">{deliverable.name}</td>
              <td className="px-3 py-1.5">
                <StatusBadge status={deliverable.status} />
              </td>
              <td className="px-3 py-1.5 text-gray-700">{deliverable.owner ?? '—'}</td>
              <td className="px-3 py-1.5 text-gray-700">{formatDate(deliverable.due_date)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Collapsible milestone row with nested deliverables */
function MilestoneItem({ milestone }: { milestone: SdlcMilestoneResponse }) {
  const [expanded, setExpanded] = useState(false);
  const hasDeliverables = milestone.deliverables.length > 0;

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <button
        type="button"
        className="flex w-full items-center gap-2 px-4 py-2 text-left hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-label={`Milestone: ${milestone.name}`}
      >
        {hasDeliverables ? (
          expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-gray-400 shrink-0" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-gray-400 shrink-0" />
          )
        ) : (
          <span className="w-3.5 shrink-0" />
        )}

        <span className="flex-1 text-sm text-gray-800">{milestone.name}</span>
        <StatusBadge status={milestone.status} />
        <span className="ml-4 text-xs text-gray-500 whitespace-nowrap">
          Planned: {formatDate(milestone.planned_date)}
        </span>
        <span className="ml-2 text-xs text-gray-500 whitespace-nowrap">
          Actual: {formatDate(milestone.actual_date)}
        </span>
      </button>

      {expanded && hasDeliverables && (
        <div className="pb-2">
          <DeliverablesList deliverables={milestone.deliverables} />
        </div>
      )}
    </div>
  );
}

/** Collapsible phase card with nested milestones */
function PhaseCard({ phase }: { phase: SdlcPhaseResponse }) {
  const [expanded, setExpanded] = useState(false);
  const hasMilestones = phase.milestones.length > 0;

  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      <button
        type="button"
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-label={`Phase ${phase.sequence_order}: ${phase.phase_name}`}
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-gray-500 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-500 shrink-0" />
        )}

        <span className="text-xs text-gray-400 font-mono shrink-0">#{phase.sequence_order}</span>
        <span className="flex-1 text-sm font-medium text-gray-900">{phase.phase_name}</span>
        <StatusBadge status={phase.status} />
      </button>

      {/* Phase date details — always visible below the header */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-1 border-t border-gray-100 px-4 py-2 text-xs text-gray-500 sm:grid-cols-4">
        <div>
          <span className="font-medium">Planned Start:</span> {formatDate(phase.planned_start_date)}
        </div>
        <div>
          <span className="font-medium">Planned End:</span> {formatDate(phase.planned_end_date)}
        </div>
        <div>
          <span className="font-medium">Actual Start:</span> {formatDate(phase.actual_start_date)}
        </div>
        <div>
          <span className="font-medium">Actual End:</span> {formatDate(phase.actual_end_date)}
        </div>
      </div>

      {/* Milestones — collapsible */}
      {expanded && (
        <div className="border-t border-gray-200">
          {hasMilestones ? (
            <div className="divide-y divide-gray-100">
              {phase.milestones.map((milestone: SdlcMilestoneResponse) => (
                <MilestoneItem key={milestone.id} milestone={milestone} />
              ))}
            </div>
          ) : (
            <p className="px-4 py-3 text-xs text-gray-400 italic">No milestones for this phase</p>
          )}
        </div>
      )}
    </div>
  );
}

export function SdlcSection({ projectId }: SdlcSectionProps) {
  const { data, isLoading, isError, refetch } = useProjectSdlc(projectId);

  if (isLoading) {
    return <LoadingState variant="skeleton" message="Loading SDLC phases..." />;
  }

  if (isError) {
    return (
      <ErrorState
        message="Failed to load SDLC data. Please try again."
        onRetry={() => void refetch()}
      />
    );
  }

  if (!data || data.phases.length === 0) {
    return <EmptyState message="No SDLC phases configured for this project." />;
  }

  const { phases } = data;
  // Sort phases by sequence_order
  const sortedPhases = [...phases].sort((a, b) => a.sequence_order - b.sequence_order);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">
          SDLC Phases ({sortedPhases.length})
        </h3>
      </div>

      <div className="space-y-3">
        {sortedPhases.map((phase: SdlcPhaseResponse) => (
          <PhaseCard key={phase.id} phase={phase} />
        ))}
      </div>
    </div>
  );
}
