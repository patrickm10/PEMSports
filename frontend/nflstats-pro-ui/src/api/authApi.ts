import type { LoginCredentials, RegisterCredentials, AuthResponse, UserProfile } from '../models/Auth';
import { getApiBaseUrl } from '../utils/backendOrigin';

const API_BASE = `${getApiBaseUrl()}/auth`;

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const formData = new URLSearchParams();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    const response = await fetch(`${API_BASE}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
    if (!response.ok) throw new Error('Login failed');
    return response.json();
  },

  register: async (credentials: RegisterCredentials): Promise<UserProfile> => {
    const response = await fetch(`${API_BASE}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });
    if (!response.ok) throw new Error('Registration failed');
    return response.json();
  },

  getProfile: async (token: string): Promise<UserProfile> => {
    const response = await fetch(`${API_BASE}/me`, {
      method: 'GET',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    if (!response.ok) throw new Error('Failed to fetch profile');
    return response.json();
  }
};
