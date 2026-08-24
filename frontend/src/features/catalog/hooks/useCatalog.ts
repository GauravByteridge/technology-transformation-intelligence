import { useQuery } from '@tanstack/react-query';
import { searchCatalog } from '../services/catalogService';
import type { CatalogEntry } from '../types';

/**
 * Fetches all catalog entries for the catalog overview page.
 * Uses a broad search to retrieve the full catalog.
 */
export function useCatalogEntries() {
  return useQuery<CatalogEntry[]>({
    queryKey: ['catalog', 'all'],
    queryFn: () => searchCatalog('*'),
  });
}
