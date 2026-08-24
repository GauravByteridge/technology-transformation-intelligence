import { useMutation } from '@tanstack/react-query';
import type { ExecutiveBrief } from '../types';

/**
 * Stub hooks for Executive Brief generation.
 * The backend endpoint POST /api/v1/briefs/generate does NOT exist yet.
 * These hooks throw an explicit error until the backend support is added.
 */

export function useGenerateBrief() {
  return useMutation<ExecutiveBrief, Error, string>({
    mutationFn: () => {
      throw new Error('Brief generation is not yet supported — backend endpoint does not exist.');
    },
  });
}

export function useExportBriefPDF() {
  return useMutation<Blob, Error, string>({
    mutationFn: () => {
      throw new Error('PDF export is not yet supported — backend endpoint does not exist.');
    },
  });
}
