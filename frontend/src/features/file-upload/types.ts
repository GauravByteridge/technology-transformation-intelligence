// File upload constants and types for client-side validation

export const ALLOWED_EXTENSIONS = [
  'xlsx',
  'xls',
  'csv',
  'json',
  'pdf',
  'docx',
  'txt',
] as const;

/** 50 MB in bytes */
export const MAX_FILE_SIZE_BYTES = 52_428_800;

export type AllowedExtension = (typeof ALLOWED_EXTENSIONS)[number];

export interface FileValidationResult {
  valid: boolean;
  error?: string;
}
