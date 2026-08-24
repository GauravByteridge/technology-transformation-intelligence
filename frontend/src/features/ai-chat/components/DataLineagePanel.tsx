import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  Wrench,
  Sparkles,
  MessageSquare,
} from 'lucide-react';
import type { LineageTrace, LineageStep } from '../types';

interface DataLineagePanelProps {
  lineage: LineageTrace;
}

/** Status color mapping for lineage step indicators */
const STATUS_CONFIG: Record<string, { color: string; bgColor: string; icon: typeof CheckCircle2 }> = {
  success: { color: 'text-green-600', bgColor: 'bg-green-100', icon: CheckCircle2 },
  failed: { color: 'text-red-600', bgColor: 'bg-red-100', icon: XCircle },
  timeout: { color: 'text-orange-600', bgColor: 'bg-orange-100', icon: Clock },
};

/** Step type display configuration */
const STEP_TYPE_CONFIG: Record<string, { icon: typeof Search; label: string }> = {
  catalog_lookup: { icon: Search, label: 'Catalog Lookup' },
  tool_invocation: { icon: Wrench, label: 'Tool Invocation' },
  synthesis: { icon: Sparkles, label: 'Synthesis' },
};

/**
 * DataLineagePanel — displays the full execution trace for an AI query.
 *
 * Shows the path: Question → Catalog Lookup → Tool Invocations → Evidence → Answer
 * as a vertical sequence with connecting lines between steps.
 *
 * Validates: Requirements 13.3, 13.5, 6.1, 6.4
 */
export function DataLineagePanel({ lineage }: DataLineagePanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Don't render if no lineage trace or no steps
  if (!lineage || !lineage.steps || lineage.steps.length === 0) {
    return null;
  }

  const successCount = lineage.steps.filter((s) => s.status === 'success').length;
  const failedCount = lineage.steps.filter((s) => s.status === 'failed' || s.status === 'timeout').length;

  return (
    <div className="rounded-lg border border-gray-200 bg-white" aria-label="Data lineage panel">
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-gray-50 transition-colors rounded-t-lg"
        aria-expanded={isExpanded}
        aria-controls="data-lineage-content"
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
        )}
        <h3 className="text-sm font-semibold text-gray-800">Data Lineage</h3>
        <span className="ml-auto text-xs text-gray-400">
          {lineage.steps.length} step{lineage.steps.length !== 1 ? 's' : ''} ·{' '}
          {lineage.total_duration_ms}ms
          {failedCount > 0 && (
            <span className="ml-1 text-red-500">
              ({failedCount} failed)
            </span>
          )}
        </span>
      </button>

      {/* Expandable content */}
      {isExpanded && (
        <div id="data-lineage-content" className="border-t border-gray-100 px-4 py-3">
          {/* Execution flow as vertical sequence */}
          <div className="relative space-y-0">
            {/* Question node (always first) */}
            <LineageNode
              icon={MessageSquare}
              label="Question"
              detail={lineage.question}
              status="success"
              isFirst
              isLast={false}
            />

            {/* Lineage steps */}
            {lineage.steps.map((step, index) => (
              <LineageStepNode
                key={`${step.step_type}-${step.timestamp}-${index}`}
                step={step}
                isLast={index === lineage.steps.length - 1}
              />
            ))}
          </div>

          {/* Summary footer */}
          <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-green-500" />
              {successCount} successful
            </span>
            {failedCount > 0 && (
              <span className="flex items-center gap-1">
                <XCircle className="h-3 w-3 text-red-500" />
                {failedCount} failed
              </span>
            )}
            <span className="ml-auto">
              {lineage.sources_consulted.length} source{lineage.sources_consulted.length !== 1 ? 's' : ''} consulted
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

/** Renders a single lineage step as a vertical node in the flow */
function LineageStepNode({ step, isLast }: { step: LineageStep; isLast: boolean }) {
  const stepConfig = STEP_TYPE_CONFIG[step.step_type] || STEP_TYPE_CONFIG.tool_invocation;

  const label = getStepLabel(step);
  const detail = getStepDetail(step);

  return (
    <LineageNode
      icon={stepConfig.icon}
      label={label}
      detail={detail}
      status={step.status}
      durationMs={step.duration_ms}
      recordsCount={step.records_count}
      error={step.error}
      isFirst={false}
      isLast={isLast}
    />
  );
}

/** Returns a human-readable label for a lineage step */
function getStepLabel(step: LineageStep): string {
  switch (step.step_type) {
    case 'catalog_lookup':
      return 'Catalog Lookup';
    case 'synthesis':
      return 'Synthesis';
    case 'tool_invocation':
      return step.tool_name || 'Tool Invocation';
    default:
      return step.step_type;
  }
}

/** Returns detail text for a lineage step */
function getStepDetail(step: LineageStep): string | null {
  switch (step.step_type) {
    case 'catalog_lookup':
      return step.records_count > 0
        ? `${step.records_count} entries found`
        : 'No entries found';
    case 'tool_invocation':
      return [step.source_name, step.object_name].filter(Boolean).join(' → ') || null;
    case 'synthesis':
      return 'Generating answer from evidence';
    default:
      return null;
  }
}

/** A single node in the vertical lineage flow with connecting line */
function LineageNode({
  icon: Icon,
  label,
  detail,
  status,
  durationMs,
  recordsCount,
  error,
  isFirst,
  isLast,
}: {
  icon: typeof Search;
  label: string;
  detail: string | null;
  status: string;
  durationMs?: number;
  recordsCount?: number;
  error?: string;
  isFirst: boolean;
  isLast: boolean;
}) {
  const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG.success;
  const StatusIcon = statusConfig.icon;

  return (
    <div className="relative flex items-start gap-3 pb-4 last:pb-0">
      {/* Vertical connecting line */}
      {!isLast && (
        <div
          className="absolute left-[15px] top-[30px] bottom-0 w-px bg-gray-200"
          aria-hidden="true"
        />
      )}

      {/* Node icon circle */}
      <div
        className={`relative z-10 flex h-[30px] w-[30px] flex-shrink-0 items-center justify-center rounded-full border ${
          isFirst ? 'border-blue-200 bg-blue-50' : `border-gray-200 ${statusConfig.bgColor}`
        }`}
      >
        <Icon className={`h-3.5 w-3.5 ${isFirst ? 'text-blue-600' : statusConfig.color}`} />
      </div>

      {/* Node content */}
      <div className="flex-1 min-w-0 pt-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-gray-800">{label}</span>
          {!isFirst && (
            <StatusIcon className={`h-3.5 w-3.5 ${statusConfig.color}`} aria-label={`Status: ${status}`} />
          )}
          {durationMs != null && (
            <span className="text-xs text-gray-400">{durationMs}ms</span>
          )}
          {recordsCount != null && recordsCount > 0 && (
            <span className="text-xs text-gray-400">
              {recordsCount} record{recordsCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {detail && (
          <p className="text-xs text-gray-500 mt-0.5 truncate">{detail}</p>
        )}
        {error && (
          <p className="text-xs text-red-500 mt-0.5 truncate">{error}</p>
        )}
      </div>
    </div>
  );
}
