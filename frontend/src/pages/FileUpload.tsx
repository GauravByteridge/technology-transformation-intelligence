import { useCallback, useState } from 'react';
import {
  useFileUpload,
  FileDropZone,
  UploadProgress,
  ProcessingResult,
} from '@/features/file-upload';
import { Upload, FileText, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useProjects } from '@/hooks';
import type { FileUploadResponse } from '@/types';

type UploadState = 'idle' | 'uploading' | 'complete' | 'error';

const SUPPORTED_TYPES = ['PDF', 'DOCX', 'XLSX', 'XLS', 'CSV', 'TXT', 'JSON'];

/**
 * File Upload page — enterprise document ingestion with content-aware processing.
 */
export default function FileUpload() {
  const navigate = useNavigate();
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
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Back button */}
      <button
        onClick={() => navigate('/sources')}
        className="flex items-center gap-1 text-sm text-teal-400 hover:text-teal-300 transition-colors"
      >
        <ArrowLeft size={14} />
        Back to Data Sources
      </button>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-white flex items-center gap-2">
          <Upload size={24} className="text-teal-400" />
          Upload Enterprise Information
        </h1>
        <p className="mt-1 text-sm text-gray-400">
          Upload documents and spreadsheets for content-aware processing.
          Files are analyzed, classified, chunked and indexed for AI-powered search.
        </p>
      </div>

      {/* Supported types */}
      <div className="flex items-center gap-2 flex-wrap">
        {SUPPORTED_TYPES.map((type) => (
          <span
            key={type}
            className="px-2 py-0.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-400 font-mono"
          >
            {type}
          </span>
        ))}
      </div>

      {/* Project selector dropdown */}
      <div>
        <label htmlFor="project-select" className="block text-sm font-medium text-gray-300 mb-1">
          Project (optional)
        </label>
        <ProjectDropdown
          value={projectId}
          onChange={setProjectId}
          disabled={uploadState === 'uploading'}
        />
      </div>

      {/* Upload flow states */}
      {uploadState === 'idle' && (
        <FileDropZone onFileSelect={handleFileSelect} />
      )}

      {uploadState === 'uploading' && (
        <div className="space-y-4">
          <UploadProgress fileName={selectedFileName} />
          {/* Processing steps visualization */}
          <ProcessingSteps fileName={selectedFileName} />
        </div>
      )}

      {uploadState === 'complete' && result && (
        <div className="space-y-4">
          <ProcessingResult result={result} />
          <div className="flex items-center gap-3">
            <button
              onClick={handleReset}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-500 transition-colors"
            >
              Upload another file
            </button>
            <button
              onClick={() => navigate('/catalog')}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
            >
              View in Catalog
            </button>
          </div>
        </div>
      )}

      {uploadState === 'error' && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4" role="alert">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-red-400 text-sm font-medium">{errorMessage}</span>
          </div>
          <button
            onClick={handleReset}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-red-600 text-white hover:bg-red-500 transition-colors"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}

/** Dropdown to select a project by name instead of entering UUID */
function ProjectDropdown({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (id: string) => void;
  disabled: boolean;
}) {
  const { data: projects } = useProjects();

  return (
    <select
      id="project-select"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:ring-1 focus:ring-teal-500 disabled:opacity-50"
    >
      <option value="">— No project (general upload) —</option>
      {projects?.items?.map((p) => (
        <option key={p.id} value={p.id}>
          {p.name}
        </option>
      ))}
    </select>
  );
}

/** Simulated processing steps shown during upload */
function ProcessingSteps({ fileName }: { fileName: string }) {
  const isExcel = /\.(xlsx?|csv)$/i.test(fileName);

  const steps = isExcel
    ? [
        { label: '✓ Uploaded', done: true },
        { label: 'Parsing sheets...', active: true },
        { label: 'Detecting structured datasets', pending: true },
        { label: 'Classification', pending: true },
        { label: 'Catalog registration', pending: true },
        { label: 'AI Queryable', pending: true },
      ]
    : [
        { label: '✓ Uploaded', done: true },
        { label: 'Parsing...', active: true },
        { label: 'Content extraction', pending: true },
        { label: 'Classification', pending: true },
        { label: 'Chunking / Dataset extraction', pending: true },
        { label: 'Indexing', pending: true },
        { label: 'Catalog registration', pending: true },
        { label: 'AI Queryable', pending: true },
      ];

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 space-y-2">
      <div className="flex items-center gap-2 mb-3">
        <FileText size={14} className="text-teal-400" />
        <span className="text-sm font-medium text-white">{fileName}</span>
      </div>
      {steps.map((step, idx) => (
        <div
          key={idx}
          className={`flex items-center gap-2 text-xs ${
            step.done
              ? 'text-green-400'
              : step.active
                ? 'text-teal-400'
                : 'text-gray-500'
          }`}
        >
          {step.done && <span>✓</span>}
          {step.active && <span className="animate-spin">⟳</span>}
          {step.pending && <span className="opacity-30">○</span>}
          <span>{step.label}</span>
        </div>
      ))}
    </div>
  );
}
