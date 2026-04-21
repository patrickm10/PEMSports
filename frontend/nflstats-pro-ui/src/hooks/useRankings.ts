import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { RankingsApi } from '../api/rankingsApi';
import type { SeasonalRanking, SortField, SortOrder } from '../models/Ranking';
import { SeasonalStatsListSchema } from '../v3/schemas/player';

/**
 * Fetches and caches player rankings for a given position and year.
 *
 * Cache behavior:
 * - Data is considered fresh for 5 minutes (staleTime).
 * - Stale data stays in cache for 30 minutes before garbage collection (gcTime).
 * - 2 automatic retries on transient network errors.
 *
 * Sorting note:
 * - Sorting is owned by TanStack Table inside `VirtualizedGrid`. This hook
 *   used to re-sort the array client-side, which duplicated the grid's
 *   sort pass and forced every consumer to pass `sortBy`/`sortOrder`.
 *   Parameters are preserved for API compatibility but unused.
 */
export function useRankings(
  position: string,
  year: string,
  _sortBy: SortField = 'fpts_ppr',
  _sortOrder: SortOrder = 'desc',
) {
  return useQuery<SeasonalRanking[], Error>({
    queryKey: ['rankings', position, year],
    queryFn: async ({ signal }) => {
      const data = await RankingsApi.fetchRankings(position, year, signal);
      return SeasonalStatsListSchema.parse(data) as unknown as SeasonalRanking[];
    },
    staleTime: 0,
    gcTime: 10 * 60 * 1000,
    retry: 2,
    enabled: !!position && !!year,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });
}
