import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { PortfolioSummaryResponse } from '@/types';

/**
 * Fetches the portfolio summary from the backend.
 * Chart data derivation happens in the consuming page component, not here.
 */
export function usePortfolioSummary() {
  return useQuery<PortfolioSummaryResponse>({
    queryKey: ['portfolio', 'summary'],
    queryFn: () => apiClient.getDashboardSummary(),
  });
}
