import { useState } from 'react';
import {
  DatasetList,
  DatasetPreview,
  DatasetConfirmButton,
  DatasetQueryPanel,
  useDatasets,
} from '@/features/dataset-browser';

/**
 * DatasetBrowser — Page for browsing, previewing, confirming, and querying datasets.
 * Datasets are created when the backend detects structured content in uploaded files.
 */
export default function DatasetBrowser() {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const { data: datasets } = useDatasets();

  // Derive the selected dataset's status to determine whether confirm button is shown
  const selectedDataset = datasets?.find((d) => d.id === selectedDatasetId);
  const selectedStatus = selectedDataset?.status ?? null;

  const handleSelectDataset = (id: string) => {
    setSelectedDatasetId(id);
  };

  const handleConfirmed = () => {
    // Status will auto-update via query invalidation in DatasetConfirmButton
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dataset Browser</h1>
        <p className="mt-1 text-sm text-gray-600">
          Browse and query structured datasets detected from uploaded files.
        </p>
      </div>

      {/* Dataset List — full width */}
      <DatasetList onSelectDataset={handleSelectDataset} />

      {/* Selected Dataset Details */}
      {selectedDatasetId && (
        <div className="space-y-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              {selectedDataset?.name ?? 'Dataset Details'}
            </h2>
            {selectedStatus === 'REVIEW_REQUIRED' && (
              <DatasetConfirmButton
                datasetId={selectedDatasetId}
                status={selectedStatus}
                onConfirmed={handleConfirmed}
              />
            )}
          </div>

          {/* Preview: sample rows */}
          <DatasetPreview datasetId={selectedDatasetId} />

          {/* Query Panel */}
          <DatasetQueryPanel datasetId={selectedDatasetId} />
        </div>
      )}
    </div>
  );
}
