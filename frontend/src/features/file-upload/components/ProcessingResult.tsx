import type { FileUploadResponse } from '@/types';

interface ProcessingResultProps {
  result: FileUploadResponse;
}

/**
 * Displays file upload processing results including datasets created
 * and documents indexed. One file may produce multiple content types.
 */
export function ProcessingResult({ result }: ProcessingResultProps) {
  const datasetNames = result.datasets_created.map(
    (ds) => (ds as Record<string, unknown>).name ?? 'Unnamed dataset',
  );

  return (
    <div
      className="rounded-lg border border-green-200 bg-green-50 p-4"
      role="status"
      aria-live="polite"
      aria-label="File processing result"
    >
      {/* Header */}
      <div className="mb-3 flex items-center gap-2">
        <svg
          className="h-5 w-5 text-green-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <h3 className="text-sm font-semibold text-green-800">File processed</h3>
      </div>

      {/* File metadata */}
      <dl className="space-y-2 text-sm">
        <div className="flex items-baseline gap-2">
          <dt className="font-medium text-gray-700">File:</dt>
          <dd className="text-gray-900">{result.file_name}</dd>
        </div>

        <div className="flex items-baseline gap-2">
          <dt className="font-medium text-gray-700">Content detected:</dt>
          <dd className="text-gray-900">{result.file_type}</dd>
        </div>

        <div className="flex items-baseline gap-2">
          <dt className="font-medium text-gray-700">Status:</dt>
          <dd>
            <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
              {result.processing_status}
            </span>
          </dd>
        </div>

        <div className="flex items-baseline gap-2">
          <dt className="font-medium text-gray-700">Datasets created:</dt>
          <dd className="text-gray-900">{result.datasets_created.length}</dd>
        </div>

        {datasetNames.length > 0 && (
          <div className="ml-4">
            <ul className="list-disc space-y-0.5 pl-4 text-xs text-gray-700">
              {datasetNames.map((name, index) => (
                <li key={index}>{String(name)}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex items-baseline gap-2">
          <dt className="font-medium text-gray-700">Documents indexed:</dt>
          <dd className="text-gray-900">{result.documents_indexed}</dd>
        </div>
      </dl>

      {/* Informational note about multi-content files */}
      {result.datasets_created.length > 0 && result.documents_indexed > 0 && (
        <p className="mt-3 text-xs text-gray-600">
          This file produced both structured datasets and indexed documents for search.
        </p>
      )}
    </div>
  );
}
