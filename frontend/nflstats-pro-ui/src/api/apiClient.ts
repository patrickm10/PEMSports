import { getApiBaseUrl } from '../utils/backendOrigin';

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function csrfHeaders(): Record<string, string> {
  if (typeof document === 'undefined') return {};
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
  if (!match) return {};
  return { 'X-CSRF-Token': decodeURIComponent(match[1]) };
}

let refreshInFlight: Promise<boolean> | null = null;

/** Rotate the access cookie using the httpOnly refresh cookie + CSRF header. */
export async function refreshSession(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/auth/refresh`, {
        method: 'POST',
        headers: csrfHeaders(),
        credentials: 'include',
      });
      return response.ok;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

/**
 * fetch wrapper for authenticated API routes.
 * Sends httpOnly session cookies cross-origin and retries once after refresh on 401.
 */
export async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  const withCredentials: RequestInit = {
    ...init,
    credentials: 'include',
  };
  let response = await fetch(url, withCredentials);
  if (response.status === 401) {
    const refreshed = await refreshSession();
    if (refreshed) {
      response = await fetch(url, withCredentials);
    }
  }
  return response;
}

export async function apiFetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(url, init);
  if (!response.ok) {
    throw new ApiError(`HTTP ${response.status}`, response.status);
  }
  return response.json() as Promise<T>;
}
