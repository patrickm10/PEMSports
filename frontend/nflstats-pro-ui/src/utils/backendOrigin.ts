/**
 * Single source of truth for API base URL and backend origin (scheme + host + port).
 * Keeps rankings, auth, and static assets aligned when using VITE_API_BASE or VITE_API_BASE_URL.
 */
export function getApiBaseUrl(): string {
  const direct = import.meta.env.VITE_API_BASE;
  if (direct) return direct;
  const root = import.meta.env.VITE_API_BASE_URL;
  if (root) {
    return `${String(root).replace(/\/$/, '')}/api/v1`;
  }
  if (import.meta.env.PROD) {
    throw new Error(
      'Missing API base URL: set VITE_API_BASE (or VITE_API_BASE_URL) for production builds.'
    );
  }
  return 'http://localhost:8000/api/v1';
}

export function getBackendOrigin(): string {
  try {
    return new URL(getApiBaseUrl()).origin;
  } catch {
    return '';
  }
}

/** Absolute or same-origin path for `/static/...` on the API. */
export function staticAssetUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const p = path.startsWith('/') ? path : `/${path}`;
  const origin = getBackendOrigin();
  return origin ? `${origin}${p}` : p;
}

/** Vite `public/default-player.png` — works even when the API is down. */
export const PUBLIC_DEFAULT_PLAYER_IMG = '/default-player.png';
