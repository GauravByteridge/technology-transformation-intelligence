import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { ExecutiveBrief } from '../types';

export function useGenerateBrief() {
  return useMutation<ExecutiveBrief, Error, string>({
    mutationFn: (projectId) => apiClient.generateBrief(projectId),
  });
}

export function useExportBriefPDF() {
  return useMutation<Blob, Error, string>({
    mutationFn: (projectId) => apiClient.exportBriefPDF(projectId),
  });
}
