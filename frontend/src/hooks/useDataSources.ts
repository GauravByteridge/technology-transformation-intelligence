import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { DataSourceStatus } from '../types';

export function useDataSources() {
  return useQuery<DataSourceStatus[]>({
    queryKey: ['datasources'],
    queryFn: () => apiClient.getDataSources(),
  });
}
