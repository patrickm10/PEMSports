import { useQuery } from '@tanstack/react-query';
import { RankingsApi, shouldRetryRankingsQuery } from '../api/rankingsApi';

/**
 * Fetches available season years for a position.
 * Cached for 1 hour — seasons list changes only when the pipeline runs.
 */
export function useSeasons(position: string) {
  return useQuery<number[], Error>({
    queryKey: ['seasons', position],
    queryFn: ({ signal }) => RankingsApi.fetchSeasons(position, signal),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: shouldRetryRankingsQuery,
    enabled: !!position,
  });
}
