import axios from 'axios';
import type { LoginCredentials, RegisterCredentials, AuthResponse, UserProfile } from '../models/Auth';

const API_BASE = import.meta.env.VITE_API_BASE_URL 
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/auth` 
  : 'http://localhost:8000/api/v1/auth';

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const formData = new URLSearchParams();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    const response = await axios.post<AuthResponse>(`${API_BASE}/token`, formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },

  register: async (credentials: RegisterCredentials): Promise<UserProfile> => {
    const response = await axios.post<UserProfile>(`${API_BASE}/register`, credentials);
    return response.data;
  },

  getProfile: async (token: string): Promise<UserProfile> => {
    const response = await axios.get<UserProfile>(`${API_BASE}/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  }
};
