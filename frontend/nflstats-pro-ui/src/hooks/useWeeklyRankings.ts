import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { RankingsApi } from '../api/rankingsApi';
import type { SortField, SortOrder, WeeklyRanking } from '../models/Ranking';
import { WeeklyStatsListSchema } from '../v3/schemas/player';

/**
 * Fetches weekly player rankings for a specific position and week.
 *
 * Sorting note:
 * - Sorting is owned by TanStack Table inside `VirtualizedGrid`.
 * - Arguments preserved for API compatibility but unused here — removing
 *   the duplicate sort pass fixes a UX bug where the app was sorting on
 *   `fpts_ppr` (which was also hidden from the grid).
 */
export function useWeeklyRankings(
  position: string,
  year: string,
  week: string,
  _sortBy: SortField = 'fpts_ppr',
  _sortOrder: SortOrder = 'desc',
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
