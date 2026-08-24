import { useState } from 'react';
import { ChevronDown, ChevronRight, Database, FileText, Shield } from 'lucide-react';
import type { EvidenceItem } from '../types';

interface EvidencePanelProps {
  evidence: EvidenceItem[];
}

/** Maps confidence classification to badge styling and human-readable label. */
const CONFIDENCE_CONFIG: Record<
  EvidenceItem['confidence'],
  { label: string; className: string }
> = {
  retrieved_fact: {
    label: 'Retrieved Fact',
    className: 'bg-green-100 text-green-800',
  },
  derived_calculation: {
    label: 'Derived Calculation',
    className: 'bg-blue-100 text-blue-800',
  },
  ai_explanation: {
    label: 'AI Explanation',
    className: 'bg-gray-100 text-gray-700',
  },
};

/** Icon per source type for visual differentiation. */
const SOURCE_ICON: Record<EvidenceItem['source_type'], typeof Database> = {
  postgresql: Database,
  mongodb: Database,
  document: FileText,
};

/**
 * EvidencePanel — Collapsible panel listing evidence items supporting an AI response.
 *
 * Each item shows source name + object, an excerpt, and a confidence badge.
 * Items are individually expandable to reveal full details (delegated to
 * EvidenceItemDetail in task 12.2; for now shows the full excerpt inline).
 *
 * Collapsed by default to keep the answer area clean.
 * Returns null when there is no evidence to display.
 */
export function EvidencePanel({ evidence }: EvidencePanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Don't render the panel when there is no evidence
  if (!evidence || evidence.length === 0) {
    return null;
  }

  return (
    <div
      className="rounded-lg border border-gray-200 bg-white"
      aria-label="Evidence panel"
    >
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-gray-50 transition-colors rounded-lg"
        aria-expanded={isExpanded}
        aria-controls="evidence-panel-content"
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
        )}
        <Shield className="h-4 w-4 text-indigo-500 flex-shrink-0" />
        <h3 className="text-sm font-semibold text-gray-800">Evidence</h3>
        <span className="ml-auto text-xs text-gray-400">
          {evidence.length} {evidence.length === 1 ? 'item' : 'items'}
        </span>
      </button>

      {/* Panel content — list of expandable evidence items */}
      {isExpanded && (
        <div
          id="evidence-panel-content"
          className="border-t border-gray-100 px-4 py-3 space-y-2"
        >
          {evidence.map((item) => (
            <EvidenceItemCard key={item.evidence_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * EvidenceItemCard — Single expandable evidence entry.
 *
 * Collapsed: shows source reference line + confidence badge + truncated excerpt.
 * Expanded: shows the full excerpt. (Task 12.2 will replace the expanded view
 * with the full EvidenceItemDetail component.)
 */
function EvidenceItemCard({ item }: { item: EvidenceItem }) {
  const [isItemExpanded, setIsItemExpanded] = useState(false);

  const confidenceCfg = CONFIDENCE_CONFIG[item.confidence];
  const IconComponent = SOURCE_ICON[item.source_type];
  const sourceLabel = buildSourceLabel(item);

  return (
    <div className="rounded-md border border-gray-200 bg-gray-50 overflow-hidden">
      {/* Item header — always visible */}
      <button
        type="button"
        onClick={() => setIsItemExpanded((prev) => !prev)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-white transition-colors"
        aria-expanded={isItemExpanded}
      >
        {isItemExpanded ? (
          <ChevronDown className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
        )}
        <IconComponent className="h-3.5 w-3.5 text-gray-500 flex-shrink-0" />
        <span className="text-xs font-medium text-gray-700 truncate">
          {sourceLabel}
        </span>
        <span
          className={`ml-auto text-xs font-medium px-1.5 py-0.5 rounded flex-shrink-0 ${confidenceCfg.className}`}
        >
          {confidenceCfg.label}
        </span>
      </button>

      {/* Collapsed excerpt preview */}
      {!isItemExpanded && item.excerpt && (
        <div className="px-3 pb-2">
          <p className="text-xs text-gray-600 line-clamp-2 italic">
            {item.excerpt}
          </p>
        </div>
      )}

      {/* Expanded detail — full excerpt (EvidenceItemDetail in 12.2 will enhance this) */}
      {isItemExpanded && (
        <div className="border-t border-gray-100 px-3 py-2 space-y-2">
          {item.excerpt && (
            <blockquote className="border-l-3 border-indigo-300 bg-indigo-50 px-3 py-2 text-xs text-gray-700 italic rounded-r">
              {item.excerpt}
            </blockquote>
          )}
          <EvidenceMetadata item={item} />
        </div>
      )}
    </div>
  );
}

/** Renders additional metadata fields when an evidence item is expanded. */
function EvidenceMetadata({ item }: { item: EvidenceItem }) {
  const fields: { label: string; value: string | number | undefined }[] = [];

  if (item.database_name) fields.push({ label: 'Database', value: item.database_name });
  if (item.schema_name) fields.push({ label: 'Schema', value: item.schema_name });
  if (item.table_name) fields.push({ label: 'Table', value: item.table_name });
  if (item.collection_name) fields.push({ label: 'Collection', value: item.collection_name });
  if (item.column_names?.length) fields.push({ label: 'Columns', value: item.column_names.join(', ') });
  if (item.record_reference) fields.push({ label: 'Record', value: item.record_reference });
  if (item.file_name) fields.push({ label: 'File', value: item.file_name });
  if (item.page_number != null) fields.push({ label: 'Page', value: item.page_number });
  if (item.sheet_name) fields.push({ label: 'Sheet', value: item.sheet_name });
  if (item.section) fields.push({ label: 'Section', value: item.section });

  if (fields.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
      {fields.map(({ label, value }) => (
        <span key={label}>
          <span className="font-medium text-gray-500">{label}:</span> {value}
        </span>
      ))}
    </div>
  );
}

/**
 * Builds a human-readable source label from an evidence item.
 * Format: "SourceName — object_name" (e.g., "PostgreSQL — project_finance")
 */
function buildSourceLabel(item: EvidenceItem): string {
  const sourceName = item.source_name || item.source_type;
  const objectName = item.object_name;
  return `${sourceName} — ${objectName}`;
}
