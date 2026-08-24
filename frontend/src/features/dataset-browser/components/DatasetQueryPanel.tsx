import { useState } from 'react';
import { useDatasetQuery } from '../hooks/useDatasets';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';
import { Button } from '@/components/ui/button';
import type { DatasetQueryRequest } from '@/types';

interface DatasetQueryPanelProps {
  datasetId: string;
}

/**
 * DatasetQueryPanel — Form for querying a dataset with limit, columns, and filters.
 * Displays result rows in a table after submission.
 */
export function DatasetQueryPanel({ datasetId }: DatasetQueryPanelProps) {
  const [limit, setLimit] = useState<number>(50);
  const [columns, setColumns] = useState<string>('');
  const [filtersText, setFiltersText] = useState<string>('');
  const [filtersError, setFiltersError] = useState<string | null>(null);

  const queryMutation = useDatasetQuery();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFiltersError(null);

    let parsedFilters: Record<string, unknown> | undefined;
    if (filtersText.trim()) {
      try {
        parsedFilters = JSON.parse(filtersText) as Record<string, unknown>;
      } catch {
        setFiltersError('Invalid JSON. Please enter valid JSON for filters.');
        return;
      }
    }

    const request: DatasetQueryRequest = {
      limit,
      ...(columns.trim() && {
        columns: columns.split(',').map((c) => c.trim()).filter(Boolean),
      }),
      ...(parsedFilters && { filters: parsedFilters }),
    };

    queryMutation.mutate({ id: datasetId, request });
  };

  const resultRecords = queryMutation.data?.records;
  const resultColumns = resultRecords && resultRecords.length > 0
    ? Object.keys(resultRecords[0] as Record<string, unknown>)
    : [];

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
        <h3 className="text-sm font-medium text-gray-700">Query Dataset</h3>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label htmlFor="query-limit" className="block text-xs font-medium text-gray-600">
              Limit
            </label>
            <input
              id="query-limit"
              type="number"
              min={1}
              max={1000}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="query-columns" className="block text-xs font-medium text-gray-600">
              Columns (comma-separated)
            </label>
            <input
              id="query-columns"
              type="text"
              value={columns}
              onChange={(e) => setColumns(e.target.value)}
              placeholder="e.g. name, amount, date"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="query-filters" className="block text-xs font-medium text-gray-600">
              Filters (JSON)
            </label>
            <input
              id="query-filters"
              type="text"
              value={filtersText}
              onChange={(e) => {
                setFiltersText(e.target.value);
                setFiltersError(null);
              }}
              placeholder='e.g. {"status": "active"}'
              className={`mt-1 block w-full rounded-md border px-3 py-1.5 text-sm shadow-sm focus:outline-none focus:ring-1 ${
                filtersError
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                  : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
              }`}
              aria-invalid={filtersError ? 'true' : undefined}
              aria-describedby={filtersError ? 'filters-error' : undefined}
            />
            {filtersError && (
              <p id="filters-error" className="mt-1 text-xs text-red-600" role="alert">
                {filtersError}
              </p>
            )}
          </div>
        </div>

        <Button
          type="submit"
          disabled={queryMutation.isPending}
          size="sm"
        >
          {queryMutation.isPending ? 'Querying…' : 'Run Query'}
        </Button>
      </form>

      {/* Query Results */}
      {queryMutation.isPending && (
        <LoadingState variant="inline" message="Running query…" />
      )}

      {queryMutation.isError && (
        <ErrorState
          message={queryMutation.error?.message ?? 'Query failed.'}
          onRetry={() => queryMutation.reset()}
        />
      )}

      {queryMutation.isSuccess && resultRecords && resultRecords.length === 0 && (
        <EmptyState message="Query returned no results." />
      )}

      {queryMutation.isSuccess && resultRecords && resultRecords.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-700">Results</h4>
            <span className="text-xs text-gray-500">
              {resultRecords.length} of {queryMutation.data.total_count.toLocaleString()} records
            </span>
          </div>

          <div className="max-h-96 overflow-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="sticky top-0 bg-gray-50">
                <tr>
                  {resultColumns.map((col) => (
                    <th
                      key={col}
                      scope="col"
                      className="whitespace-nowrap px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {resultRecords.map((row, rowIndex) => (
                  <tr key={rowIndex} className="hover:bg-gray-50">
                    {resultColumns.map((col) => {
                      const value = (row as Record<string, unknown>)[col];
                      return (
                        <td
                          key={col}
                          className="whitespace-nowrap px-4 py-2 text-sm text-gray-700"
                        >
                          {value == null ? <span className="text-gray-400">—</span> : String(value)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
