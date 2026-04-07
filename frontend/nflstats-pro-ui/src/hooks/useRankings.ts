import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { RankingsApi } from '../api/rankingsApi';
import type { Ranking, SortField, SortOrder } from '../models/Ranking';

/**
 * Fetches and caches player rankings for a given position and year.
 *
 * Cache behavior:
 * - Data is considered fresh for 5 minutes (staleTime).
 * - Stale data stays in cache for 30 minutes before garbage collection (gcTime).
 * - 2 automatic retries on transient network errors.
 * - Client-side sorting is applied at the component level; the query key
 *   does NOT include sortBy/sortOrder because sorting doesn't change the
 *   fetched dataset, only its presentation order.
 */
import { PlayerStatsListSchema } from '../v3/schemas/player';

export function useRankings(
  position: string,
  year: string,
  sortBy: SortField,
  sortOrder: SortOrder,
) {
  const query = useQuery<Ranking[], Error>({
    queryKey: ['rankings', position, year],
    queryFn: async ({ signal }) => {
      const data = await RankingsApi.fetchRankings(position, year, signal);
      // V3 HARDNESS: Validate data integrity at the ingestion boundary
      return PlayerStatsListSchema.parse(data) as unknown as Ranking[];
    },
    staleTime: 0,
    gcTime: 10 * 60 * 1000,
    retry: 2,
    enabled: !!position && !!year,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });

  // Apply client-side sorting to the cached data without triggering a refetch.
  const sortedData = query.data
    ? [...query.data].sort((a, b) => {
        const aVal = (a as any)[sortBy] ?? 0;
        const bVal = (b as any)[sortBy] ?? 0;
        if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      })
    : [];

  return { ...query, data: sortedData };
}
