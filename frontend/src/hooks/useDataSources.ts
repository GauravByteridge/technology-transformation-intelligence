import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { DataSourceResponse } from '@/types';

export function useDataSources() {
  return useQuery<DataSourceResponse[]>({
    queryKey: ['data-sources'],
    queryFn: () => apiClient.getDataSources(),
  });
}
