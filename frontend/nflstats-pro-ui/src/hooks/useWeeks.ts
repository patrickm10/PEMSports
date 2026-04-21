import { useQuery } from '@tanstack/react-query';
import { RankingsApi } from '../api/rankingsApi';
import { useQueryErrorToast } from './useQueryErrorToast';

/**
 * Fetches available weeks for a given position and year.
 */
export function useWeeks(position: string, year: string) {
  const q = useQuery<number[], Error>({
    queryKey: ['weeks', position, year],
    queryFn: () => RankingsApi.fetchWeeks(position, year),
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
    placeholderData: (prev) => prev,
    enabled: !!position && !!year,
  });
  useQueryErrorToast(q.error, q.isError);
  return q;
}
