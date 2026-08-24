import { useState } from 'react';
import {
  Database,
  FileText,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Tag,
  Layers,
} from 'lucide-react';
import { LoadingState, ErrorState, EmptyState } from '@/components/common';
import { useCatalogEntries } from '../hooks/useCatalog';
import type { CatalogEntry, CatalogField } from '../types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Maximum number of key fields displayed per catalog entry. */
const MAX_DISPLAY_FIELDS = 6;

/** Icon and styling configuration per source type. */
const SOURCE_TYPE_CONFIG: Record<
  CatalogEntry['source_type'],
  { icon: typeof Database; label: string; badgeColor: string }
> = {
  postgresql: { icon: Database, label: 'PostgreSQL', badgeColor: 'bg-blue-100 text-blue-800' },
  mongodb: { icon: Database, label: 'MongoDB', badgeColor: 'bg-green-100 text-green-800' },
  document: { icon: FileText, label: 'Document', badgeColor: 'bg-amber-100 text-amber-800' },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Groups catalog entries by their domain tags. Entries with no tags go into "Uncategorized". */
function groupByDomain(entries: CatalogEntry[]): Record<string, CatalogEntry[]> {
  const groups: Record<string, CatalogEntry[]> = {};

  for (const entry of entries) {
    const tags = entry.domain_tags.length > 0 ? entry.domain_tags : ['Uncategorized'];

    for (const tag of tags) {
      const domainKey = formatDomainLabel(tag);
      if (!groups[domainKey]) {
        groups[domainKey] = [];
      }
      groups[domainKey].push(entry);
    }
  }

  return groups;
}

/** Capitalizes a domain tag string for display (e.g., "finance" → "Finance"). */
function formatDomainLabel(tag: string): string {
  return tag.charAt(0).toUpperCase() + tag.slice(1).toLowerCase();
}

/** Returns the display name for a catalog entry, preferring semantic_name. */
function getDisplayName(entry: CatalogEntry): string {
  return entry.semantic_name || entry.object_name;
}

/** Returns key fields (first N) with semantic labels where available. */
function getKeyFields(fields: CatalogField[], limit: number = MAX_DISPLAY_FIELDS): CatalogField[] {
  return fields.slice(0, limit);
}

// ---------------------------------------------------------------------------
// Sub-Components
// ---------------------------------------------------------------------------

/** Renders a single catalog entry card within a domain group. */
function CatalogEntryCard({ entry }: { entry: CatalogEntry }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const config = SOURCE_TYPE_CONFIG[entry.source_type] ?? SOURCE_TYPE_CONFIG.document;
  const IconComponent = config.icon;
  const keyFields = getKeyFields(entry.fields);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 hover:shadow-sm transition-shadow">
      {/* Header: source icon + name + description */}
      <div className="flex items-start gap-3">
        <IconComponent className="h-5 w-5 text-gray-500 mt-0.5 flex-shrink-0" aria-hidden="true" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-gray-900 truncate">
              {getDisplayName(entry)}
            </h3>
            <span
              className={`text-xs font-medium px-1.5 py-0.5 rounded flex-shrink-0 ${config.badgeColor}`}
            >
              {config.label}
            </span>
            {entry.confidence && entry.confidence !== 'high' && (
              <span className="text-xs text-gray-400 italic">
                ({entry.confidence} confidence)
              </span>
            )}
          </div>
          {entry.semantic_description && (
            <p className="mt-1 text-sm text-gray-600 line-clamp-2">
              {entry.semantic_description}
            </p>
          )}
        </div>
      </div>

      {/* Key fields */}
      {keyFields.length > 0 && (
        <div className="mt-3">
          <div className="flex items-center gap-1 mb-1.5">
            <Tag className="h-3.5 w-3.5 text-gray-400" aria-hidden="true" />
            <span className="text-xs font-medium text-gray-500">Key Fields</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {keyFields.map((field) => (
              <span
                key={field.name}
                className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
                title={field.semantic_description || field.name}
              >
                {field.semantic_label || field.name}
              </span>
            ))}
            {entry.fields.length > MAX_DISPLAY_FIELDS && (
              <span className="text-xs text-gray-400">
                +{entry.fields.length - MAX_DISPLAY_FIELDS} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Suggested questions (collapsible) */}
      {entry.suggested_queries.length > 0 && (
        <div className="mt-3 border-t border-gray-100 pt-2">
          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
            aria-expanded={isExpanded}
          >
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
            <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Sample Questions ({entry.suggested_queries.length})</span>
          </button>
          {isExpanded && (
            <ul className="mt-2 space-y-1 pl-5" role="list">
              {entry.suggested_queries.map((question, idx) => (
                <li key={idx} className="text-xs text-gray-600 italic">
                  "{question}"
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

/** Renders a domain group with its heading and entries. */
function DomainGroup({
  domain,
  entries,
}: {
  domain: string;
  entries: CatalogEntry[];
}) {
  return (
    <section aria-labelledby={`domain-${domain}`}>
      <div className="flex items-center gap-2 mb-3">
        <Layers className="h-4 w-4 text-gray-500" aria-hidden="true" />
        <h2 id={`domain-${domain}`} className="text-lg font-semibold text-gray-800">
          {domain}
        </h2>
        <span className="text-sm text-gray-400">
          ({entries.length} {entries.length === 1 ? 'entry' : 'entries'})
        </span>
      </div>
      <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {entries.map((entry) => (
          <CatalogEntryCard key={entry.entry_id} entry={entry} />
        ))}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

/**
 * CatalogPage — Enterprise Data Catalog organized by semantic domain.
 *
 * Shows how the platform understands connected enterprise data, displaying
 * business meaning (domain, descriptions, suggested questions) rather than
 * only raw technical table/column names.
 *
 * Validates: Requirements 17.1, 17.2, 17.3
 */
export function CatalogPage() {
  const { data: entries, isLoading, isError, refetch } = useCatalogEntries();

  if (isLoading) {
    return <LoadingState variant="full-page" message="Loading enterprise catalog..." />;
  }

  if (isError) {
    return (
      <ErrorState
        message="Failed to load the enterprise catalog. Please try again."
        onRetry={() => refetch()}
      />
    );
  }

  if (!entries || entries.length === 0) {
    return (
      <div className="space-y-6">
        <CatalogHeader totalEntries={0} />
        <EmptyState message="No catalog entries discovered yet. Connect a data source and run discovery to populate the catalog." />
      </div>
    );
  }

  const domainGroups = groupByDomain(entries);
  const sortedDomains = Object.keys(domainGroups).sort((a, b) => {
    // "Uncategorized" goes last
    if (a === 'Uncategorized') return 1;
    if (b === 'Uncategorized') return -1;
    return a.localeCompare(b);
  });

  return (
    <div className="space-y-8">
      <CatalogHeader totalEntries={entries.length} />
      {sortedDomains.map((domain) => (
        <DomainGroup key={domain} domain={domain} entries={domainGroups[domain]} />
      ))}
    </div>
  );
}

/** Page header with title, description, and entry count. */
function CatalogHeader({ totalEntries }: { totalEntries: number }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900">Enterprise Data Catalog</h1>
      <p className="mt-1 text-sm text-gray-500">
        Semantic understanding of connected enterprise data, organized by business domain.
        {totalEntries > 0 && (
          <span className="ml-1 font-medium text-gray-700">
            {totalEntries} {totalEntries === 1 ? 'entry' : 'entries'} discovered.
          </span>
        )}
      </p>
    </div>
  );
}
