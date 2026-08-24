import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type {
  DatasetResponse,
  DatasetPreviewResponse,
  DatasetDetailResponse,
  DatasetQueryRequest,
  DatasetQueryResponse,
  DatasetConfirmRequest,
} from '@/types';

/**
 * Fetches all available datasets.
 */
export function useDatasets() {
  return useQuery<DatasetResponse[]>({
    queryKey: ['datasets'],
    queryFn: () => apiClient.getDatasets(),
  });
}

/**
 * Fetches a dataset preview (column headers + sample rows).
 * Only enabled when a valid dataset ID is provided.
 */
export function useDatasetPreview(id: string) {
  return useQuery<DatasetPreviewResponse>({
    queryKey: ['datasets', id, 'preview'],
    queryFn: () => apiClient.getDatasetPreview(id),
    enabled: !!id,
  });
}

/**
 * Confirms a dataset (transitions status from REVIEW_REQUIRED to READY).
 */
export function useDatasetConfirm() {
  return useMutation<
    DatasetDetailResponse,
    Error,
    { id: string; request?: DatasetConfirmRequest }
  >({
    mutationFn: ({ id, request }) => apiClient.confirmDataset(id, request),
  });
}

/**
 * Queries a dataset with filters, sort, pagination, and optional aggregations.
 */
export function useDatasetQuery() {
  return useMutation<
    DatasetQueryResponse,
    Error,
    { id: string; request: DatasetQueryRequest }
  >({
    mutationFn: ({ id, request }) => apiClient.queryDataset(id, request),
  });
}
