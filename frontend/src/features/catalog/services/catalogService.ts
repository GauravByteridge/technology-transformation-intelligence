import { apiClient } from '@/services/api-client';
import type { CatalogEntry, DiscoveryResult } from '../types';

/**
 * API service for the Enterprise Data Catalog.
 * Provides access to catalog entries, search, and discovery operations.
 */

/** Fetch all catalog entries for a specific data source. */
export async function getCatalogForSource(sourceId: string): Promise<CatalogEntry[]> {
  const response = await apiClient.get<CatalogEntry[]>(
    `/api/v1/catalog/source/${sourceId}`,
  );
  return response.data;
}

/** Fetch all catalog entries mapped to a specific project. */
export async function getCatalogForProject(projectId: string): Promise<CatalogEntry[]> {
  const response = await apiClient.get<CatalogEntry[]>(
    `/api/v1/catalog/project/${projectId}`,
  );
  return response.data;
}

/** Fetch a single catalog entry by its ID. */
export async function getCatalogEntry(entryId: string): Promise<CatalogEntry> {
  const response = await apiClient.get<CatalogEntry>(
    `/api/v1/catalog/entries/${entryId}`,
  );
  return response.data;
}

/** Search the catalog by natural-language query, optionally scoped to a project. */
export async function searchCatalog(
  query: string,
  projectId?: string,
): Promise<CatalogEntry[]> {
  const params: Record<string, unknown> = { q: query };
  if (projectId) {
    params.project_id = projectId;
  }

  const response = await apiClient.get<CatalogEntry[]>('/api/v1/catalog/search', {
    params,
  });
  return response.data;
}

/** Trigger schema discovery and semantic profiling for a connected data source. */
export async function triggerDiscovery(sourceId: string): Promise<DiscoveryResult> {
  const response = await apiClient.post<DiscoveryResult>(
    `/api/v1/data-sources/${sourceId}/discover`,
  );
  return response.data;
}
