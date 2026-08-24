import {
  ALLOWED_EXTENSIONS,
  MAX_FILE_SIZE_BYTES,
  type AllowedExtension,
  type FileValidationResult,
} from './types';

/**
 * Validates a file before upload by checking extension and size.
 * Returns a result indicating whether the file is acceptable.
 */
export function validateFile(file: File): FileValidationResult {
  const fileName = file.name;
  const dotIndex = fileName.lastIndexOf('.');
  const extension = dotIndex >= 0 ? fileName.slice(dotIndex + 1).toLowerCase() : '';

  if (!ALLOWED_EXTENSIONS.includes(extension as AllowedExtension)) {
    return {
      valid: false,
      error: `Unsupported file type: ${extension}. Supported types: xlsx, xls, csv, json, pdf, docx, txt`,
    };
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: 'File size exceeds maximum of 50 MB',
    };
  }

  return { valid: true };
}
