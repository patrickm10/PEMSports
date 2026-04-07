import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { RankingsApi } from '../api/rankingsApi';
import type { Ranking, SortField, SortOrder } from '../models/Ranking';


/**
 * Fetches weekly player rankings for a specific position and week.
 */
import { PlayerStatsListSchema } from '../v3/schemas/player';

export function useWeeklyRankings(
  position: string, 
  year: string, 
  week: string,
  sortBy: SortField = 'rank',
  sortOrder: SortOrder = 'asc'
) {
  const result = useQuery({
    queryKey: ['weekly-rankings', position, year, week],
    queryFn: async ({ signal }) => {
      const data = await RankingsApi.fetchWeeklyRankings(position, year, week, signal);
      // V3 HARDNESS: Validate data integrity at the ingestion boundary
      return PlayerStatsListSchema.parse(data) as unknown as Ranking[];
    },

    staleTime: 0,
    gcTime: 10 * 60 * 1000,
    retry: 2,
    enabled: !!position && !!year && !!week,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });

  // Client-side sorting for responsiveness after data is cached
  const sortedData = result.data ? [...result.data].sort((a, b) => {
    const valA = (a as any)[sortBy] ?? 0;
    const valB = (b as any)[sortBy] ?? 0;
    
    if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
    if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  }) : [];

  return { ...result, data: sortedData };
}
