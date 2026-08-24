import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { validateFile } from '../validation';
import type { FileUploadResponse } from '@/types';

interface UploadFileParams {
  file: File;
  projectId?: string;
}

/**
 * Mutation hook for uploading files with client-side validation.
 * Validates the file (extension + size) before sending to the backend.
 */
export function useFileUpload() {
  return useMutation<FileUploadResponse, Error, UploadFileParams>({
    mutationFn: async ({ file, projectId }: UploadFileParams) => {
      const validation = validateFile(file);
      if (!validation.valid) {
        throw new Error(validation.error);
      }

      return apiClient.uploadFile(file, projectId);
    },
  });
}
