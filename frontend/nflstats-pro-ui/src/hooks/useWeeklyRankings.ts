import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { RankingsApi } from '../api/rankingsApi';
import type { WeeklyRanking } from '../models/Ranking';
import { WeeklyStatsListSchema } from '../v3/schemas/player';

/**
 * Fetches weekly player rankings for a specific position and week.
 *
 * Sorting is owned by TanStack Table inside `VirtualizedGrid`.
 */
export function useWeeklyRankings(
  position: string,
  year: string,
  week: string,
) {
  return useQuery<WeeklyRanking[], Error>({
    queryKey: ['weekly-rankings', position, year, week],
    queryFn: async ({ signal }) => {
      const data = await RankingsApi.fetchWeeklyRankings(position, year, week, signal);
      return WeeklyStatsListSchema.parse(data) as unknown as WeeklyRanking[];
    },
    staleTime: 0,
    gcTime: 10 * 60 * 1000,
    retry: 2,
    enabled: !!position && !!year && !!week,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });
}
