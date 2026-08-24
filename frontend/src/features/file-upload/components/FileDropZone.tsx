import { useCallback, useRef, useState } from 'react';
import type { DragEvent, ChangeEvent } from 'react';
import { ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES } from '../types';

interface FileDropZoneProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

const MAX_SIZE_MB = MAX_FILE_SIZE_BYTES / (1024 * 1024);
const ACCEPTED_TYPES_DISPLAY = ALLOWED_EXTENSIONS.join(', ');
const ACCEPT_ATTRIBUTE = ALLOWED_EXTENSIONS.map((ext) => `.${ext}`).join(',');

/**
 * Drag-and-drop file selection zone with click-to-browse support.
 * Shows accepted file types and maximum file size.
 */
export function FileDropZone({ onFileSelect, disabled = false }: FileDropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) {
        setIsDragOver(true);
      }
    },
    [disabled],
  );

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      if (disabled) return;

      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) {
        onFileSelect(droppedFile);
      }
    },
    [disabled, onFileSelect],
  );

  const handleInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) {
        onFileSelect(selectedFile);
      }
      // Reset input so the same file can be re-selected
      e.target.value = '';
    },
    [onFileSelect],
  );

  const handleClick = useCallback(() => {
    if (!disabled) {
      inputRef.current?.click();
    }
  }, [disabled]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        inputRef.current?.click();
      }
    },
    [disabled],
  );

  const borderStyles = isDragOver
    ? 'border-blue-500 bg-blue-50'
    : disabled
      ? 'border-gray-200 bg-gray-50'
      : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50';

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label="File upload drop zone. Click or drag and drop a file to upload."
      aria-disabled={disabled}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${borderStyles} ${disabled ? 'cursor-not-allowed opacity-60' : ''}`}
    >
      {/* Upload icon */}
      <svg
        className={`mb-3 h-10 w-10 ${isDragOver ? 'text-blue-500' : 'text-gray-400'}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
        />
      </svg>

      <p className="mb-1 text-sm font-medium text-gray-700">
        {isDragOver ? 'Drop file here' : 'Drag and drop a file, or click to browse'}
      </p>

      <p className="text-xs text-gray-500">
        Supported: {ACCEPTED_TYPES_DISPLAY}
      </p>
      <p className="text-xs text-gray-500">
        Max size: {MAX_SIZE_MB} MB
      </p>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT_ATTRIBUTE}
        onChange={handleInputChange}
        disabled={disabled}
        className="hidden"
        aria-hidden="true"
        tabIndex={-1}
      />
    </div>
  );
}
