import { getApiBaseUrl } from '../utils/backendOrigin';
import type {
  InsightContext,
  InsightPosition,
  InsightsContextValuesResponse,
  InsightsLeaderboardResponse,
  InsightsPlayerDetailResponse,
} from './insightsTypes';
import { apiFetchJson } from './apiClient';

const API_BASE = getApiBaseUrl();

async function fetchJson<T>(url: URL, signal?: AbortSignal): Promise<T> {
  return apiFetchJson<T>(url.toString(), { signal });
}

export interface InsightsQueryParams {
  position: InsightPosition;
  context: InsightContext;
  contextValue: string;
  metric?: string;
  year?: string;
  week?: string;
  seasons?: string;
  limit?: number;
  signal?: AbortSignal;
}

export const InsightsApi = {
  async fetchLeaderboard(params: InsightsQueryParams): Promise<InsightsLeaderboardResponse> {
    const url = new URL(`${API_BASE}/insights`);
    url.searchParams.set('position', params.position);
    url.searchParams.set('context', params.context);
    url.searchParams.set('context_value', params.contextValue);
    if (params.metric) url.searchParams.set('metric', params.metric);
    if (params.year) url.searchParams.set('year', params.year);
    if (params.week) url.searchParams.set('week', params.week);
    if (params.seasons) url.searchParams.set('seasons', params.seasons);
    if (params.limit) url.searchParams.set('limit', String(params.limit));
    return fetchJson<InsightsLeaderboardResponse>(url, params.signal);
  },

  async fetchContextValues(
    position: InsightPosition,
    context: InsightContext,
    year?: string,
    signal?: AbortSignal,
  ): Promise<InsightsContextValuesResponse> {
    const url = new URL(`${API_BASE}/insights/contexts`);
    url.searchParams.set('position', position);
    url.searchParams.set('context', context);
    if (year) url.searchParams.set('year', year);
    return fetchJson<InsightsContextValuesResponse>(url, signal);
  },

  async fetchPlayerDetail(
    playerId: string,
    params: Omit<InsightsQueryParams, 'limit'> & { position: Exclude<InsightPosition, 'all'> },
  ): Promise<InsightsPlayerDetailResponse> {
    const url = new URL(`${API_BASE}/insights/player/${playerId}`);
    url.searchParams.set('position', params.position);
    url.searchParams.set('context', params.context);
    url.searchParams.set('context_value', params.contextValue);
    if (params.metric) url.searchParams.set('metric', params.metric);
    if (params.year) url.searchParams.set('year', params.year);
    if (params.week) url.searchParams.set('week', params.week);
    if (params.seasons) url.searchParams.set('seasons', params.seasons);
    return fetchJson<InsightsPlayerDetailResponse>(url, params.signal);
  },
};
