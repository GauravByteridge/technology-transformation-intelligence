import { useState } from 'react';
import { Database, FileText, StickyNote, ChevronDown, ChevronRight, Info } from 'lucide-react';
import type { SourceEvidence, SourceType } from '../../types';

interface EvidencePanelProps {
  /** Array of source evidence items from the AI response */
  evidence: SourceEvidence[];
}

/** Maps source type to its icon component and accessible label */
const SOURCE_TYPE_CONFIG: Record<SourceType, { icon: typeof Database; label: string; color: string }> = {
  database: { icon: Database, label: 'Database source', color: 'text-blue-600' },
  document: { icon: FileText, label: 'Document source', color: 'text-amber-600' },
  notes: { icon: StickyNote, label: 'Notes source', color: 'text-green-600' },
};

/**
 * EvidencePanel — displays source attribution for AI responses.
 *
 * Shows 1–10 source names with type indicators. Each source is expandable
 * to reveal data rows/excerpts (max 50 items per source) and collapsible
 * back to summary state. Displays a message when no sources were queried.
 *
 * Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
 */
export function EvidencePanel({ evidence }: EvidencePanelProps) {
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());

  // Requirement 7.3: Show message when no sources were queried
  if (!evidence || evidence.length === 0) {
    return (
      <div
        className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3"
        role="status"
        aria-label="No sources queried"
      >
        <Info className="h-4 w-4 text-gray-400 flex-shrink-0" />
        <p className="text-sm text-gray-500">No sources were queried for this response.</p>
      </div>
    );
  }

  const toggleSource = (sourceName: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      if (next.has(sourceName)) {
        next.delete(sourceName);
      } else {
        next.add(sourceName);
      }
      return next;
    });
  };

  return (
    <div className="space-y-2" aria-label="Evidence sources">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
        Sources ({evidence.length})
      </h3>
      {evidence.map((source) => {
        const isExpanded = expandedSources.has(source.source_name);
        const config = SOURCE_TYPE_CONFIG[source.source_type];
        const IconComponent = config.icon;
        // Requirement 7.2: max 50 items per source
        const visibleItems = source.data_items.slice(0, 50);

        return (
          <div
            key={source.source_name}
            className="rounded-lg border border-gray-200 bg-white overflow-hidden"
          >
            {/* Collapsible header */}
            <button
              type="button"
              onClick={() => toggleSource(source.source_name)}
              className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
              aria-expanded={isExpanded}
              aria-controls={`evidence-${source.source_name}`}
            >
              {/* Expand/collapse chevron */}
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
              )}
              {/* Type indicator icon */}
              <IconComponent
                className={`h-4 w-4 flex-shrink-0 ${config.color}`}
                aria-label={config.label}
              />
              {/* Human-readable display name */}
              <span className="text-sm font-medium text-gray-800 truncate">
                {source.display_name}
              </span>
              {/* Item count badge */}
              {source.data_items.length > 0 && (
                <span className="ml-auto text-xs text-gray-400">
                  {Math.min(source.data_items.length, 50)} item{source.data_items.length !== 1 ? 's' : ''}
                </span>
              )}
            </button>

            {/* Expandable data items section */}
            {isExpanded && (
              <div
                id={`evidence-${source.source_name}`}
                className="border-t border-gray-100 px-4 py-3 bg-gray-50"
                role="region"
                aria-label={`Data from ${source.display_name}`}
              >
                {visibleItems.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">No data items available.</p>
                ) : (
                  <ul className="space-y-2 max-h-64 overflow-y-auto">
                    {visibleItems.map((item, index) => (
                      <li
                        key={index}
                        className="rounded border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700"
                      >
                        <DataItemRow item={item} />
                      </li>
                    ))}
                  </ul>
                )}
                {source.data_items.length > 50 && (
                  <p className="mt-2 text-xs text-gray-400 italic">
                    Showing 50 of {source.data_items.length} items.
                  </p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** Renders key-value pairs from a data item record */
function DataItemRow({ item }: { item: Record<string, unknown> }) {
  const entries = Object.entries(item);

  if (entries.length === 0) {
    return <span className="text-gray-400 italic">Empty record</span>;
  }

  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1">
      {entries.map(([key, value]) => (
        <span key={key}>
          <span className="font-medium text-gray-500">{formatKey(key)}:</span>{' '}
          <span className="text-gray-800">{formatValue(value)}</span>
        </span>
      ))}
    </div>
  );
}

/** Converts snake_case keys to readable labels */
function formatKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Formats unknown values to display strings */
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
