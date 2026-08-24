import { useState } from 'react';
import {
  DatasetList,
  DatasetPreview,
  DatasetConfirmButton,
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
        <h1 className="text-2xl font-semibold text-white">Dataset Browser</h1>
        <p className="mt-1 text-sm text-gray-400">
          Browse and query structured datasets detected from uploaded files.
        </p>
      </div>

      {/* Dataset List — full width */}
      <DatasetList onSelectDataset={handleSelectDataset} />

      {/* Selected Dataset Details */}
      {selectedDatasetId && (
        <div className="space-y-6 rounded-lg border border-gray-700/50 bg-gray-800/50 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">
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

          {/* Format-specific content */}
          {selectedDataset?.source_type === 'txt' || selectedDataset?.source_type === 'pdf' || selectedDataset?.source_type === 'docx' ? (
            <div className="bg-gray-900/50 rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">📄 Document file — indexed for AI search</span>
              </div>
              <p className="text-xs text-gray-500">
                This file has been chunked and indexed for semantic search. Ask questions about its content using the AI Query page.
              </p>
              <div className="flex items-center gap-4 text-xs text-gray-400">
                <span>Type: {selectedDataset.source_type.toUpperCase()}</span>
                <span>Classification: {selectedDataset.classification}</span>
                <span>Chunks: {selectedDataset.record_count}</span>
              </div>
            </div>
          ) : (
            <>
              {/* Preview: sample rows (structured data only) */}
              <DatasetPreview datasetId={selectedDatasetId} />
            </>
          )}
        </div>
      )}
    </div>
  );
}
