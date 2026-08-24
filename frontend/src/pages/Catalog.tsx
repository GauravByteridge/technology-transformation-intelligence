import { useState, useMemo } from 'react';
import { Search, Filter, Database, FileText, Layers, Tag, ChevronDown, ChevronRight, MessageSquare } from 'lucide-react';
import { LoadingState, ErrorState, EmptyState } from '@/components/common';
import { useCatalogEntries } from '@/features/catalog/hooks/useCatalog';
import type { CatalogEntry, CatalogField } from '@/features/catalog/types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_DISPLAY_FIELDS = 6;

const SOURCE_TYPE_CONFIG: Record<string, { icon: typeof Database; label: string; badgeColor: string }> = {
  postgresql: { icon: Database, label: 'PostgreSQL', badgeColor: 'bg-blue-500/20 text-blue-300' },
  mongodb: { icon: Database, label: 'MongoDB', badgeColor: 'bg-green-500/20 text-green-300' },
  document: { icon: FileText, label: 'Document', badgeColor: 'bg-amber-500/20 text-amber-300' },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function groupByDomain(entries: CatalogEntry[]): Record<string, CatalogEntry[]> {
  const groups: Record<string, CatalogEntry[]> = {};
  for (const entry of entries) {
    const tags = entry.domain_tags.length > 0 ? entry.domain_tags : ['Uncategorized'];
    for (const tag of tags) {
      const key = tag.charAt(0).toUpperCase() + tag.slice(1).toLowerCase();
      if (!groups[key]) groups[key] = [];
      groups[key].push(entry);
    }
  }
  return groups;
}

function getDisplayName(entry: CatalogEntry): string {
  return entry.semantic_name || entry.object_name;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CatalogEntryCard({ entry }: { entry: CatalogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const config = SOURCE_TYPE_CONFIG[entry.source_type] ?? SOURCE_TYPE_CONFIG.document;
  const IconComponent = config.icon;
  const keyFields = entry.fields.slice(0, MAX_DISPLAY_FIELDS);

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 hover:border-teal-500/30 transition-colors">
      {/* Header */}
      <div className="flex items-start gap-3">
        <IconComponent className="h-5 w-5 text-gray-400 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-white truncate">
              {getDisplayName(entry)}
            </h3>
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${config.badgeColor}`}>
              {config.label}
            </span>
          </div>
          {entry.semantic_description && (
            <p className="mt-1 text-xs text-gray-400 line-clamp-2">{entry.semantic_description}</p>
          )}
        </div>
      </div>

      {/* Domain */}
      {entry.domain_tags.length > 0 && (
        <div className="mt-2 flex items-center gap-1">
          <span className="text-xs text-gray-500">Domain:</span>
          <span className="text-xs text-gray-300">{entry.domain_tags.join(', ')}</span>
        </div>
      )}

      {/* Fields */}
      {keyFields.length > 0 && (
        <div className="mt-3">
          <div className="flex items-center gap-1 mb-1.5">
            <Tag className="h-3 w-3 text-gray-500" />
            <span className="text-xs font-medium text-gray-500">Fields</span>
          </div>
          <div className="space-y-0.5">
            {keyFields.map((field: CatalogField) => (
              <div key={field.name} className="flex items-center gap-2 text-xs">
                <span className="text-gray-400 font-mono">{field.name}</span>
                {field.semantic_label && (
                  <span className="text-gray-500">{field.semantic_label}</span>
                )}
              </div>
            ))}
            {entry.fields.length > MAX_DISPLAY_FIELDS && (
              <span className="text-xs text-gray-500">
                +{entry.fields.length - MAX_DISPLAY_FIELDS} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Projects count */}
      {entry.project_fields.length > 0 && (
        <div className="mt-2 text-xs text-gray-500">
          Projects: <span className="text-gray-300">{entry.project_fields.length}</span>
        </div>
      )}

      {/* Suggested Questions */}
      {entry.suggested_queries.length > 0 && (
        <div className="mt-3 border-t border-gray-700/50 pt-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            <MessageSquare size={12} />
            Sample Questions ({entry.suggested_queries.length})
          </button>
          {expanded && (
            <ul className="mt-2 space-y-1 pl-4">
              {entry.suggested_queries.map((q, idx) => (
                <li key={idx} className="text-xs text-gray-400 italic">"{q}"</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* View Details */}
      <div className="mt-3 pt-2 border-t border-gray-700/50">
        <button className="text-xs text-teal-400 hover:text-teal-300 font-medium transition-colors">
          View Details →
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function Catalog() {
  const { data: entries, isLoading, isError, refetch } = useCatalogEntries();
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [domainFilter, setDomainFilter] = useState<string>('all');

  // Filter entries
  const filteredEntries = useMemo(() => {
    if (!entries) return [];
    let result = entries;

    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (e) =>
          getDisplayName(e).toLowerCase().includes(q) ||
          (e.semantic_description || '').toLowerCase().includes(q) ||
          e.fields.some((f) => f.name.toLowerCase().includes(q) || (f.semantic_label || '').toLowerCase().includes(q)),
      );
    }

    // Source type filter
    if (sourceFilter !== 'all') {
      result = result.filter((e) => e.source_type === sourceFilter);
    }

    // Domain filter
    if (domainFilter !== 'all') {
      result = result.filter((e) => e.domain_tags.some((t) => t.toLowerCase() === domainFilter.toLowerCase()));
    }

    return result;
  }, [entries, searchQuery, sourceFilter, domainFilter]);

  // Get unique domains for filter
  const allDomains = useMemo(() => {
    if (!entries) return [];
    const domains = new Set<string>();
    entries.forEach((e) => e.domain_tags.forEach((t) => domains.add(t)));
    return Array.from(domains).sort();
  }, [entries]);

  const domainGroups = groupByDomain(filteredEntries);
  const sortedDomains = Object.keys(domainGroups).sort((a, b) => {
    if (a === 'Uncategorized') return 1;
    if (b === 'Uncategorized') return -1;
    return a.localeCompare(b);
  });

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-white">Data Catalog</h1>
        <p className="text-sm text-gray-400 mt-1">
          Search datasets, fields, domains and business concepts.
          {entries && entries.length > 0 && (
            <span className="ml-1 text-gray-300 font-medium">
              {entries.length} entries discovered.
            </span>
          )}
        </p>
      </div>

      {/* Search */}
      <div className="relative max-w-lg">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          type="text"
          placeholder="Search: finance, project risk, actual cost..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500 focus:border-teal-500"
        />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <Filter size={14} className="text-gray-500" />
          <span className="text-xs text-gray-500">Filters:</span>
        </div>
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-md text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-teal-500"
        >
          <option value="all">All Sources</option>
          <option value="postgresql">PostgreSQL</option>
          <option value="mongodb">MongoDB</option>
          <option value="document">Documents</option>
        </select>
        <select
          value={domainFilter}
          onChange={(e) => setDomainFilter(e.target.value)}
          className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-md text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-teal-500"
        >
          <option value="all">All Domains</option>
          {allDomains.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>

      {/* Catalog entries grouped by domain */}
      {!entries || entries.length === 0 ? (
        <EmptyState message="No catalog entries discovered yet. Connect a data source and run discovery to populate the catalog." />
      ) : filteredEntries.length === 0 ? (
        <EmptyState message="No entries match your search criteria." />
      ) : (
        <div className="space-y-8">
          {sortedDomains.map((domain) => (
            <section key={domain}>
              <div className="flex items-center gap-2 mb-3">
                <Layers size={16} className="text-teal-400" />
                <h2 className="text-lg font-semibold text-white">{domain}</h2>
                <span className="text-sm text-gray-500">
                  ({domainGroups[domain].length})
                </span>
              </div>
              <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                {domainGroups[domain].map((entry) => (
                  <CatalogEntryCard key={entry.entry_id} entry={entry} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
