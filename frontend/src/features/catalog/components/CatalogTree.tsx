import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, Table2, Database, FileText, Tag, Columns3 } from 'lucide-react';

import { LoadingState, ErrorState, EmptyState } from '@/components/common';
import type { CatalogEntry, CatalogField } from '../types';
import { getCatalogForSource } from '../services/catalogService';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CatalogTreeProps {
  /** The data source ID to display catalog entries for. */
  sourceId: string;
  /** If provided, skips the API call and renders these entries directly. */
  entries?: CatalogEntry[];
}

// ---------------------------------------------------------------------------
// Icons for object types
// ---------------------------------------------------------------------------

const OBJECT_TYPE_ICONS: Record<string, typeof Table2> = {
  table: Table2,
  collection: Database,
  view: Columns3,
  document: FileText,
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Renders a single field row within a catalog object node. */
function FieldNode({ field }: { field: CatalogField }) {
  const semanticLabel = field.semantic_label ? ` (${field.semantic_label})` : '';

  return (
    <li className="flex items-center gap-2 py-1 pl-10 text-sm text-gray-600">
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-gray-400 flex-shrink-0" aria-hidden="true" />
      <span className="font-mono text-xs text-gray-800">{field.name}</span>
      <span className="text-xs text-gray-500">{field.field_type}</span>
      {semanticLabel && (
        <span className="text-xs italic text-indigo-600">{semanticLabel}</span>
      )}
      {field.is_primary_key && (
        <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800">PK</span>
      )}
      {field.is_sensitive && (
        <span className="rounded bg-red-100 px-1.5 py-0.5 text-[10px] font-medium text-red-800">Sensitive</span>
      )}
    </li>
  );
}

/** Renders a single catalog entry (table/collection) as an expandable node. */
function ObjectNode({ entry }: { entry: CatalogEntry }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const Icon = OBJECT_TYPE_ICONS[entry.object_type] ?? Table2;
  const displayName = entry.semantic_name || entry.object_name;

  return (
    <li className="border-b border-gray-100 last:border-b-0">
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left hover:bg-gray-50 transition-colors"
        aria-expanded={isExpanded}
        aria-controls={`catalog-fields-${entry.entry_id}`}
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
        )}
        <Icon className="h-4 w-4 text-blue-600 flex-shrink-0" aria-hidden="true" />
        <span className="text-sm font-medium text-gray-900">{displayName}</span>
        {entry.semantic_name && entry.semantic_name !== entry.object_name && (
          <span className="text-xs text-gray-500 font-mono">({entry.object_name})</span>
        )}
        <span className="ml-auto text-xs text-gray-400">{entry.fields.length} fields</span>
      </button>

      {/* Domain tags and description */}
      {isExpanded && (
        <div id={`catalog-fields-${entry.entry_id}`} className="pb-2">
          {/* Semantic description */}
          {entry.semantic_description && (
            <p className="px-9 pb-1 text-xs text-gray-500">{entry.semantic_description}</p>
          )}

          {/* Domain tags */}
          {entry.domain_tags.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 px-9 pb-2">
              <Tag className="h-3 w-3 text-gray-400" aria-hidden="true" />
              {entry.domain_tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Fields list */}
          {entry.fields.length > 0 ? (
            <ul role="list" className="space-y-0.5">
              {entry.fields.map((field) => (
                <FieldNode key={field.name} field={field} />
              ))}
            </ul>
          ) : (
            <p className="px-9 text-xs text-gray-400">No fields discovered.</p>
          )}
        </div>
      )}
    </li>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * CatalogTree — displays an expandable tree view of discovered catalog entries
 * (tables/collections/documents) and their fields for a given data source.
 *
 * Used inside the Data Sources page when a source card is expanded.
 */
export function CatalogTree({ sourceId, entries: externalEntries }: CatalogTreeProps) {
  const {
    data: fetchedEntries,
    isLoading,
    isError,
    refetch,
  } = useQuery<CatalogEntry[]>({
    queryKey: ['catalog', 'source', sourceId],
    queryFn: () => getCatalogForSource(sourceId),
    enabled: !externalEntries,
  });

  const entries = externalEntries ?? fetchedEntries;

  if (!externalEntries && isLoading) {
    return <LoadingState variant="inline" message="Loading catalog..." />;
  }

  if (!externalEntries && isError) {
    return (
      <ErrorState
        message="Failed to load catalog entries."
        onRetry={() => refetch()}
      />
    );
  }

  if (!entries || entries.length === 0) {
    return (
      <EmptyState message="No catalog entries discovered for this source. Run discovery to populate the catalog." />
    );
  }

  return (
    <div className="rounded-md border border-gray-200 bg-white" role="tree" aria-label="Catalog schema tree">
      <ul role="group" className="divide-y divide-gray-100">
        {entries.map((entry) => (
          <ObjectNode key={entry.entry_id} entry={entry} />
        ))}
      </ul>
    </div>
  );
}
