import { useQuery } from '@tanstack/react-query';

import { RankingsApi } from '../api/rankingsApi';
import { PlayerProfileResponseSchema, type PlayerProfileResponse } from '../v3/schemas/player';
import { useQueryErrorToast } from './useQueryErrorToast';

export function usePlayerProfile(
  playerId: string | null,
  year: string,
  position: string,
  enabled: boolean,
) {
  const q = useQuery<PlayerProfileResponse, Error>({
    queryKey: ['playerProfile', position, playerId, year],
    queryFn: async ({ signal }) => {
      if (!playerId) throw new Error('playerId required');
      const raw = await RankingsApi.fetchPlayerProfile(position, playerId, year, signal);
      return PlayerProfileResponseSchema.parse(raw);
    },
    enabled: Boolean(enabled && playerId && year && position),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: 2,
    refetchOnWindowFocus: false,
  });
  useQueryErrorToast(q.error, q.isError);
  return q;
}
