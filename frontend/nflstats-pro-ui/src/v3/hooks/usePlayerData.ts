import { useQuery } from '@tanstack/react-query';
import { PlayerStatsListSchema } from '../schemas/player';
import type { PlayerStats } from '../schemas/player';

interface RankingParams {
  position: string;
  year: string;
  viewMode: 'seasonal' | 'weekly';
  week?: string;
}

/**
 * usePlayerData (V3)
 * Fetches player statistics from the backend and validates them via Zod.
 * Enforces Zero-Transformation Data Integrity at the point of ingestion.
 */
export const usePlayerData = (params: RankingParams) => {
  const { position, year, viewMode, week } = params;

  const endpoint = viewMode === 'weekly' 
    ? `http://localhost:8000/api/v1/rankings/${position}/weekly?year=${year}&week=${week}`
    : `http://localhost:8000/api/v1/rankings/${position}?year=${year}`;

  return useQuery<PlayerStats[]>({
    queryKey: ['rankings', position, year, viewMode, week],
    queryFn: async () => {
      const response = await fetch(endpoint);
      if (!response.ok) {
        throw new Error(`NFL API Error: ${response.status} (Failed Fetch)`);
      }
      
      const rawData = await response.json();
      
      // Zero-Transformation Schema Validation
      const result = PlayerStatsListSchema.safeParse(rawData);
      
      if (!result.success) {
        console.error('Schema Validation Failed:', result.error.format());
        // In V3, we fail fast for data integrity
        throw new Error('NFL Data Integrity Violation: Schema Mismatch');
      }

      return result.data;
    },
    enabled: !!position && !!year,
  });
};
