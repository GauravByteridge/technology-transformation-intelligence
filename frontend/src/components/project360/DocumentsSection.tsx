import { useState } from 'react';
import { Search } from 'lucide-react';
import { useProjectDocuments, useDocumentSearch } from '@/hooks';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';
import type { DocumentResponse } from '@/types';

interface DocumentsSectionProps {
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

/** Format file size in bytes to a human-readable string */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, exponent);
  return `${value.toFixed(exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

const PROCESSING_STATUS_COLORS: Record<string, string> = {
  completed: 'bg-green-100 text-green-800',
  processing: 'bg-blue-100 text-blue-800',
  pending: 'bg-yellow-100 text-yellow-800',
  failed: 'bg-red-100 text-red-800',
};

function ProcessingStatusBadge({ status }: { status: string }) {
  const colorClass = PROCESSING_STATUS_COLORS[status.toLowerCase()] ?? 'bg-gray-100 text-gray-800';
  const label = status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  );
}

/** Renders the document list table */
function DocumentsTable({ documents }: { documents: DocumentResponse[] }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-700">
          Project Documents ({documents.length})
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">File Name</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Size</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {documents.map((doc) => (
              <tr key={doc.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-sm text-gray-900">{doc.file_name}</td>
                <td className="px-4 py-2 text-sm text-gray-700">{doc.file_type}</td>
                <td className="px-4 py-2 text-sm text-gray-700">{formatFileSize(doc.file_size)}</td>
                <td className="px-4 py-2 text-sm">
                  <ProcessingStatusBadge status={doc.processing_status} />
                </td>
                <td className="px-4 py-2 text-sm text-gray-700">{formatDate(doc.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Renders search results from semantic document search */
function SearchResults({ results }: { results: Record<string, unknown>[] }) {
  if (results.length === 0) {
    return <EmptyState message="No matching documents found for your query." />;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-700">
          Search Results ({results.length})
        </h3>
      </div>
      <div className="divide-y divide-gray-200">
        {results.map((result, index) => {
          const fileName = result.file_name as string | undefined;
          const fileType = result.file_type as string | undefined;
          const relevanceScore = result.relevance_score as number | undefined;
          const textExcerpt = result.text_excerpt as string | undefined;
          const sheetName = result.sheet_name as string | undefined;
          const region = result.region as string | undefined;

          return (
            <div key={index} className="px-4 py-3 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900">
                    {fileName ?? 'Unknown file'}
                  </span>
                  {fileType && (
                    <span className="inline-flex items-center rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                      {fileType}
                    </span>
                  )}
                  {/* Show sheet_name and region for Excel-derived content */}
                  {sheetName && (
                    <span className="inline-flex items-center rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700">
                      Sheet: {sheetName}
                    </span>
                  )}
                  {region && (
                    <span className="inline-flex items-center rounded bg-purple-50 px-1.5 py-0.5 text-xs text-purple-700">
                      Region: {region}
                    </span>
                  )}
                </div>
                {relevanceScore != null && (
                  <span className="text-xs text-gray-500">
                    Relevance: {(relevanceScore * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              {textExcerpt && (
                <p className="mt-1 text-sm text-gray-600 line-clamp-3">{textExcerpt}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function DocumentsSection({ projectId }: DocumentsSectionProps) {
  const [searchText, setSearchText] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  const { data: documents, isLoading, isError, refetch } = useProjectDocuments(projectId);
  const { mutate: searchDocuments, data: searchData, isPending: isSearching, isError: isSearchError, reset: resetSearch } = useDocumentSearch();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchText.trim();
    if (!query) return;

    setHasSearched(true);
    searchDocuments({ project_id: projectId, query });
  };

  const handleClearSearch = () => {
    setSearchText('');
    setHasSearched(false);
    resetSearch();
  };

  return (
    <div className="space-y-6">
      {/* Semantic Search */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Semantic Document Search</h3>
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" aria-hidden="true" />
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search documents using natural language..."
              className="w-full rounded-md border border-gray-300 py-2 pl-9 pr-3 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              aria-label="Semantic document search"
            />
          </div>
          <button
            type="submit"
            disabled={isSearching || !searchText.trim()}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSearching ? 'Searching...' : 'Search'}
          </button>
          {hasSearched && (
            <button
              type="button"
              onClick={handleClearSearch}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Clear
            </button>
          )}
        </form>

        {/* Search results */}
        {isSearching && (
          <div className="mt-4">
            <LoadingState variant="inline" message="Searching documents..." />
          </div>
        )}

        {isSearchError && (
          <div className="mt-4">
            <ErrorState message="Document search failed. Please try again." onRetry={() => {
              if (searchText.trim()) {
                searchDocuments({ project_id: projectId, query: searchText.trim() });
              }
            }} />
          </div>
        )}

        {!isSearching && !isSearchError && hasSearched && searchData && (
          <div className="mt-4">
            <SearchResults results={searchData.results} />
          </div>
        )}
      </div>

      {/* Document list */}
      {isLoading && <LoadingState variant="skeleton" message="Loading documents..." />}

      {isError && (
        <ErrorState
          message="Failed to load documents. Please try again."
          onRetry={() => void refetch()}
        />
      )}

      {!isLoading && !isError && (!documents || documents.length === 0) && (
        <EmptyState message="No documents have been uploaded for this project." />
      )}

      {!isLoading && !isError && documents && documents.length > 0 && (
        <DocumentsTable documents={documents} />
      )}
    </div>
  );
}
