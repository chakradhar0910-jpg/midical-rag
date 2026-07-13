import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi, userApi } from '@/lib/api';

interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  role: string;
  status: string;
  is_email_verified: boolean;
  is_mfa_enabled: boolean;
  last_login?: string;
  created_at: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string, mfaToken?: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (data: any) => Promise<void>;
  fetchProfile: () => Promise<void>;
  updateProfile: (data: any) => Promise<void>;
  setTokens: (access: string, refresh: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isLoading: false,
      isAuthenticated: false,

      setTokens: (access: string, refresh: string) => {
        if (typeof window !== 'undefined') {
          localStorage.setItem('access_token', access);
          localStorage.setItem('refresh_token', refresh);
        }
        set({ accessToken: access, refreshToken: refresh, isAuthenticated: true });
      },

      login: async (email, password, mfaToken) => {
        set({ isLoading: true });
        try {
          const { data } = await authApi.login({ email, password, mfa_token: mfaToken });
          if (typeof window !== 'undefined') {
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
          }
          set({ accessToken: data.access_token, refreshToken: data.refresh_token, isAuthenticated: true });
          await get().fetchProfile();
        } finally {
          set({ isLoading: false });
        }
      },

      logout: async () => {
        const { refreshToken } = get();
        try {
          if (refreshToken) await authApi.logout(refreshToken);
        } catch {}
        if (typeof window !== 'undefined') localStorage.clear();
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
      },

      register: async (data) => {
        set({ isLoading: true });
        try {
          await authApi.register(data);
        } finally {
          set({ isLoading: false });
        }
      },

      fetchProfile: async () => {
        try {
          const { data } = await userApi.getProfile();
          set({ user: data, isAuthenticated: true });
        } catch {
          set({ user: null, isAuthenticated: false });
        }
      },

      updateProfile: async (data) => {
        const { data: updated } = await userApi.updateProfile(data);
        set({ user: updated });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
