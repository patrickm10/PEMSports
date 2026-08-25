import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { authApi } from '../api/authApi';
import type { UserProfile, LoginCredentials, RegisterCredentials } from '../models/Auth';

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function clearLegacyToken(): void {
  try {
    localStorage.removeItem('auth_token');
  } catch {
    // ignore quota / private mode
  }
}

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    clearLegacyToken();
    let mounted = true;

    const initializeAuth = async () => {
      try {
        const profile = await authApi.getProfile();
        if (mounted) {
          setUser(profile);
        }
      } catch {
        if (mounted) {
          setUser(null);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    void initializeAuth();

    return () => {
      mounted = false;
    };
  }, []);

  const login = async (credentials: LoginCredentials) => {
    await authApi.login(credentials);
    const profile = await authApi.getProfile();
    setUser(profile);
  };

  const register = async (credentials: RegisterCredentials) => {
    await authApi.register(credentials);
    await login(credentials);
  };

  const logout = () => {
    setUser(null);
    void authApi.logout().catch(() => {
      /* cookie clear is best-effort; UI is already signed out */
    });
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
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
