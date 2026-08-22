import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { AIResponse, AIQuestionRequest } from '../types';

export function useAIAsk() {
  return useMutation<AIResponse, Error, AIQuestionRequest>({
    mutationFn: (request) => apiClient.askQuestion(request),
  });
}
