import { getApiBaseUrl } from '../utils/backendOrigin';
import type {
  PlayerMetadataResponse,
  PlayerSearchResponse,
  PlayerSplitResponse,
  PlayerSplitByYearResponse,
  PlayerWeeklyResponse,
  SplitDimension,
} from './playerTypes';
import { ApiError, apiFetch } from './apiClient';

const API_BASE = getApiBaseUrl();
const REQUEST_TIMEOUT_MS = 10_000;

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(new Error('TimeoutError')),
    REQUEST_TIMEOUT_MS,
  );
  const onParentAbort = () => controller.abort(signal?.reason);
  if (signal) signal.addEventListener('abort', onParentAbort);

  try {
    const response = await apiFetch(url, { signal: controller.signal });
    if (!response.ok) {
      throw new ApiError(`HTTP ${response.status}`, response.status);
    }
    return (await response.json()) as T;
  } finally {
    clearTimeout(timeout);
    if (signal) signal.removeEventListener('abort', onParentAbort);
  }
}

/**
 * Player API client. One method per resource — no metric polymorphism.
 * Each split dimension owns its own URL so the contracts can evolve
 * independently without breaking siblings.
 */
export const PlayersApi = {
  search(q: string, limit = 10, signal?: AbortSignal): Promise<PlayerSearchResponse> {
    const url = new URL(`${API_BASE}/players/search`);
    url.searchParams.set('q', q);
    url.searchParams.set('limit', String(limit));
    return getJson<PlayerSearchResponse>(url.toString(), signal);
  },

  splits(
    playerId: string,
    position: string,
    dimension: SplitDimension,
    signal?: AbortSignal,
  ): Promise<PlayerSplitResponse> {
    const url = new URL(
      `${API_BASE}/players/${encodeURIComponent(playerId)}/splits/${dimension}`,
    );
    url.searchParams.set('pos', position);
    return getJson<PlayerSplitResponse>(url.toString(), signal);
  },

  splitsByYear(
    playerId: string,
    position: string,
    dimension: SplitDimension,
    signal?: AbortSignal,
  ): Promise<PlayerSplitByYearResponse> {
    const url = new URL(
      `${API_BASE}/players/${encodeURIComponent(playerId)}/splits/${dimension}/by-year`,
    );
    url.searchParams.set('pos', position);
    return getJson<PlayerSplitByYearResponse>(url.toString(), signal);
  },

  weekly(
    playerId: string,
    position: string,
    seasons?: number[],
    signal?: AbortSignal,
  ): Promise<PlayerWeeklyResponse> {
    const url = new URL(
      `${API_BASE}/players/${encodeURIComponent(playerId)}/weekly`,
    );
    url.searchParams.set('pos', position);
    if (seasons && seasons.length) {
      url.searchParams.set('seasons', seasons.join(','));
    }
    return getJson<PlayerWeeklyResponse>(url.toString(), signal);
  },

  metadata(
    playerId: string,
    position: string,
    signal?: AbortSignal,
  ): Promise<PlayerMetadataResponse> {
    const url = new URL(
      `${API_BASE}/players/${encodeURIComponent(playerId)}/metadata`,
    );
    url.searchParams.set('pos', position);
    return getJson<PlayerMetadataResponse>(url.toString(), signal);
  },
};

export { ApiError as PlayersApiError };
