import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Database,
  FileText,
  Table2,
  Shield,
} from 'lucide-react';
import type { EvidenceItem } from '../types';

interface EvidenceItemDetailProps {
  item: EvidenceItem;
}

/** Badge color based on groundedness confidence classification */
const CONFIDENCE_CONFIG: Record<string, { label: string; className: string }> = {
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
    className: 'bg-amber-100 text-amber-800',
  },
};

/** Icon for each source type */
const SOURCE_TYPE_ICON: Record<string, typeof Database> = {
  postgresql: Database,
  mongodb: Database,
  document: FileText,
};

/**
 * EvidenceItemDetail — Expandable detail view for a single evidence item.
 *
 * Handles different rendering for database evidence (PostgreSQL/MongoDB)
 * vs. document evidence (PDF, DOCX, Excel, etc.).
 *
 * Database evidence shows: database_name, schema_name, table_name/collection_name,
 * column_names, record_reference, records_summary.
 *
 * Document evidence shows: file_name, page_number, sheet_name, section, full excerpt.
 *
 * Validates: Requirements 13.2, 13.4, 5.3, 5.4, 5.5
 */
export function EvidenceItemDetail({ item }: EvidenceItemDetailProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const isDatabaseEvidence =
    item.source_type === 'postgresql' || item.source_type === 'mongodb';
  const IconComponent =
    SOURCE_TYPE_ICON[item.source_type] ?? FileText;
  const confidenceConfig =
    CONFIDENCE_CONFIG[item.confidence] ?? CONFIDENCE_CONFIG.retrieved_fact;

  return (
    <div
      className="rounded-md border border-gray-200 bg-white overflow-hidden"
      aria-label={`Evidence from ${item.source_name}`}
    >
      {/* Collapsed header — always visible */}
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left hover:bg-gray-50 transition-colors"
        aria-expanded={isExpanded}
        aria-controls={`evidence-detail-${item.evidence_id}`}
      >
        {isExpanded ? (
          <ChevronDown className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
        )}
        <IconComponent className="h-3.5 w-3.5 text-gray-500 flex-shrink-0" />
        <span className="text-xs font-medium text-gray-800 truncate">
          {item.source_name}
        </span>
        <span className="text-xs text-gray-500 truncate">
          — {item.object_name}
        </span>
        <span
          className={`ml-auto text-[10px] font-medium px-1.5 py-0.5 rounded flex-shrink-0 ${confidenceConfig.className}`}
        >
          {confidenceConfig.label}
        </span>
      </button>

      {/* Expandable detail content */}
      {isExpanded && (
        <div
          id={`evidence-detail-${item.evidence_id}`}
          className="border-t border-gray-100 px-3 py-3 space-y-3"
        >
          {isDatabaseEvidence ? (
            <DatabaseEvidenceDetail item={item} />
          ) : (
            <DocumentEvidenceDetail item={item} />
          )}

          {/* Full excerpt — always shown when expanded */}
          <ExcerptSection excerpt={item.excerpt} />
        </div>
      )}
    </div>
  );
}

/**
 * Renders database-specific evidence fields:
 * database_name, schema_name, table_name/collection_name,
 * column_names, record_reference, records_summary.
 */
function DatabaseEvidenceDetail({ item }: { item: EvidenceItem }) {
  const tableName = item.table_name ?? item.collection_name;
  const isPostgres = item.source_type === 'postgresql';

  return (
    <div className="space-y-2">
      {/* Source path: database > schema > table/collection */}
      <div className="flex items-center gap-1.5 text-xs text-gray-600">
        <Database className="h-3 w-3 text-gray-400 flex-shrink-0" />
        <span className="font-medium text-gray-500">
          {isPostgres ? 'Table Path:' : 'Collection Path:'}
        </span>
        <span className="font-mono text-gray-700">
          {[item.database_name, item.schema_name, tableName]
            .filter(Boolean)
            .join(' → ')}
        </span>
      </div>

      {/* Metadata grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {item.database_name && (
          <MetadataField label="Database" value={item.database_name} />
        )}
        {item.schema_name && (
          <MetadataField label="Schema" value={item.schema_name} />
        )}
        {tableName && (
          <MetadataField
            label={isPostgres ? 'Table' : 'Collection'}
            value={tableName}
          />
        )}
        {item.record_reference && (
          <MetadataField label="Record Ref" value={item.record_reference} />
        )}
      </div>

      {/* Column names */}
      {item.column_names && item.column_names.length > 0 && (
        <div className="space-y-1">
          <span className="text-xs font-medium text-gray-500 flex items-center gap-1">
            <Table2 className="h-3 w-3" />
            Columns
          </span>
          <div className="flex flex-wrap gap-1">
            {item.column_names.map((col) => (
              <span
                key={col}
                className="inline-block text-[11px] font-mono bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded"
              >
                {col}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Records summary */}
      {item.records_summary &&
        Object.keys(item.records_summary).length > 0 && (
          <div className="space-y-1">
            <span className="text-xs font-medium text-gray-500">
              Records Summary
            </span>
            <div className="rounded bg-gray-50 border border-gray-100 p-2 overflow-x-auto">
              <pre className="text-[11px] text-gray-700 whitespace-pre-wrap font-mono">
                {JSON.stringify(item.records_summary, null, 2)}
              </pre>
            </div>
          </div>
        )}
    </div>
  );
}

/**
 * Renders document-specific evidence fields:
 * file_name, page_number, sheet_name, section, full excerpt.
 */
function DocumentEvidenceDetail({ item }: { item: EvidenceItem }) {
  return (
    <div className="space-y-2">
      {/* Document identifier with icon */}
      <div className="flex items-center gap-1.5 text-xs text-gray-600">
        <FileText className="h-3 w-3 text-gray-400 flex-shrink-0" />
        <span className="font-medium text-gray-500">Document:</span>
        <span className="text-gray-700 font-medium truncate">
          {item.file_name ?? item.object_name}
        </span>
      </div>

      {/* Metadata grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {item.file_name && (
          <MetadataField label="File" value={item.file_name} />
        )}
        {item.page_number != null && (
          <MetadataField label="Page" value={String(item.page_number)} />
        )}
        {item.sheet_name && (
          <MetadataField label="Sheet" value={item.sheet_name} />
        )}
        {item.section && (
          <MetadataField label="Section" value={item.section} />
        )}
      </div>
    </div>
  );
}

/** Renders the full data excerpt in a styled blockquote */
function ExcerptSection({ excerpt }: { excerpt: string }) {
  if (!excerpt) return null;

  return (
    <div className="space-y-1">
      <span className="text-xs font-medium text-gray-500 flex items-center gap-1">
        <Shield className="h-3 w-3" />
        Data Excerpt
      </span>
      <blockquote className="border-l-3 border-blue-300 bg-blue-50 px-3 py-2 text-xs text-gray-700 italic rounded-r">
        {excerpt}
      </blockquote>
    </div>
  );
}

/** Renders a single labeled metadata field */
function MetadataField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-1.5 text-xs">
      <span className="font-medium text-gray-500 whitespace-nowrap">
        {label}:
      </span>
      <span className="text-gray-700 truncate" title={value}>
        {value}
      </span>
    </div>
  );
}
