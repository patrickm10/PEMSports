import type { SeasonalRanking, WeeklyRanking } from '../models/Ranking';
import { getApiBaseUrl } from '../utils/backendOrigin';

const API_BASE = getApiBaseUrl();

/** Under gunicorn --timeout 60; long enough for one Render free-tier wake. */
export const REQUEST_TIMEOUT_MS = 30_000;

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === 'AbortError') ||
    (err instanceof Error && err.name === 'AbortError')
  );
}

function timeoutError(): Error {
  const err = new Error('TimeoutError');
  err.name = 'TimeoutError';
  return err;
}

const TIMEOUT_ABORT = 'RankingsTimeout';

/** Single attempt with timeout. React Query owns retries; 4xx is not retried there. */
async function fetchWithTimeout(url: string, signal?: AbortSignal): Promise<Response> {
  if (signal?.aborted) {
    throw new DOMException('Aborted', 'AbortError');
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(TIMEOUT_ABORT), REQUEST_TIMEOUT_MS);
  const onParentAbort = () => controller.abort(signal?.reason);
  signal?.addEventListener('abort', onParentAbort);

  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) {
      throw new ApiError(`HTTP ${response.status}`, response.status);
    }
    return response;
  } catch (err) {
    if (controller.signal.reason === TIMEOUT_ABORT) {
      throw timeoutError();
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
    signal?.removeEventListener('abort', onParentAbort);
  }
}

export function shouldRetryRankingsQuery(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status != null && error.status >= 400 && error.status < 500) {
    return false;
  }
  if (isAbortError(error)) return false;
  return failureCount < 2;
}

function parseYearList(payload: unknown): number[] {
  if (!Array.isArray(payload)) return [];
  return payload.map((v) => Number(v)).filter((n) => Number.isFinite(n));
}

/**
 * Type-safe API client for the PEM Sports rankings backend.
 *
 * API_BASE points to /api/v1 — set VITE_API_BASE in production
 * (e.g. https://nflstats-api.onrender.com/api/v1).
 */
export const RankingsApi = {
  async fetchRankings(position: string, year: string, signal?: AbortSignal): Promise<SeasonalRanking[]> {
    const url = new URL(`${API_BASE}/rankings/${position}`);
    if (year) url.searchParams.set('year', year);
    url.searchParams.set('limit', '500');

    const response = await fetchWithTimeout(url.toString(), signal);
    return response.json();
  },

  async fetchRankingsCsv(position: string, year: string): Promise<string> {
    const url = new URL(`${API_BASE}/rankings/${position}/csv`);
    if (year) url.searchParams.set('year', year);

    const response = await fetchWithTimeout(url.toString());
    return response.text();
  },

  async fetchSeasons(position: string, signal?: AbortSignal): Promise<number[]> {
    const url = `${API_BASE}/rankings/${position}/seasons`;
    const response = await fetchWithTimeout(url, signal);
    return parseYearList(await response.json());
  },

  async fetchWeeklyRankings(position: string, year: string, week: string, signal?: AbortSignal): Promise<WeeklyRanking[]> {
    const url = new URL(`${API_BASE}/rankings/${position}/weekly`);
    if (year) url.searchParams.set('year', year);
    if (week) url.searchParams.set('week', week);
    url.searchParams.set('limit', '500');

    const response = await fetchWithTimeout(url.toString(), signal);
    return response.json();
  },

  async fetchWeeklyRankingsCsv(position: string, year: string, week: string): Promise<string> {
    const url = new URL(`${API_BASE}/rankings/${position}/weekly/csv`);
    if (year) url.searchParams.set('year', year);
    if (week) url.searchParams.set('week', week);

    const response = await fetchWithTimeout(url.toString());
    return response.text();
  },

  async fetchWeeks(position: string, year: string, signal?: AbortSignal): Promise<number[]> {
    const url = new URL(`${API_BASE}/rankings/${position}/weeks`);
    if (year) url.searchParams.set('year', year);
    const response = await fetchWithTimeout(url.toString(), signal);
    return parseYearList(await response.json());
  },
};
