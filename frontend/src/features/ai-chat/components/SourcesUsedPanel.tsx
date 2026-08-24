import { useState } from 'react';
import { ChevronDown, ChevronRight, Database, FileText } from 'lucide-react';
import type { SourceReference } from '../types';

interface SourcesUsedPanelProps {
  sources: SourceReference[];
}

/** Icon and label configuration per source type. */
const SOURCE_TYPE_CONFIG: Record<
  SourceReference['source_type'],
  { icon: typeof Database; label: string; badgeColor: string }
> = {
  postgresql: { icon: Database, label: 'PostgreSQL', badgeColor: 'bg-blue-100 text-blue-800' },
  mongodb: { icon: Database, label: 'MongoDB', badgeColor: 'bg-green-100 text-green-800' },
  document: { icon: FileText, label: 'Document', badgeColor: 'bg-amber-100 text-amber-800' },
};

/**
 * SourcesUsedPanel — displays the list of data sources actively queried
 * during an AI response execution.
 *
 * Collapsed by default. Renders nothing when the sources list is empty.
 *
 * Validates: Requirements 13.1, 13.5, 7.1, 7.2
 */
export function SourcesUsedPanel({ sources }: SourcesUsedPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Don't render the panel when no sources were queried
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white" aria-label="Sources used panel">
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-gray-50 transition-colors rounded-t-lg"
        aria-expanded={isExpanded}
        aria-controls="sources-used-content"
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
        )}
        <h3 className="text-sm font-semibold text-gray-800">Sources Used</h3>
        <span className="ml-auto text-xs text-gray-400">
          {sources.length} source{sources.length !== 1 ? 's' : ''}
        </span>
      </button>

      {/* Expandable content */}
      {isExpanded && (
        <ul
          id="sources-used-content"
          className="border-t border-gray-100 px-4 py-3 space-y-2"
          role="list"
          aria-label="List of queried data sources"
        >
          {sources.map((source) => (
            <SourceItem key={source.source_id} source={source} />
          ))}
        </ul>
      )}
    </div>
  );
}

/** Renders a single source reference with type icon, name, object, record count, and duration. */
function SourceItem({ source }: { source: SourceReference }) {
  const config = SOURCE_TYPE_CONFIG[source.source_type] ?? SOURCE_TYPE_CONFIG.document;
  const IconComponent = config.icon;

  return (
    <li className="flex items-center gap-3 rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
      {/* Source type icon and badge */}
      <IconComponent className="h-4 w-4 text-gray-500 flex-shrink-0" aria-hidden="true" />
      <span className={`text-xs font-medium px-1.5 py-0.5 rounded flex-shrink-0 ${config.badgeColor}`}>
        {config.label}
      </span>

      {/* Source name and object */}
      <div className="flex flex-col min-w-0 flex-1">
        <span className="text-sm font-medium text-gray-800 truncate">
          {source.source_name}
        </span>
        <span className="text-xs text-gray-500 truncate">
          {source.object_name}
        </span>
      </div>

      {/* Record count and duration */}
      <div className="flex items-center gap-3 flex-shrink-0 text-xs text-gray-500">
        <span aria-label={`${source.records_returned} records returned`}>
          {source.records_returned} record{source.records_returned !== 1 ? 's' : ''}
        </span>
        <span aria-label={`Query took ${source.query_duration_ms} milliseconds`}>
          {formatDuration(source.query_duration_ms)}
        </span>
      </div>
    </li>
  );
}

/** Formats milliseconds into a human-readable duration string. */
function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}
