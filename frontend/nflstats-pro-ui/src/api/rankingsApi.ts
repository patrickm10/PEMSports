import type { SeasonalRanking, WeeklyRanking } from '../models/Ranking';
import { getApiBaseUrl } from '../utils/backendOrigin';

const API_BASE = getApiBaseUrl();

class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function fetchWithRetry(url: string, signal?: AbortSignal, retries = 2): Promise<Response> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      // 10 second timeout for all API requests
      const timeoutId = setTimeout(() => controller.abort(new Error('TimeoutError')), 10000);

      // If a parent signal is provided, link it to the controller
      const onParentAbort = () => controller.abort(signal?.reason);
      if (signal) {
        signal.addEventListener('abort', onParentAbort);
      }

      const response = await fetch(url, { 
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      if (signal) {
        signal.removeEventListener('abort', onParentAbort);
      }

      if (!response.ok) {
        throw new ApiError(`HTTP ${response.status}`, response.status);
      }
      return response;
    } catch (err) {
      if ((err as Error).name === 'AbortError' && signal?.aborted) throw err;
      if (attempt === retries) throw err;
      // Exponential backoff: 500ms, 1s
      await new Promise((r) => setTimeout(r, 500 * Math.pow(2, attempt)));
    }
  }
  // Unreachable, but satisfies TypeScript
  throw new ApiError('Max retries exceeded');
}

/**
 * Type-safe API client for the NFL rankings backend.
 *
 * Notes:
 * - Sorting is intentionally client-side only. The backend returns data
 *   sorted by fpts_ppr by default. We sort in useRankings() post-cache
 *   to avoid unnecessary network requests on sort column changes.
 * - API_BASE points to /api/v1 — the versioned endpoint.
 *   The VITE_API_BASE env var should be set to the deployed backend URL
 *   in production (e.g. https://your-app.onrender.com/api/v1).
 */
export const RankingsApi = {
  async fetchRankings(position: string, year: string, signal?: AbortSignal): Promise<SeasonalRanking[]> {
    const url = new URL(`${API_BASE}/rankings/${position}`);
    if (year) url.searchParams.set('year', year);
    url.searchParams.set('limit', '500');

    const response = await fetchWithRetry(url.toString(), signal);
    return response.json();
  },

  async fetchRankingsCsv(position: string, year: string): Promise<string> {
    const url = new URL(`${API_BASE}/rankings/${position}/csv`);
    if (year) url.searchParams.set('year', year);

    const response = await fetchWithRetry(url.toString());
    return response.text();
  },

  async fetchSeasons(position: string): Promise<number[]> {
    const url = `${API_BASE}/rankings/${position}/seasons`;
    const response = await fetchWithRetry(url);
    return response.json();
  },

  async fetchWeeklyRankings(position: string, year: string, week: string, signal?: AbortSignal): Promise<WeeklyRanking[]> {
    const url = new URL(`${API_BASE}/weekly-rankings`);
    if (position) url.searchParams.set('pos', position);
    if (year) url.searchParams.set('year', year);
    if (week) url.searchParams.set('week', week);
    url.searchParams.set('limit', '500');

    const response = await fetchWithRetry(url.toString(), signal);
    return response.json();
  },

  async fetchWeeklyRankingsCsv(position: string, year: string, week: string): Promise<string> {
    const url = new URL(`${API_BASE}/weekly-rankings/csv`);
    if (position) url.searchParams.set('position', position);
    if (year) url.searchParams.set('year', year);
    if (week) url.searchParams.set('week', week);

    const response = await fetchWithRetry(url.toString());
    return response.text();
  },

  async fetchWeeks(position: string, year: string): Promise<number[]> {
    const url = new URL(`${API_BASE}/rankings/${position}/weeks`);
    if (year) url.searchParams.set('year', year);
    const response = await fetchWithRetry(url.toString());
    return response.json();
  },

  async fetchPlayerProfile(
    position: string,
    playerId: string,
    year: string,
    signal?: AbortSignal,
  ): Promise<unknown> {
    const url = new URL(`${API_BASE}/rankings/${position}/players/${encodeURIComponent(playerId)}/profile`);
    url.searchParams.set('year', year);
    const response = await fetchWithRetry(url.toString(), signal);
    return response.json();
  },
};
