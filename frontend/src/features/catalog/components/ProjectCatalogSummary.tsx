import { Database, FileText, Layers } from 'lucide-react';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { useCatalogForProject } from '../hooks/useCatalogForProject';
import type { CatalogEntry } from '../types';

interface ProjectCatalogSummaryProps {
  projectId: string;
}

/** Grouping of catalog entries by source type for display. */
interface SourceGroup {
  sourceType: CatalogEntry['source_type'];
  label: string;
  objectCount: number;
  entries: CatalogEntry[];
}

/** Icon and label configuration per source type. */
const SOURCE_TYPE_CONFIG: Record<
  CatalogEntry['source_type'],
  { icon: typeof Database; label: string; objectLabel: string; badgeColor: string }
> = {
  postgresql: {
    icon: Database,
    label: 'PostgreSQL',
    objectLabel: 'tables',
    badgeColor: 'bg-blue-100 text-blue-800',
  },
  mongodb: {
    icon: Layers,
    label: 'MongoDB',
    objectLabel: 'collections',
    badgeColor: 'bg-green-100 text-green-800',
  },
  document: {
    icon: FileText,
    label: 'Documents',
    objectLabel: 'documents',
    badgeColor: 'bg-amber-100 text-amber-800',
  },
};

/**
 * ProjectCatalogSummary — compact view of catalog sources connected
 * to a specific project. Designed to be rendered inside the Project 360 page.
 *
 * Shows: "Connected Sources: PostgreSQL (3 tables) · MongoDB (2 collections) · Documents (5)"
 * Each source entry shows semantic_name, domain tags, and object count.
 *
 * Validates: Requirements 17.4
 */
export function ProjectCatalogSummary({ projectId }: ProjectCatalogSummaryProps) {
  const { data: entries, isLoading, isError, error, refetch } = useCatalogForProject(projectId);

  if (isLoading) {
    return <LoadingState variant="inline" message="Loading catalog sources…" />;
  }

  if (isError) {
    return (
      <ErrorState
        message={error?.message ?? 'Failed to load catalog sources.'}
        onRetry={() => refetch()}
      />
    );
  }

  if (!entries || entries.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
        <p className="text-sm text-gray-500">No connected sources for this project.</p>
      </div>
    );
  }

  const groups = groupEntriesBySourceType(entries);

  return (
    <div className="rounded-lg border border-gray-200 bg-white" aria-label="Project catalog summary">
      {/* Compact summary line */}
      <div className="px-4 py-3 border-b border-gray-100">
        <p className="text-sm text-gray-700">
          <span className="font-semibold text-gray-800">Connected Sources: </span>
          {groups.map((group, index) => (
            <span key={group.sourceType}>
              {index > 0 && <span className="mx-1 text-gray-400">·</span>}
              <span>{group.label} ({group.objectCount})</span>
            </span>
          ))}
        </p>
      </div>

      {/* Per-entry details */}
      <ul className="divide-y divide-gray-100 px-4" role="list" aria-label="Catalog entries for project">
        {entries.map((entry) => (
          <CatalogEntryRow key={entry.entry_id} entry={entry} />
        ))}
      </ul>
    </div>
  );
}

/** Renders a single catalog entry row with semantic_name, domain tags, and object count. */
function CatalogEntryRow({ entry }: { entry: CatalogEntry }) {
  const config = SOURCE_TYPE_CONFIG[entry.source_type] ?? SOURCE_TYPE_CONFIG.document;
  const IconComponent = config.icon;
  const fieldCount = entry.fields?.length ?? 0;

  return (
    <li className="flex items-center gap-3 py-2.5">
      <IconComponent className="h-4 w-4 text-gray-400 flex-shrink-0" aria-hidden="true" />

      {/* Name and description */}
      <div className="flex flex-col min-w-0 flex-1">
        <span className="text-sm font-medium text-gray-800 truncate">
          {entry.semantic_name || entry.object_name}
        </span>
        {entry.object_name && entry.semantic_name && (
          <span className="text-xs text-gray-500 truncate">{entry.object_name}</span>
        )}
      </div>

      {/* Domain tags */}
      {entry.domain_tags.length > 0 && (
        <div className="flex items-center gap-1 flex-shrink-0">
          {entry.domain_tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Field/object count */}
      <span className="text-xs text-gray-400 flex-shrink-0">
        {fieldCount} field{fieldCount !== 1 ? 's' : ''}
      </span>
    </li>
  );
}

/** Groups catalog entries by source_type and computes per-group object count. */
function groupEntriesBySourceType(entries: CatalogEntry[]): SourceGroup[] {
  const groupMap = new Map<CatalogEntry['source_type'], CatalogEntry[]>();

  for (const entry of entries) {
    const existing = groupMap.get(entry.source_type) ?? [];
    existing.push(entry);
    groupMap.set(entry.source_type, existing);
  }

  const groups: SourceGroup[] = [];
  for (const [sourceType, groupEntries] of groupMap) {
    const config = SOURCE_TYPE_CONFIG[sourceType];
    groups.push({
      sourceType,
      label: config?.label ?? sourceType,
      objectCount: groupEntries.length,
      entries: groupEntries,
    });
  }

  return groups;
}
