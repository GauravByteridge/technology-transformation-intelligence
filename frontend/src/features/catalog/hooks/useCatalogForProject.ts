import { useQuery } from '@tanstack/react-query';
import { getCatalogForProject } from '../services/catalogService';
import type { CatalogEntry } from '../types';

/**
 * Fetches catalog entries mapped to a specific project.
 * Enabled only when a valid projectId is provided.
 */
export function useCatalogForProject(projectId: string) {
  return useQuery<CatalogEntry[]>({
    queryKey: ['catalog', 'project', projectId],
    queryFn: () => getCatalogForProject(projectId),
    enabled: !!projectId,
  });
}
