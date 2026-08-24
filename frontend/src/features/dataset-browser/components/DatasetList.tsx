import { useDatasets } from '../hooks/useDatasets';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';

interface DatasetListProps {
  onSelectDataset: (id: string) => void;
}

const STATUS_BADGE_STYLES: Record<string, string> = {
  READY: 'bg-green-100 text-green-800 border-green-200',
  REVIEW_REQUIRED: 'bg-yellow-100 text-yellow-800 border-yellow-200',
};

/**
 * DatasetList — Table listing all datasets detected from uploaded files.
 * Only backend-detected structured content appears here.
 */
export function DatasetList({ onSelectDataset }: DatasetListProps) {
  const { data: datasets, isLoading, isError, error, refetch } = useDatasets();

  if (isLoading) {
    return <LoadingState variant="skeleton" message="Loading datasets…" />;
  }

  if (isError) {
    return (
      <ErrorState
        message={error?.message ?? 'Failed to load datasets.'}
        onRetry={() => void refetch()}
      />
    );
  }

  if (!datasets || datasets.length === 0) {
    return (
      <EmptyState message="No datasets available. Datasets are created when structured content is detected in uploaded files." />
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Name
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Source Type
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Sheet
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Classification
            </th>
            <th scope="col" className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
              Records
            </th>
            <th scope="col" className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
              Confidence
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Status
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {datasets.map((dataset) => (
            <tr
              key={dataset.id}
              onClick={() => onSelectDataset(dataset.id)}
              className="cursor-pointer transition-colors hover:bg-blue-50 focus-within:bg-blue-50"
              role="button"
              tabIndex={0}
              aria-label={`Select dataset ${dataset.name}`}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectDataset(dataset.id);
                }
              }}
            >
              <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                {dataset.name}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                {dataset.source_type}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                {dataset.sheet_name ?? '—'}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                {dataset.classification}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-600">
                {dataset.record_count.toLocaleString()}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-600">
                {(dataset.confidence * 100).toFixed(0)}%
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-sm">
                <span
                  className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                    STATUS_BADGE_STYLES[dataset.status] ?? 'bg-gray-100 text-gray-700 border-gray-200'
                  }`}
                  role="status"
                  aria-label={`Status: ${dataset.status}`}
                >
                  {dataset.status === 'REVIEW_REQUIRED' ? 'Review Required' : dataset.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
