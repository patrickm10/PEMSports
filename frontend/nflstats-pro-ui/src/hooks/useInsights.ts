import { useQuery } from '@tanstack/react-query';
import { InsightsApi } from '../api/insightsApi';
import type { InsightContext, InsightPosition } from '../api/insightsTypes';
import { useInsightsStore } from '../stores/insightsStore';

interface UseInsightsFilters {
  year: string;
  week: string;
  viewMode: 'season' | 'weekly';
}

export function useInsightsLeaderboard(filters: UseInsightsFilters) {
  const position = useInsightsStore((s) => s.position);
  const context = useInsightsStore((s) => s.context);
  const contextValue = useInsightsStore((s) => s.contextValue);

  const year = filters.year || undefined;
  const week = filters.viewMode === 'weekly' && filters.week ? filters.week : undefined;

  return useQuery({
    queryKey: ['insights', position, context, contextValue, year, week],
    queryFn: ({ signal }) =>
      InsightsApi.fetchLeaderboard({
        position,
        context,
        contextValue,
        year,
        week,
        limit: 15,
        signal,
      }),
    enabled: Boolean(contextValue),
    staleTime: 5 * 60 * 1000,
  });
}

export function useInsightsContextValues(
  position: InsightPosition,
  context: string,
  year: string,
  enabled = true,
) {
  return useQuery({
    queryKey: ['insights-contexts', position, context, year],
    queryFn: ({ signal }) =>
      InsightsApi.fetchContextValues(
        position,
        context as InsightContext,
        year || undefined,
        signal,
      ),
    enabled,
    staleTime: 10 * 60 * 1000,
  });
}

export function useInsightsPlayerDetail(
  playerId: string | null,
  playerPosition: Exclude<InsightPosition, 'all'> | null,
  filters: UseInsightsFilters,
) {
  const context = useInsightsStore((s) => s.context);
  const contextValue = useInsightsStore((s) => s.contextValue);

  const year = filters.year || undefined;
  const week = filters.viewMode === 'weekly' && filters.week ? filters.week : undefined;

  return useQuery({
    queryKey: ['insights-player', playerId, playerPosition, context, contextValue, year, week],
    queryFn: ({ signal }) =>
      InsightsApi.fetchPlayerDetail(playerId!, {
        position: playerPosition!,
        context,
        contextValue,
        year,
        week,
        signal,
      }),
    enabled: Boolean(playerId && playerPosition && contextValue),
    staleTime: 5 * 60 * 1000,
  });
}
