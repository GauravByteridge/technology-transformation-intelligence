import { useCallback, useState } from 'react';
import {
  useFileUpload,
  FileDropZone,
  UploadProgress,
  ProcessingResult,
} from '@/features/file-upload';
import type { FileUploadResponse } from '@/types';

type UploadState = 'idle' | 'uploading' | 'complete' | 'error';

/**
 * File Upload page — orchestrates the upload flow through a simple state machine:
 * idle → uploading → complete/error.
 */
export default function FileUpload() {
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [selectedFileName, setSelectedFileName] = useState<string>('');
  const [result, setResult] = useState<FileUploadResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [projectId, setProjectId] = useState<string>('');

  const uploadMutation = useFileUpload();

  const handleFileSelect = useCallback(
    (file: File) => {
      setSelectedFileName(file.name);
      setUploadState('uploading');
      setErrorMessage('');
      setResult(null);

      uploadMutation.mutate(
        { file, projectId: projectId || undefined },
        {
          onSuccess: (data) => {
            setResult(data);
            setUploadState('complete');
          },
          onError: (error) => {
            setErrorMessage(error.message || 'Upload failed. Please try again.');
            setUploadState('error');
          },
        },
      );
    },
    [uploadMutation, projectId],
  );

  const handleReset = useCallback(() => {
    setUploadState('idle');
    setSelectedFileName('');
    setResult(null);
    setErrorMessage('');
  }, []);

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      {/* Header */}
      <header>
        <h1 className="text-2xl font-bold text-gray-900">Upload Files</h1>
        <p className="mt-1 text-sm text-gray-600">
          Upload documents and spreadsheets for content-aware processing.
          Files are analyzed to extract structured datasets and index documents for AI-powered search.
        </p>
      </header>

      {/* Optional project ID input */}
      <div>
        <label htmlFor="project-id-input" className="block text-sm font-medium text-gray-700">
          Project ID (optional)
        </label>
        <input
          id="project-id-input"
          type="text"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          placeholder="Enter project UUID to associate file"
          disabled={uploadState === 'uploading'}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-500"
        />
      </div>

      {/* Upload flow states */}
      {uploadState === 'idle' && (
        <FileDropZone onFileSelect={handleFileSelect} />
      )}

      {uploadState === 'uploading' && (
        <UploadProgress fileName={selectedFileName} />
      )}

      {uploadState === 'complete' && result && (
        <div className="space-y-4">
          <ProcessingResult result={result} />
          <button
            onClick={handleReset}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Upload another file
          </button>
        </div>
      )}

      {uploadState === 'error' && (
        <div
          className="rounded-lg border border-red-200 bg-red-50 p-4"
          role="alert"
          aria-live="assertive"
        >
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm font-medium text-red-800">{errorMessage}</p>
          </div>
          <button
            onClick={handleReset}
            className="mt-3 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
