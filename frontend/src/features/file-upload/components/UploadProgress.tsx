interface UploadProgressProps {
  fileName: string;
}

/**
 * Indeterminate progress indicator shown while a file is being uploaded/processed.
 */
export function UploadProgress({ fileName }: UploadProgressProps) {
  return (
    <div
      className="rounded-lg border border-gray-200 bg-white p-4"
      role="status"
      aria-live="polite"
      aria-label={`Processing file ${fileName}`}
    >
      <div className="flex items-center gap-3">
        {/* Spinner */}
        <svg
          className="h-5 w-5 animate-spin text-blue-600"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-gray-900">
            {fileName}
          </p>
          <p className="text-xs text-gray-500">Processing...</p>
        </div>
      </div>

      {/* Indeterminate progress bar */}
      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
        <div className="h-full w-1/3 animate-[indeterminate_1.5s_ease-in-out_infinite] rounded-full bg-blue-600" />
      </div>
    </div>
  );
}
