import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { AIQueryRequest, AIResponse } from '@/types';

/**
 * Mutation hook for submitting AI queries.
 * Provides mutate/mutateAsync, data (AIResponse), isPending, isError, and error.
 */
export function useAIQuery() {
  return useMutation<AIResponse, Error, AIQueryRequest>({
    mutationFn: (request) => apiClient.submitAIQuery(request),
  });
}

/** @deprecated Use useAIQuery instead. Kept for backward compatibility during migration. */
export const useAIAsk = useAIQuery;
