import type { LoginCredentials, RegisterCredentials, AuthResponse, UserProfile } from '../models/Auth';

const API_BASE = import.meta.env.VITE_API_BASE_URL 
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/auth` 
  : 'http://localhost:8000/api/v1/auth';

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
