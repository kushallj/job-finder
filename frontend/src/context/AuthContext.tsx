import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api, { STORAGE_KEY_AUTH_TOKEN } from '../api/axios';

export interface UserProfile {
  id: number;
  email: string;
  full_name: string | null;
  subscription_tier: 'free' | 'starter' | 'pro' | 'unlimited';
  credits_balance: number;
  is_superuser: boolean;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  topupCredits: (amount: number) => Promise<void>;
  isAuthModalOpen: boolean;
  setIsAuthModalOpen: (open: boolean) => void;
  creditDepletedData: any | null;
  clearCreditDepletedAlert: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(STORAGE_KEY_AUTH_TOKEN);
    }
    return null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [creditDepletedData, setCreditDepletedData] = useState<any | null>(null);

  const fetchProfile = useCallback(async () => {
    try {
      const response = await api.get<UserProfile>('/api/auth/me');
      setUser(response.data);
    } catch (err) {
      console.warn('Failed to restore active auth session:', err);
      localStorage.removeItem(STORAGE_KEY_AUTH_TOKEN);
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchProfile();
    } else {
      setIsLoading(false);
    }
  }, [token, fetchProfile]);

  // Listen for global 401 and 402 events from Axios interceptor
  useEffect(() => {
    const handleAuthRequired = () => {
      setIsAuthModalOpen(true);
    };

    const handleInsufficientCredits = (event: Event) => {
      const customEvent = event as CustomEvent;
      setCreditDepletedData(customEvent.detail || { error: 'INSUFFICIENT_CREDITS' });
    };

    window.addEventListener('job_finder:auth_required', handleAuthRequired);
    window.addEventListener('job_finder:insufficient_credits', handleInsufficientCredits);

    return () => {
      window.removeEventListener('job_finder:auth_required', handleAuthRequired);
      window.removeEventListener('job_finder:insufficient_credits', handleInsufficientCredits);
    };
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    const res = await api.post<AuthResponse>('/api/auth/login', { email, password });
    const { access_token, user: profile } = res.data;
    localStorage.setItem(STORAGE_KEY_AUTH_TOKEN, access_token);
    setToken(access_token);
    setUser(profile);
    setIsAuthModalOpen(false);
  };

  const register = async (email: string, password: string, fullName?: string): Promise<void> => {
    const res = await api.post<AuthResponse>('/api/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    const { access_token, user: profile } = res.data;
    localStorage.setItem(STORAGE_KEY_AUTH_TOKEN, access_token);
    setToken(access_token);
    setUser(profile);
    setIsAuthModalOpen(false);
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY_AUTH_TOKEN);
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (!token) return;
    try {
      const res = await api.get<UserProfile>('/api/auth/me');
      setUser(res.data);
    } catch (e) {
      console.warn('Error refreshing user profile:', e);
    }
  };

  const topupCredits = async (amount: number) => {
    const res = await api.post('/api/auth/credits/topup', { amount });
    if (res.data?.credits_balance !== undefined) {
      setUser((prev) => (prev ? { ...prev, credits_balance: res.data.credits_balance } : prev));
      setCreditDepletedData(null);
    }
  };

  const clearCreditDepletedAlert = () => setCreditDepletedData(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
        topupCredits,
        isAuthModalOpen,
        setIsAuthModalOpen,
        creditDepletedData,
        clearCreditDepletedAlert,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
