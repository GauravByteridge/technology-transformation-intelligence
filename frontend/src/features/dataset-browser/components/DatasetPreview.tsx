import { useDatasetPreview } from '../hooks/useDatasets';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';

interface DatasetPreviewProps {
  datasetId: string;
}

/**
 * DatasetPreview — Shows column headers and sample rows for a dataset
 * in a horizontally-scrollable table.
 */
export function DatasetPreview({ datasetId }: DatasetPreviewProps) {
  const { data: preview, isLoading, isError, error, refetch } = useDatasetPreview(datasetId);

  if (isLoading) {
    return <LoadingState variant="skeleton" message="Loading preview…" />;
  }

  if (isError) {
    return (
      <ErrorState
        message={error?.message ?? 'Failed to load dataset preview.'}
        onRetry={() => void refetch()}
      />
    );
  }

  if (!preview || preview.records.length === 0) {
    return <EmptyState message="No preview data available for this dataset." />;
  }

  // Extract column names from the columns metadata
  const columnNames = preview.columns.map((col) => {
    const name = (col as Record<string, unknown>).name;
    return typeof name === 'string' ? name : String(name ?? 'unknown');
  });

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700">
          Preview — {preview.dataset.name}
        </h3>
        <span className="text-xs text-gray-500">
          Showing {preview.records.length} of {preview.total_count.toLocaleString()} records
        </span>
      </div>

      <div className="max-h-96 overflow-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="sticky top-0 bg-gray-50">
            <tr>
              {columnNames.map((colName) => (
                <th
                  key={colName}
                  scope="col"
                  className="whitespace-nowrap px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                >
                  {colName}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {preview.records.map((row, rowIndex) => (
              <tr key={rowIndex} className="hover:bg-gray-50">
                {columnNames.map((colName) => {
                  const value = (row as Record<string, unknown>)[colName];
                  return (
                    <td
                      key={colName}
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
  );
}
