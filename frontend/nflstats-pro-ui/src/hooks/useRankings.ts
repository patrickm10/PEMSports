import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { RankingsApi } from '../api/rankingsApi';
import type { SeasonalRanking } from '../models/Ranking';
import { SeasonalStatsListSchema } from '../v3/schemas/player';

/**
 * Fetches and caches player rankings for a given position and year.
 *
 * Sorting is owned by TanStack Table inside `VirtualizedGrid`.
 */
export function useRankings(position: string, year: string) {
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
