import type { LoginCredentials, RegisterCredentials, AuthResponse, UserProfile } from '../models/Auth';
import { getApiBaseUrl } from '../utils/backendOrigin';

const API_BASE = `${getApiBaseUrl()}/auth`;

function csrfHeaders(): Record<string, string> {
  if (typeof document === 'undefined') return {};
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
  if (!match) return {};
  return { 'X-CSRF-Token': decodeURIComponent(match[1]) };
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const formData = new URLSearchParams();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    const response = await fetch(`${API_BASE}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
      credentials: 'include',
    });
    if (!response.ok) throw new Error('Login failed');
    return response.json();
  },

  register: async (credentials: RegisterCredentials): Promise<UserProfile> => {
    const response = await fetch(`${API_BASE}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
      credentials: 'include',
    });
    if (!response.ok) throw new Error('Registration failed');
    return response.json();
  },

  getProfile: async (token?: string | null): Promise<UserProfile> => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await fetch(`${API_BASE}/me`, {
      method: 'GET',
      headers,
      credentials: 'include',
    });
    if (!response.ok) throw new Error('Failed to fetch profile');
    return response.json();
  },

  logout: async (): Promise<void> => {
    await fetch(`${API_BASE}/logout`, {
      method: 'POST',
      headers: { ...csrfHeaders() },
      credentials: 'include',
    });
  },
};
