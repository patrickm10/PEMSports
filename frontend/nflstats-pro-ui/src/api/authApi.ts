import type { LoginCredentials, RegisterCredentials, SessionAck, UserProfile } from '../models/Auth';
import { AuthApiError } from '../models/Auth';

/** Same-origin via Vite proxy / Vercel rewrite — first-party cookie host. */
const AUTH_BASE = '/api/v1/auth';

const CREDENTIALS: RequestInit = { credentials: 'include' };

export function parseAuthDetail(payload: unknown, fallback: string): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (
      Array.isArray(detail) &&
      detail[0] &&
      typeof detail[0] === 'object' &&
      detail[0] !== null &&
      'msg' in detail[0]
    ) {
      return String((detail[0] as { msg: unknown }).msg);
    }
  }
  return fallback;
}

async function readError(response: Response, fallback: string): Promise<AuthApiError> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  const detail = parseAuthDetail(payload, fallback);
  return new AuthApiError(response.status, detail);
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<SessionAck> => {
    const formData = new URLSearchParams();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    const response = await fetch(`${AUTH_BASE}/token`, {
      ...CREDENTIALS,
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
    if (!response.ok) {
      throw await readError(response, 'Email or password is incorrect.');
    }
    return response.json();
  },

  register: async (credentials: RegisterCredentials): Promise<UserProfile> => {
    const response = await fetch(`${AUTH_BASE}/register`, {
      ...CREDENTIALS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });
    if (!response.ok) {
      throw await readError(response, 'Could not create the account.');
    }
    return response.json();
  },

  getProfile: async (): Promise<UserProfile> => {
    const response = await fetch(`${AUTH_BASE}/me`, {
      ...CREDENTIALS,
      method: 'GET',
    });
    if (!response.ok) {
      throw await readError(response, 'Failed to fetch profile');
    }
    return response.json();
  },

  logout: async (): Promise<void> => {
    const response = await fetch(`${AUTH_BASE}/logout`, {
      ...CREDENTIALS,
      method: 'POST',
    });
    if (!response.ok) {
      throw await readError(response, 'Could not sign out.');
    }
  },
};
