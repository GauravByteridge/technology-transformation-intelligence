import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { DocumentSearchRequest, DocumentSearchResponse } from '@/types';

/**
 * Mutation hook for performing semantic document search.
 * Sends a search request and returns matching document results.
 */
export function useDocumentSearch() {
  return useMutation<DocumentSearchResponse, Error, DocumentSearchRequest>({
    mutationFn: (request: DocumentSearchRequest) => apiClient.searchDocuments(request),
  });
}
