import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { authApi } from '../api/authApi';
import type { UserProfile, LoginCredentials, RegisterCredentials } from '../models/Auth';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    const initializeAuth = async () => {
      const hasSessionHint =
        typeof document !== 'undefined' && document.cookie.includes('csrf_token=');
      if (!hasSessionHint) {
        if (mounted) {
          setUser(null);
          setIsLoading(false);
        }
        return;
      }
      try {
        const profile = await authApi.getProfile();
        if (mounted) {
          setUser(profile);
        }
      } catch {
        if (mounted) {
          setToken(null);
          setUser(null);
        }
      }
      if (mounted) {
        setIsLoading(false);
      }
    };

    initializeAuth();

    return () => {
      mounted = false;
    };
  }, []);

  const login = async (credentials: LoginCredentials) => {
    const response = await authApi.login(credentials);
    setToken(response.access_token);
    const profile = await authApi.getProfile(response.access_token);
    setUser(profile);
  };

  const register = async (credentials: RegisterCredentials) => {
    await authApi.register(credentials);
    await login(credentials);
  };

  const logout = () => {
    void authApi.logout();
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// Fast Refresh requires component-only exports; the hook is the AuthProvider consumer.
// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
