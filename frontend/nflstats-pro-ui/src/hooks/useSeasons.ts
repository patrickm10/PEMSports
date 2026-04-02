import { useQuery } from '@tanstack/react-query';
import { RankingsApi } from '../api/rankingsApi';

/**
 * Fetches available season years for a position.
 * Cached for 1 hour — seasons list changes only when the pipeline runs.
 */
export function useSeasons(position: string) {
  return useQuery<number[], Error>({
    queryKey: ['seasons', position],
    queryFn: () => RankingsApi.fetchSeasons(position),
    staleTime: 60 * 60 * 1000,
    gcTime: 120 * 60 * 1000,
    retry: 1,
    enabled: !!position,
  });
}
